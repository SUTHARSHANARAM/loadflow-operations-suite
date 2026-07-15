from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class RateConfirmation(Base):
    __tablename__ = "rate_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    load_id = Column(Integer, ForeignKey("loads.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    rate = Column(Float, nullable=False)
    accessorials = Column(Float, default=0.0, nullable=False)
    confirmed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    load = relationship("Load", back_populates="rate_confirmations")
    confirmer = relationship("User", back_populates="confirmed_rates")
