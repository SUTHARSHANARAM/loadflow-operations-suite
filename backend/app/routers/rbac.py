from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import RoleCreate, RoleResponse, PermissionResponse, UserStaffCreate, UserResponse, OrgResponse
from app.services.rbac_service import RbacService
from app.services.auth_service import AuthService
from app.permissions import PermissionChecker, get_current_user
from app.models.user import User
from typing import List

router = APIRouter(prefix="/rbac", tags=["RBAC & Staff Management"])

# Guard all routes with staff.manage checker
staff_manage_guard = PermissionChecker("staff.manage")

@router.get("/permissions", response_model=List[PermissionResponse])
def get_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_manage_guard)
):
    return RbacService.list_permissions(db)

@router.post("/roles", response_model=RoleResponse)
def create_role(
    schema: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_manage_guard)
):
    role = RbacService.create_role(db, current_user.org_id, schema.role_name, schema.permission_ids)
    return role

@router.get("/roles", response_model=List[RoleResponse])
def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_manage_guard)
):
    return RbacService.list_roles(db, current_user.org_id)

@router.post("/staff", response_model=UserResponse)
def create_staff(
    schema: UserStaffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_manage_guard)
):
    staff = RbacService.create_staff(
        db, 
        current_user.org_id, 
        schema.name, 
        schema.email, 
        schema.password, 
        schema.role_id
    )
    perms = AuthService.get_user_permissions(db, staff)
    return {
        "id": staff.id,
        "name": staff.name,
        "email": staff.email,
        "account_type": staff.account_type,
        "org_id": staff.org_id,
        "role_id": staff.role_id,
        "org": staff.org,
        "permissions": perms
    }

@router.get("/staff", response_model=List[UserResponse])
def get_staff(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_manage_guard)
):
    staff_members = RbacService.list_staff(db, current_user.org_id)
    response_list = []
    for staff in staff_members:
        perms = AuthService.get_user_permissions(db, staff)
        response_list.append({
            "id": staff.id,
            "name": staff.name,
            "email": staff.email,
            "account_type": staff.account_type,
            "org_id": staff.org_id,
            "role_id": staff.role_id,
            "org": staff.org,
            "permissions": perms
        })
    return response_list

@router.get("/carriers", response_model=List[OrgResponse])
def get_carriers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.account_type != "broker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only brokers can list carriers"
        )
    from app.models.org import Organization
    return db.query(Organization).filter(Organization.type == "carrier").all()

@router.get("/shippers", response_model=List[UserResponse])
def get_shippers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.account_type != "broker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only brokers can list shippers"
        )
    shippers = db.query(User).filter(User.account_type == "shipper").all()
    return [{
        "id": s.id,
        "name": s.name,
        "email": s.email,
        "account_type": s.account_type,
        "org_id": s.org_id,
        "role_id": s.role_id,
        "org": s.org,
        "permissions": []
    } for s in shippers]

