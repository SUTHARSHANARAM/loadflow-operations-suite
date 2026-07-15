from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import LoadCreate, LoadUpdate, LoadResponse
from app.services.load_service import LoadService
from app.services.state_machine import StateMachineService
from app.permissions import PermissionChecker, get_current_user
from app.models.user import User
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/loads", tags=["Loads & Shipments"])

# Permission checkers
load_create_guard = PermissionChecker("load.create")
load_assign_guard = PermissionChecker("load.assign_carrier")
pod_upload_guard = PermissionChecker("pod.upload")

class AssignCarrierRequest(BaseModel):
    carrier_id: int

class StatusTransitionRequest(BaseModel):
    status: str

class PodUploadRequest(BaseModel):
    pod_data: str  # Base64 encoded image string

@router.get("", response_model=List[LoadResponse])
def get_loads(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return LoadService.list_loads(db, current_user, origin, destination, status, search)

@router.post("", response_model=LoadResponse)
def create_load(
    schema: LoadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(load_create_guard)
):
    return LoadService.create_load(db, schema, current_user)

@router.get("/{load_id}", response_model=LoadResponse)
def get_load(
    load_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return LoadService.get_load_by_id(db, load_id, current_user)

@router.put("/{load_id}", response_model=LoadResponse)
def update_load(
    load_id: int,
    schema: LoadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(load_create_guard)
):
    return LoadService.update_load(db, load_id, schema, current_user)

@router.post("/{load_id}/assign", response_model=LoadResponse)
def assign_carrier(
    load_id: int,
    payload: AssignCarrierRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(load_assign_guard)
):
    return LoadService.assign_carrier(db, load_id, payload.carrier_id, current_user)

@router.post("/{load_id}/status", response_model=LoadResponse)
def transition_status(
    load_id: int,
    payload: StatusTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # State machine internal validation handles specific transition permissions
    return StateMachineService.transition_status(db, load_id, payload.status, current_user)

@router.post("/{load_id}/pod", response_model=LoadResponse)
def upload_pod(
    load_id: int,
    payload: PodUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(pod_upload_guard)
):
    # Validate load access and status
    load = LoadService.get_load_by_id(db, load_id, current_user)
    
    if load.status not in ["Delivered", "In Transit"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only upload POD when load is In Transit or Delivered"
        )
    
    load.pod_url = payload.pod_data
    db.commit()
    db.refresh(load)
    
    # Audit log
    from app.services.audit_service import AuditService
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        organization_id=current_user.org_id,
        action="POD_UPLOADED",
        target_type="load",
        target_id=str(load.id),
        details=f"Proof of Delivery document uploaded by {current_user.email}"
    )
    
    return load
