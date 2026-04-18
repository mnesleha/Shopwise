import pytest
from httpx import AsyncClient
from sqlmodel import select

from app.models.main_models import LoginOTP

pytestmark = pytest.mark.asyncio


async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "currency" in data


async def test_create_invoice_success(client: AsyncClient):
    payload = {
        "amount": 5000,
        "reference": "TEST-ORDER-101",
        "webhookUrl": "https://example.com/webhook",
        "redirectUrl": "https://example.com/success"
    }

    response = await client.post("/api/create-invoice", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert "pageUrl" in data
    assert "/checkout/" in data["pageUrl"]


async def test_create_invoice_invalid_data(client: AsyncClient):
    payload = {
        "reference": "TEST-ORDER-FAIL",
        "webhookUrl": "https://example.com/webhook",
    }

    response = await client.post("/api/create-invoice", json=payload)

    assert response.status_code == 422


async def test_checkout_page_load(client: AsyncClient):
    payload = {
        "amount": 10000,
        "reference": "TEST-CHECKOUT-FLOW",
        "webhookUrl": "https://example.com/hook",
        "redirectUrl": "https://example.com/ok"
    }
    create_resp = await client.post("/api/create-invoice", json=payload)
    assert create_resp.status_code == 200
    page_url = create_resp.json()["pageUrl"]

    payment_id = page_url.split("/")[-1]

    checkout_resp = await client.get(f"/checkout/{payment_id}")

    assert checkout_resp.status_code == 200
    assert "TEST-CHECKOUT-FLOW" in checkout_resp.text


async def test_auth_code_persisted_and_verified(client: AsyncClient, db_session):
    email = "user@example.com"

    send_response = await client.post("/api/auth/send-code", json={"email": email})

    assert send_response.status_code == 200

    result = await db_session.execute(
        select(LoginOTP).where(LoginOTP.email == email).order_by(LoginOTP.created_at.desc())
    )
    stored_code = result.scalars().first()

    assert stored_code is not None
    assert len(stored_code.code) == 4

    verify_response = await client.post(
        "/api/auth/verify-code",
        json={"email": email, "code": stored_code.code}
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "ok"

    remaining = await db_session.execute(select(LoginOTP).where(LoginOTP.email == email))
    assert remaining.scalars().first() is None


async def test_auth_resend_invalidates_previous_code(client: AsyncClient, db_session):
    email = "resend@example.com"

    first_response = await client.post("/api/auth/send-code", json={"email": email})
    assert first_response.status_code == 200

    first_query = await db_session.execute(
        select(LoginOTP).where(LoginOTP.email == email).order_by(LoginOTP.created_at.desc())
    )
    first_code = first_query.scalars().first()
    assert first_code is not None

    second_response = await client.post("/api/auth/send-code", json={"email": email})
    assert second_response.status_code == 200

    second_query = await db_session.execute(
        select(LoginOTP).where(LoginOTP.email == email).order_by(LoginOTP.created_at.desc())
    )
    second_code = second_query.scalars().first()
    assert second_code is not None
    assert second_code.code != first_code.code

    invalid_response = await client.post(
        "/api/auth/verify-code",
        json={"email": email, "code": first_code.code}
    )

    assert invalid_response.status_code == 400
    assert invalid_response.json()["detail"] == "Invalid code"

    valid_response = await client.post(
        "/api/auth/verify-code",
        json={"email": email, "code": second_code.code}
    )

    assert valid_response.status_code == 200