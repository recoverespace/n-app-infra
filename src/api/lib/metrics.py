from opentelemetry.metrics import get_meter
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp

meter = get_meter(__name__)

INFO = meter.create_gauge("fastapi_app_info", "", "FastAPI application information.")
REQUESTS = meter.create_counter(
    "http.server.request.total", "requests", "Total count of requests by method and path."
)
RESPONSES = meter.create_counter(
    "http.server.response.total", "responses", "Total count of responses by method, path and status codes."
)
EXCEPTIONS = meter.create_counter(
    "http.server.exception.total",
    "errors",
    "Total count of exceptions raised by path and exception type",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, app_name: str = "fastapi-app", app_version: str = "0.0.1") -> None:
        super().__init__(app)
        self._common_attrs = {"app_name": app_name, "app_version": app_version}
        INFO.set(1.0, attributes=self._common_attrs)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        path, is_handled_path = self.get_path(request)
        attrs = {"method": method, "path": path, **self._common_attrs}

        if not is_handled_path:
            return await call_next(request)

        REQUESTS.add(1, attributes=attrs)
        try:
            response = await call_next(request)
        except BaseException as e:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
            exc_labels = {"exception_type": type(e).__name__, **attrs}
            EXCEPTIONS.add(1, attributes=exc_labels)
            raise e from None
        else:
            status_code = response.status_code
        finally:
            RESPONSES.add(1, attributes={"status_code": status_code, **attrs})

        return response

    @staticmethod
    def get_path(request: Request) -> tuple[str, bool]:
        for route in request.app.routes:
            match, child_scope = route.matches(request.scope)
            if match == Match.FULL:
                return route.path, True

        return request.url.path, False
