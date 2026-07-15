from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserRegister, UserLogin, UserResponse, Token
from app.services.auth_service import AuthService
from app.permissions import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse)
def register(schema: UserRegister, db: Session = Depends(get_db)):
    user = AuthService.register_user(db, schema)
    perms = AuthService.get_user_permissions(db, user)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "account_type": user.account_type,
        "org_id": user.org_id,
        "role_id": user.role_id,
        "org": user.org,
        "permissions": perms
    }

@router.post("/login", response_model=Token)
def login(schema: UserLogin, db: Session = Depends(get_db)):
    token = AuthService.login_user(db, schema)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    perms = AuthService.get_user_permissions(db, current_user)
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "account_type": current_user.account_type,
        "org_id": current_user.org_id,
        "role_id": current_user.role_id,
        "org": current_user.org,
        "permissions": perms
    }
