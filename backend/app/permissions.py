from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from app.database import get_db
from app.models.user import User
from app.auth.security import SECRET_KEY, ALGORITHM
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService

security_scheme = HTTPBearer()

def get_current_user(
    db: Session = Depends(get_db),
    token_credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = token_credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except Exception:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

class PermissionChecker:
    def __init__(self, permission_name: str):
        self.permission_name = permission_name

    def __call__(self, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> User:
        permissions = AuthService.get_user_permissions(db, current_user)
        if self.permission_name not in permissions:
            # Log permission denied
            AuditService.log_action(
                db=db,
                user_id=current_user.id,
                user_email=current_user.email,
                organization_id=current_user.org_id,
                action="PERMISSION_DENIED",
                target_type="permission",
                target_id=self.permission_name,
                details=f"User {current_user.email} attempted to perform action requiring '{self.permission_name}' but was blocked."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Requires '{self.permission_name}'"
            )
        return current_user
