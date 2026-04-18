import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from sqlmodel import select

from app.database.core.session import get_db
from fastapi import Depends
from app.models.main_models import LoginOTP
from app.security.crypto import generate_secure_otp
from app.services.smtp_service import send_otp_email

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
)


class EmailRequest(BaseModel):
    email: str


class VerifyCodeRequest(BaseModel):
    email: str
    code: str


@router.post("/send-code")
async def auth_send_code(
    req: EmailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Auth code requested for {req.email}")
    code = generate_secure_otp()
    await db.execute(delete(LoginOTP).where(LoginOTP.email == req.email))
    db.add(LoginOTP(email=req.email, code=code))
    await db.commit()
    background_tasks.add_task(send_otp_email, req.email, code)
    return {"status": "sent", "message": "Code sent"}


@router.post("/verify-code")
async def auth_verify_code(req: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"Verifying code for {req.email}")
    result = await db.execute(
        select(LoginOTP)
        .where(LoginOTP.email == req.email)
        .order_by(LoginOTP.created_at.desc())
    )
    stored_code = result.scalars().first()

    if not stored_code:
        logger.warning(f"Code expired or not found for {req.email}")
        raise HTTPException(400, "Code expired or not found")

    if stored_code.expires_at < datetime.utcnow():
        await db.execute(delete(LoginOTP).where(LoginOTP.email == req.email))
        await db.commit()
        logger.warning(f"Expired code attempt for {req.email}")
        raise HTTPException(400, "Code expired or not found")

    if stored_code.code != req.code:
        logger.warning(f"Invalid code attempt for {req.email}")
        raise HTTPException(400, "Invalid code")

    await db.execute(delete(LoginOTP).where(LoginOTP.email == req.email))
    await db.commit()
    logger.info(f"User {req.email} verified successfully")
    return {"status": "ok", "message": "Verified"}