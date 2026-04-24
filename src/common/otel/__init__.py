import inspect
import logging
import os
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast, overload
from common.settings import settings
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHTTPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as OTLPHTTPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter as OTLPHTTPLogExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter as OTLPGRPCLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as OTLPGRPCMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as OTLPGRPCSpanExporter 
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_INSTANCE_ID, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, get_tracer_provider, set_tracer_provider
from opentelemetry.util.types import AttributeValue as SpanAttributeValue

CallableType = Callable[..., Any]
DecoratedFuncType = TypeVar("DecoratedFuncType", bound=CallableType)


class FastAPISpanProcessor(BatchSpanProcessor):
    def on_end(self, span: ReadableSpan) -> None:
        if span.kind == SpanKind.INTERNAL and (
            span.attributes is not None
            and span.attributes.get("type", None)
            in ("http.request", "http.response.start", "http.response.body")
        ):
            return
        super().on_end(span=span)


def get_tracer(module_name: str):
    return get_tracer_provider().get_tracer(module_name)


def get_meter(module_name: str):
    return get_meter_provider().get_meter(module_name)


def get_logger(name):
    _logger = logging.getLogger(name)
    return _logger


def init_telemetry(service_name: str, endpoint: str | None = None):
    if "TESTING" in os.environ or not settings.MONITORING_ENABLED:
        return
    
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") if endpoint is None else endpoint
    auth_token = os.getenv("OTEL_AUTH_TOKEN")
    protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")
    if endpoint is not None:
        if protocol == "http/protobuf":
            headers = {"Authorization": f"Basic {auth_token}"} if auth_token is not None else None
            traces_exporter = OTLPHTTPSpanExporter(endpoint=endpoint+"/v1/traces", headers=headers)
            meter_exporter = OTLPHTTPMetricExporter(endpoint=endpoint+"/v1/metrics", headers=headers)
            log_exporter = OTLPHTTPLogExporter(endpoint=endpoint+"/v1/logs", headers=headers)
        else:
            traces_exporter = OTLPGRPCSpanExporter(endpoint=endpoint, headers=headers)
            meter_exporter = OTLPGRPCMetricExporter(endpoint=endpoint, headers=headers)
            log_exporter = OTLPGRPCLogExporter(endpoint=endpoint, headers=headers)
    else:
        traces_exporter = None
        meter_exporter = None
        log_exporter = None
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_INSTANCE_ID: os.uname().nodename,
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    if traces_exporter is not None:
        processor = FastAPISpanProcessor(traces_exporter)
        tracer_provider.add_span_processor(processor)

    set_tracer_provider(tracer_provider)

    if meter_exporter is not None:
        reader = PeriodicExportingMetricReader(meter_exporter)
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    else:
        meter_provider = MeterProvider(resource=resource)
    set_meter_provider(meter_provider)

    if log_exporter is not None:
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        set_logger_provider(logger_provider)

        handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger().addHandler(console)

    logging.getLogger().setLevel(logging.INFO)
    logger = logging.getLogger()
    logger.info("Telemetry initialized")


class Instrumented:
    def __init__(
        self,
        span_name: str | None = None,
        service_name: str | None = None,
        span_attributes: dict[str, SpanAttributeValue] | None = None,
    ) -> None:
        self.span_name = span_name
        self.service_name = service_name
        self.span_attributes = span_attributes if span_attributes is not None else {}

    def __call__(self, wrapped_function: DecoratedFuncType) -> DecoratedFuncType:
        module = inspect.getmodule(wrapped_function)
        has_span_param = inspect.signature(wrapped_function).parameters.get("span") is not None
        is_async = inspect.iscoroutinefunction(wrapped_function)
        module_name = __name__
        if module is not None:
            module_name = module.__name__
        span_name = self.span_name or wrapped_function.__qualname__

        @wraps(wrapped_function)
        def new_f(*args: Any, **kwargs: Any) -> Any:
            with get_tracer(module_name).start_as_current_span(span_name) as span:
                span.set_attributes(self.span_attributes)
                if has_span_param:
                    return wrapped_function(*args, span=span, **kwargs)
                return wrapped_function(*args, **kwargs)

        @wraps(wrapped_function)
        async def new_f_async(*args: Any, **kwargs: Any) -> Any:
            with get_tracer(module_name).start_as_current_span(span_name) as span:
                span.set_attributes(self.span_attributes)
                if has_span_param:
                    return await wrapped_function(*args, span=span, **kwargs)
                return await wrapped_function(*args, **kwargs)

        return cast(DecoratedFuncType, new_f_async) if is_async else cast(DecoratedFuncType, new_f)


@overload
def instrumented(wrapped_function: DecoratedFuncType) -> DecoratedFuncType: ...


@overload
def instrumented(
    *,
    span_name: str | None = None,
    service_name: str | None = None,
    span_attributes: dict[str, SpanAttributeValue] | None = None,
) -> Instrumented: ...


def instrumented(
    wrapped_function: DecoratedFuncType | None = None,
    *,
    span_name: str | None = None,
    service_name: str | None = None,
    span_attributes: dict[str, SpanAttributeValue] | None = None,
) -> DecoratedFuncType | Instrumented:
    """
    Decorator to enable opentelemetry instrumentation on a function.

    When the decorator is used, a child span will be created in the current trace
    context, using the fully-qualified function name as the span name.
    Alternatively, the span name can be set manually by setting the span_name parameter

    @param wrapped_function:  function or method to wrap
    @param span_name:  optional span name.  Defaults to fully qualified function name of wrapped function
    @param service_name: optional service name.  Defaults to service name set in first invocation
                         of `init_telemetry_provider`
    @param span_attributes: optional dictionary of attributes to be set on the span
    """
    inst = Instrumented(span_name=span_name, service_name=service_name, span_attributes=span_attributes)
    if wrapped_function:
        return inst(wrapped_function)
    return inst
