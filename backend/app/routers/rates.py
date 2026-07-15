from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import RateConfirmationCreate, RateConfirmationResponse
from app.services.rate_service import RateService
from app.permissions import PermissionChecker, get_current_user
from app.models.user import User

router = APIRouter(prefix="/rates", tags=["Rate Confirmations"])

# Require rate.confirm permission
rate_confirm_guard = PermissionChecker("rate.confirm")

@router.post("/load/{load_id}", response_model=RateConfirmationResponse)
def propose_rate(
    load_id: int,
    schema: RateConfirmationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(rate_confirm_guard)
):
    return RateService.create_rate_proposal(db, load_id, schema.rate, schema.accessorials, current_user)

@router.post("/load/{load_id}/confirm/{version}", response_model=RateConfirmationResponse)
def confirm_rate(
    load_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(rate_confirm_guard)
):
    return RateService.confirm_rate_proposal(db, load_id, version, current_user)
