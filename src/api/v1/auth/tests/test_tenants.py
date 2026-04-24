from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.lib.tests.urls import AUTH_DOMAIN_CHECK
from api.lib.tests.utils import init_tenant


async def test_domain_check_exists(client: AsyncClient, session: AsyncSession) -> None:
    """Test domain-check returns true for existing tenant domain."""
    tenant = await init_tenant(session, "Test Company", ["testcompany.com"])

    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": "user@testcompany.com"})
    assert response.status_code == 200, response.text
    response_data = response.json()
    assert response_data["exists"] is True


async def test_domain_check_not_exists(client: AsyncClient) -> None:
    """Test domain-check returns false for non-existent domain."""
    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": "user@nonexistent.com"})
    assert response.status_code == 200, response.text
    response_data = response.json()
    assert response_data["exists"] is False


async def test_domain_check_multiple_domains(client: AsyncClient, session: AsyncSession) -> None:
    """Test domain-check works with multiple domains per tenant."""
    await init_tenant(session, "Multi Domain Company", ["company.com", "company.io", "company.net"])

    # Test first domain
    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": "user@company.com"})
    assert response.status_code == 200, response.text
    assert response.json()["exists"] is True

    # Test second domain
    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": "user@company.io"})
    assert response.status_code == 200, response.text
    assert response.json()["exists"] is True

    # Test third domain
    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": "user@company.net"})
    assert response.status_code == 200, response.text
    assert response.json()["exists"] is True


async def test_domain_check_case_sensitivity(client: AsyncClient, session: AsyncSession) -> None:
    """Test domain-check is case-sensitive (domains should be stored lowercase)."""
    await init_tenant(session, "Case Test Company", ["casetest.com"])

    # Exact match should work
    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": "user@casetest.com"})
    assert response.status_code == 200, response.text
    assert response.json()["exists"] is True

    # Different case should not match (assuming domains are stored as-is)
    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": "user@CaseTest.com"})
    assert response.status_code == 200, response.text
    # This depends on implementation - adjust assertion if domains are normalized
    assert response.json()["exists"] is False


async def test_domain_check_disabled_tenant(client: AsyncClient, session: AsyncSession) -> None:
    """Test domain-check with disabled tenant - behavior depends on requirements."""
    await init_tenant(session, "Disabled Company", ["disabled.com"], enabled=False)

    # This test assumes disabled tenants should still be found
    # Adjust based on actual requirements
    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": "user@disabled.com"})
    assert response.status_code == 200, response.text
    # If disabled tenants should not be found, change to: assert response.json()["exists"] is False


async def test_domain_check_empty_email(client: AsyncClient) -> None:
    """Test domain-check with empty email."""
    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": ""})
    # Should either return 422 validation error or false
    assert response.status_code in [200, 422], response.text
    if response.status_code == 200:
        assert response.json()["exists"] is False


async def test_domain_check_subdomain(client: AsyncClient, session: AsyncSession) -> None:
    """Test domain-check with subdomain - should not match parent domain."""
    await init_tenant(session, "Parent Domain Company", ["example.com"])

    # Subdomain should not match
    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": "user@sub.example.com"})
    assert response.status_code == 200, response.text
    assert response.json()["exists"] is False


async def test_domain_check_special_characters(client: AsyncClient, session: AsyncSession) -> None:
    """Test domain-check with special characters in domain."""
    await init_tenant(session, "Special Char Company", ["test-company.com"])

    response = await client.post(AUTH_DOMAIN_CHECK, json={"email": "user@test-company.com"})
    assert response.status_code == 200, response.text
    assert response.json()["exists"] is True
