from wtforms import fields
import json
import pydantic


class JSONField(fields.TextAreaField):
    def _value(self):
        if isinstance(self.data, pydantic.BaseModel):
            return self.data.model_dump_json(indent=2)
        return json.dumps(self.data, indent=2) if self.data else ""

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                if isinstance(self.data, pydantic.BaseModel):
                    self.data.model_validate_json(valuelist[0])
                else:
                    self.data = json.loads(valuelist[0])
            except ValueError as e:
                raise ValueError("This field contains invalid JSON") from e
        else:
            self.data = None

    def pre_validate(self, form):
        super().pre_validate(form)
        if self.data:
            try:
                if isinstance(self.data, pydantic.BaseModel):
                    self.data.model_dump_json(indent=2)
                else:
                    json.dumps(self.data, indent=2)
            except TypeError as e:
                raise ValueError("This field contains invalid JSON") from e
