from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.models.org import Organization
from app.models.role import Role, Permission, RolePermission
from app.models.compliance import Compliance
from app.schemas import UserRegister, UserLogin
from app.auth.security import get_password_hash, verify_password, create_access_token
from app.services.audit_service import AuditService
from typing import List

class AuthService:
    @staticmethod
    def register_user(db: Session, schema: UserRegister) -> User:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == schema.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered"
            )

        org_id = None
        role_id = None

        # Bootstrap Organization for Broker or Carrier
        if schema.account_type in ["broker", "carrier"]:
            if not schema.org_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization name is required for broker and carrier accounts"
                )
            
            # Check if organization name exists
            existing_org = db.query(Organization).filter(Organization.name == schema.org_name).first()
            if existing_org:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization name already exists"
                )

            # 1. Create Organization
            org = Organization(name=schema.org_name, type=schema.account_type)
            db.add(org)
            db.commit()
            db.refresh(org)
            org_id = org.id

            # If it's a carrier, bootstrap a compliance record
            if schema.account_type == "carrier":
                compliance = Compliance(
                    carrier_id=org.id,
                    authority_status="Inactive",
                    approved_equipment="[]",
                    approved_commodities="[]"
                )
                db.add(compliance)
                db.commit()

            # 2. Create default Admin Role for this Org
            admin_role = Role(org_id=org.id, role_name="Admin")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
            role_id = admin_role.id

            # 3. Associate all existing permissions in the catalog with this Admin role
            all_permissions = db.query(Permission).all()
            for perm in all_permissions:
                rp = RolePermission(role_id=admin_role.id, permission_id=perm.id)
                db.add(rp)
            db.commit()

        # Create User
        user = User(
            name=schema.name,
            email=schema.email,
            password_hash=get_password_hash(schema.password),
            account_type=schema.account_type,
            org_id=org_id,
            role_id=role_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Log Audit Trail
        AuditService.log_action(
            db=db,
            user_id=user.id,
            user_email=user.email,
            organization_id=org_id,
            action="USER_REGISTERED",
            target_type="user",
            target_id=str(user.id),
            details=f"User {user.email} registered as Org Admin for {schema.org_name}" if org_id else f"Shipper {user.email} registered."
        )

        return user

    @staticmethod
    def login_user(db: Session, schema: UserLogin) -> str:
        user = db.query(User).filter(User.email == schema.email).first()
        if not user or not verify_password(schema.password, user.password_hash):
            # Log denied login
            AuditService.log_action(
                db=db,
                user_email=schema.email,
                action="LOGIN_DENIED",
                details="Invalid email or password attempt"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Log successful login
        AuditService.log_action(
            db=db,
            user_id=user.id,
            user_email=user.email,
            organization_id=user.org_id,
            action="LOGIN_SUCCESSFUL",
            target_type="user",
            target_id=str(user.id)
        )

        # Return access token containing user_id
        return create_access_token(subject=user.id)

    @staticmethod
    def get_user_permissions(db: Session, user: User) -> List[str]:
        if user.account_type == "shipper":
            return []
        if not user.role_id:
            return []
        
        # Load permission names through RolePermission & Permission tables
        perms = (
            db.query(Permission.permission_name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id == user.role_id)
            .all()
        )
        return [p[0] for p in perms]
