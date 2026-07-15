from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Load(Base):
    __tablename__ = "loads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    equipment_required = Column(String, nullable=False)  # e.g. "Flatbed", "Reefer"
    commodity_type = Column(String, nullable=False)      # e.g. "Food", "General"

    shipper_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    broker_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    carrier_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)

    status = Column(String, default="Posted", nullable=False)  # Posted, Carrier Assigned, Rate Confirmed, etc.
    compliance_flag = Column(Boolean, default=False, nullable=False)
    pod_url = Column(String, nullable=True)  # Holds base64 encoded document image

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    shipper = relationship("User", back_populates="shipper_loads")
    broker = relationship("Organization", foreign_keys=[broker_id])
    carrier = relationship("Organization", foreign_keys=[carrier_id])
    rate_confirmations = relationship("RateConfirmation", back_populates="load", cascade="all, delete-orphan")
