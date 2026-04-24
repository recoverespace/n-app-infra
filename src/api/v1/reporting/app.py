from fastapi import FastAPI, HTTPException, Request, status
from starlette.responses import JSONResponse

from fastapi.openapi.docs import get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware

from api.settings import settings
from .users import router as users_router
from .chats import router as chats_router
from .facts import router as facts_router
from .messages import router as messages_router


# Create the reporting sub-application
reporting_app = FastAPI(
    title="Recovered Reporting API",
    description="Internal reporting API for data analytics and insights",
    version="1.0.0",
    docs_url=None,
    openapi_url=None,
    redoc_url=None,
)


@reporting_app.middleware("http")
async def auth(request: Request, call_next):
    # Check for API key
    auth_header = request.headers.get("Authorization")
    auth_query = request.query_params.get("api_key")
    auth_key = auth_header.replace("Bearer ", "") if auth_header else auth_query

    if not auth_key or auth_key != settings.REPORTING_API_KEY or not settings.REPORTING_API_KEY:

            return JSONResponse(
                status_code=401, 
                content={"error": "Unauthorized"}
            )
    
    response = await call_next(request)
    return response




@reporting_app.get("/docs")
async def get_documentation():
    return get_redoc_html(openapi_url="/v1/reporting/openapi.json?api_key=" + settings.REPORTING_API_KEY, title="docs")


@reporting_app.get("/openapi.json")
async def openapi():
    return get_openapi(title = "FastAPI", version="0.1.0", routes=reporting_app.routes)

# Include routers without API key dependency (middleware handles it)
reporting_app.include_router(users_router, tags=["Users"])
reporting_app.include_router(chats_router, tags=["Chats"])  
reporting_app.include_router(messages_router, tags=["Messages"])
reporting_app.include_router(facts_router, tags=["Facts"])