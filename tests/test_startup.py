"""Test Application Startup and Initialization."""

from backend.app.main import app, create_application
from backend.app.core.config import settings


def test_application_initialization():
    """Verify application factory instantiates without error."""
    test_app = create_application()
    assert test_app is not None
    assert test_app.title == "SupplyChainAgent Production API"
    assert test_app.version == settings.APP_VERSION


def test_middleware_registered():
    """Verify essential middlewares are mounted."""
    middleware_names = [m.cls.__name__ for m in app.user_middleware]
    assert "RequestIdMiddleware" in middleware_names
    assert "TimingMiddleware" in middleware_names
    assert "CORSMiddleware" in middleware_names
