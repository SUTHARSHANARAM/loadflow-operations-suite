from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    account_type = Column(String, nullable=False)  # "broker" | "carrier" | "shipper"
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)

    org = relationship("Organization", back_populates="users")
    role = relationship("Role", back_populates="users")
    
    audit_logs = relationship("AuditLog", back_populates="user")
    confirmed_rates = relationship("RateConfirmation", back_populates="confirmer")
    shipper_loads = relationship("Load", back_populates="shipper")
