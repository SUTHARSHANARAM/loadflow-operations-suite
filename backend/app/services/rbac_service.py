from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.models.role import Role, Permission, RolePermission
from app.auth.security import get_password_hash
from app.services.audit_service import AuditService
from typing import List

class RbacService:
    @staticmethod
    def list_permissions(db: Session) -> List[Permission]:
        return db.query(Permission).all()

    @staticmethod
    def create_role(db: Session, org_id: int, role_name: str, permission_ids: List[int]) -> Role:
        # Validate that the permissions exist
        perms = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        if len(perms) != len(permission_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some permission IDs are invalid"
            )
        
        role = Role(org_id=org_id, role_name=role_name)
        db.add(role)
        db.commit()
        db.refresh(role)

        for perm in perms:
            rp = RolePermission(role_id=role.id, permission_id=perm.id)
            db.add(rp)
        db.commit()
        db.refresh(role)
        
        # Audit log
        AuditService.log_action(
            db=db,
            organization_id=org_id,
            action="ROLE_CREATED",
            target_type="role",
            target_id=str(role.id),
            details=f"Created custom role '{role_name}' with {len(permission_ids)} permissions"
        )
        
        return role

    @staticmethod
    def list_roles(db: Session, org_id: int) -> List[Role]:
        return db.query(Role).filter(Role.org_id == org_id).all()

    @staticmethod
    def create_staff(db: Session, org_id: int, name: str, email: str, password: str, role_id: int) -> User:
        # Check if email is already taken
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already in use"
            )
        
        # Verify role belongs to the same org
        role = db.query(Role).filter(Role.id == role_id, Role.org_id == org_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role selected for organization"
            )
        
        org = role.org
        account_type = org.type

        staff = User(
            name=name,
            email=email,
            password_hash=get_password_hash(password),
            account_type=account_type,
            org_id=org_id,
            role_id=role_id
        )
        db.add(staff)
        db.commit()
        db.refresh(staff)

        # Audit log
        AuditService.log_action(
            db=db,
            organization_id=org_id,
            action="STAFF_CREATED",
            target_type="user",
            target_id=str(staff.id),
            details=f"Created staff member '{name}' ({email}) with role '{role.role_name}'"
        )
        
        return staff

    @staticmethod
    def list_staff(db: Session, org_id: int) -> List[User]:
        return db.query(User).filter(User.org_id == org_id).all()
