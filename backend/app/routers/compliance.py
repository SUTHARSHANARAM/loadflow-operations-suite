from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ComplianceUpdate, ComplianceResponse
from app.services.compliance_service import ComplianceService
from app.permissions import get_current_user
from app.models.user import User
import json

router = APIRouter(prefix="/compliance", tags=["Compliance Management"])

@router.get("/carrier/{carrier_id}", response_model=ComplianceResponse)
def get_compliance_record(
    carrier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Security scoping
    if current_user.account_type == "carrier":
        if current_user.org_id != carrier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to other carrier's compliance record")
    elif current_user.account_type == "shipper":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Shippers cannot view compliance records")
        
    record = ComplianceService.get_compliance(db, carrier_id)
    
    # Parse approved equipment and commodities arrays from JSON strings
    try:
        equipment = json.loads(record.approved_equipment)
    except Exception:
        equipment = []
    try:
        commodities = json.loads(record.approved_commodities)
    except Exception:
        commodities = []

    return {
        "id": record.id,
        "carrier_id": record.carrier_id,
        "insurance_expiry": record.insurance_expiry,
        "authority_status": record.authority_status,
        "approved_equipment": equipment,
        "approved_commodities": commodities
    }

@router.put("/carrier/{carrier_id}", response_model=ComplianceResponse)
def update_compliance_record(
    carrier_id: int,
    schema: ComplianceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.account_type != "carrier" or current_user.org_id != carrier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only carrier staff can update their own compliance documents"
        )
        
    from app.services.auth_service import AuthService
    perms = AuthService.get_user_permissions(db, current_user)
    if "staff.manage" not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires 'staff.manage' permission to update compliance settings"
        )

    record = ComplianceService.update_compliance(
        db=db,
        carrier_id=carrier_id,
        insurance_expiry=schema.insurance_expiry,
        authority_status=schema.authority_status,
        approved_equipment=schema.approved_equipment,
        approved_commodities=schema.approved_commodities
    )
    
    try:
        equipment = json.loads(record.approved_equipment)
    except Exception:
        equipment = []
    try:
        commodities = json.loads(record.approved_commodities)
    except Exception:
        commodities = []

    return {
        "id": record.id,
        "carrier_id": record.carrier_id,
        "insurance_expiry": record.insurance_expiry,
        "authority_status": record.authority_status,
        "approved_equipment": equipment,
        "approved_commodities": commodities
    }
