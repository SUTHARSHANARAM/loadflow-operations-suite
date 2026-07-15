from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import AuditLogResponse
from app.services.audit_service import AuditService
from app.permissions import get_current_user
from app.models.user import User
from typing import List

router = APIRouter(prefix="/logs", tags=["Audit Log System"])

@router.get("", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.account_type not in ["broker", "carrier"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to audit logs"
        )
    return AuditService.get_logs(db, org_id=current_user.org_id, limit=limit)
