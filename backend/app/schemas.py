from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import date, datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None

# Org Schemas
class OrgCreate(BaseModel):
    name: str
    type: str  # "broker" | "carrier"

class OrgResponse(BaseModel):
    id: int
    name: str
    type: str

    class Config:
        from_attributes = True

# Permission & Role Schemas
class PermissionResponse(BaseModel):
    id: int
    permission_name: str

    class Config:
        from_attributes = True

class RoleCreate(BaseModel):
    role_name: str
    permission_ids: List[int]

class RoleResponse(BaseModel):
    id: int
    org_id: int
    role_name: str
    permissions: List[PermissionResponse]

    class Config:
        from_attributes = True

# User Schemas
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    account_type: str  # "broker" | "carrier" | "shipper"
    org_name: Optional[str] = None  # Required if broker or carrier (creates new org)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserStaffCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role_id: int  # Custom role to assign

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    account_type: str
    org_id: Optional[int] = None
    role_id: Optional[int] = None
    org: Optional[OrgResponse] = None
    permissions: List[str] = []  # Consolidated list of string permissions

    class Config:
        from_attributes = True

# Compliance Schemas
class ComplianceUpdate(BaseModel):
    insurance_expiry: Optional[date] = None
    authority_status: Optional[str] = None  # "Active" | "Inactive"
    approved_equipment: Optional[List[str]] = None
    approved_commodities: Optional[List[str]] = None

class ComplianceResponse(BaseModel):
    id: int
    carrier_id: int
    insurance_expiry: Optional[date] = None
    authority_status: str
    approved_equipment: List[str]
    approved_commodities: List[str]

    class Config:
        from_attributes = True

# Rate Confirmation Schemas
class RateConfirmationCreate(BaseModel):
    rate: float
    accessorials: float = 0.0

class RateConfirmationResponse(BaseModel):
    id: int
    load_id: int
    version: int
    rate: float
    accessorials: float
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Load Schemas
class LoadCreate(BaseModel):
    title: str
    origin: str
    destination: str
    equipment_required: str
    commodity_type: str
    shipper_id: int

class LoadUpdate(BaseModel):
    title: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    equipment_required: Optional[str] = None
    commodity_type: Optional[str] = None
    shipper_id: Optional[int] = None

class LoadResponse(BaseModel):
    id: int
    title: str
    origin: str
    destination: str
    equipment_required: str
    commodity_type: str
    shipper_id: int
    broker_id: int
    carrier_id: Optional[int] = None
    status: str
    compliance_flag: bool
    pod_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    rate_confirmations: List[RateConfirmationResponse] = []

    class Config:
        from_attributes = True

# Audit Log Schemas
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    organization_id: Optional[int] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: datetime
    details: Optional[str] = None

    class Config:
        from_attributes = True
