from wtforms import TextAreaField
from wtforms.validators import DataRequired

from data.domain.tenants.models import Tenant
from sqladmin import ModelView


class ArrayTextAreaField(TextAreaField):
    """Custom field to handle PostgreSQL ARRAY as textarea with newline-separated values."""

    def _value(self):
        """Convert array to textarea string (for display)."""
        if self.data:
            # Convert list to newline-separated string
            return '\n'.join(self.data)
        return ''

    def process_formdata(self, valuelist):
        """Convert textarea string to array (for saving)."""
        if valuelist:
            # Split by newlines and filter out empty lines
            self.data = [
                line.strip()
                for line in valuelist[0].split('\n')
                if line.strip()
            ]
        else:
            self.data = []


class TenantAdmin(ModelView, model=Tenant):
    name = "Tenant"
    name_plural = "Tenants"
    category_icon = "fa-solid fa-building"
    category = "User Management"
    page_size = 25

    column_default_sort = [
        (Tenant.id, True),
    ]

    column_list = [
        "id",
        "title",
        "enabled",
        "domains",
    ]

    column_details_list = [
        "id",
        "title",
        "enabled",
        "domains",
        "created_at",
        "updated_at",
    ]

    column_searchable_list = (
        "id",
        "title",
    )

    column_sortable_list = (
        "id",
        "title",
        "enabled",
        "domains",
    )

    # Enable create and edit forms
    can_create = True
    can_edit = True
    can_delete = True

    # Exclude auto-generated fields from forms
    form_excluded_columns = ["id", "created_at", "updated_at"]

    # Override form fields to use custom ArrayTextAreaField for domains array
    form_overrides = dict(
        domains=ArrayTextAreaField,
    )

    # Make timestamp fields readonly (shown in detail view)
    form_widget_args = dict(
        created_at=dict(readonly=True),
        updated_at=dict(readonly=True),
        domains=dict(rows=5),  # Set textarea height
    )

    # Configure form field descriptions/help text
    form_args = dict(
        title=dict(
            label="Tenant Name",
            description="Unique name for the tenant organization"
        ),
        enabled=dict(
            label="Enabled",
            description="Whether this tenant is active and users can login"
        ),
        domains=dict(
            label="Email Domains",
            description=(
                "Enter email domains (one per line, e.g., 'example.com'). "
                "Users with these email domains will be associated with this tenant."
            )
        ),
    )
