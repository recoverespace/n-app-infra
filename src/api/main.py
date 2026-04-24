import json
from contextlib import asynccontextmanager
from api.lib.metrics import MetricsMiddleware
from sqlmodel import text
from common.processing.streams import test_broker_connection
from fastapi import FastAPI, APIRouter
from api.v1.users.router import router as users_router
from api.v1.auth.router import router as auth_router
from api.v1.circle.router import router as circle_router
from api.v1.chats.router import router as chats_router
from api.v1.storyblock.router import router as storyblock_router
from api.v1.payments.router import router as payments_router
from api.v1.community.router import router as community_router
from api.v1.reporting.app import reporting_app
from api.settings import settings

import firebase_admin
from firebase_admin import credentials
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.metrics import get_meter_provider
from opentelemetry.trace import get_tracer_provider
from common.otel import init_telemetry, get_logger
from api.lib.deps import DBDep
from api.lib.centrifuge import centrifuge
from fastapi import status as http_status
from fastapi.responses import JSONResponse

init_telemetry(f"{settings.SERVICE_PREFIX}-api")
logger = get_logger(__name__)

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(circle_router)
api_router.include_router(chats_router)
api_router.include_router(storyblock_router)
api_router.include_router(payments_router)
api_router.include_router(community_router)


@api_router.get("/health", include_in_schema=True)
def health():
    return {
        "version": settings.VERSION,
        "hash": settings.GIT_HASH,
        "branch": settings.GIT_BRANCH,
    }


@api_router.get("/live", include_in_schema=True)
async def live(db=DBDep):
    # Check redis, db and centrifugo connections
    status = {}

    # Check Redis connection
    try:
        await test_broker_connection()
        status["broker"] = "ok"
    except Exception as e:
        status["broker"] = f"error: {e}"

    # Check DB connection
    try:
        async with db as session:
            await session.exec(text("SELECT 1"))
        status["db"] = "ok"
    except Exception as e:
        status["db"] = f"error: {e}"

    # Check Centrifugo connection
    try:
        info = await centrifuge.info()
        status["centrifugo"] = "ok" if len(info.nodes) > 0 else "error: no nodes"
    except Exception as e:
        status["centrifugo"] = f"error: {e}"

    if all(v == "ok" for v in status.values()):
        status["status"] = "ok"
        return JSONResponse(content=status, status_code=http_status.HTTP_200_OK)
    else:
        status["status"] = "error"
        return JSONResponse(content=status, status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.FIREBASE_CERTIFICATE:
        try:
            firebase_cert = json.loads(settings.FIREBASE_CERTIFICATE)
            firebase_cert["private_key"] = firebase_cert.get("private_key", "").replace("\\n", "\n")
            firebase_admin.initialize_app(credential=credentials.Certificate(firebase_cert))
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")

    yield


app = FastAPI(
    title="Recovered API",
    version=settings.VERSION,
    docs_url=None,
    openapi_url="/v1/openapi.json",
    redoc_url="/v1/docs",
    lifespan=lifespan,
    logger=logger,
)

@app.get("/.well-known/assetlinks.json", include_in_schema=False)
async def asset_links():
    return [{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "com.app.recovered",
            "sha256_cert_fingerprints": settings.ANDROID_SHA256_FINGERPRINTS
        }
    }]

@app.get("/.well-known/apple-app-site-association", include_in_schema=False)
async def apple_app_site_association():
    return {
        "applinks": {
            "apps": [],
            "details": [{
                "appID": settings.APPLE_APP_ID,
                "paths": ["*"]
            }]
        }
    }

app.add_middleware(MetricsMiddleware, app_name=settings.PROJECT, app_version=settings.VERSION)
app.include_router(api_router)

# Mount reporting sub-application
app.mount("/v1/reporting", reporting_app)

if settings.MONITORING_ENABLED:
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=get_tracer_provider(),
        meter_provider=get_meter_provider(),
        excluded_urls="/health,/live,/metrics",
    )
