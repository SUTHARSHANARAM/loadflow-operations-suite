from sqlalchemy import Column, Integer, ForeignKey, Date, String
from sqlalchemy.orm import relationship
from app.database import Base

class Compliance(Base):
    __tablename__ = "compliance_records"

    id = Column(Integer, primary_key=True, index=True)
    carrier_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False)
    insurance_expiry = Column(Date, nullable=True)
    authority_status = Column(String, default="Inactive", nullable=False)  # "Active" | "Inactive"
    approved_equipment = Column(String, default="[]", nullable=False)  # JSON list, e.g. '["Flatbed", "Reefer"]'
    approved_commodities = Column(String, default="[]", nullable=False)  # JSON list, e.g. '["Food", "General"]'

    carrier = relationship("Organization", back_populates="compliance")
