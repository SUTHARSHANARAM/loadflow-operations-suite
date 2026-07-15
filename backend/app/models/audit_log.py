from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String, nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    action = Column(String, nullable=False)  # e.g. "LOAD_CREATED", "STATUS_TRANSITION", "PERMISSION_DENIED", "OVERRIDE"
    target_type = Column(String, nullable=True)  # e.g. "load", "compliance", "role"
    target_id = Column(String, nullable=True)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    details = Column(String, nullable=True)

    user = relationship("User", back_populates="audit_logs")
    organization = relationship("Organization")
