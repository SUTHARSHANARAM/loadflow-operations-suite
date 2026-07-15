from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, status
from app.models.rate_confirmation import RateConfirmation
from app.models.load import Load
from app.models.user import User
from app.services.state_machine import StateMachineService
from app.services.audit_service import AuditService
from app.services.load_service import LoadService
from datetime import datetime

class RateService:
    @staticmethod
    def create_rate_proposal(db: Session, load_id: int, rate: float, accessorials: float, broker_user: User) -> RateConfirmation:
        # Enforce that load exists and broker has access
        load = LoadService.get_load_by_id(db, load_id, broker_user)
        
        # Only allow rate configuration if load status is Posted or Carrier Assigned
        if load.status not in ["Posted", "Carrier Assigned"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add rate confirmation when load is in '{load.status}' state"
            )

        # Get latest version for this load
        latest = (
            db.query(RateConfirmation)
            .filter(RateConfirmation.load_id == load_id)
            .order_by(desc(RateConfirmation.version))
            .first()
        )
        next_version = (latest.version + 1) if latest else 1

        rate_conf = RateConfirmation(
            load_id=load_id,
            version=next_version,
            rate=rate,
            accessorials=accessorials
        )
        db.add(rate_conf)
        db.commit()
        db.refresh(rate_conf)

        AuditService.log_action(
            db=db,
            user_id=broker_user.id,
            user_email=broker_user.email,
            organization_id=broker_user.org_id,
            action="RATE_PROPOSED",
            target_type="rate_confirmation",
            target_id=str(rate_conf.id),
            details=f"Created rate proposal version {next_version} for Load {load_id}. Rate: ${rate}, Accessorials: ${accessorials}"
        )
        
        return rate_conf

    @staticmethod
    def confirm_rate_proposal(db: Session, load_id: int, version: int, confirming_user: User) -> RateConfirmation:
        # Fetch the proposal
        proposal = (
            db.query(RateConfirmation)
            .filter(RateConfirmation.load_id == load_id, RateConfirmation.version == version)
            .first()
        )
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rate confirmation version {version} not found for load {load_id}"
            )

        if proposal.confirmed_by is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This rate confirmation has already been signed/confirmed"
            )

        # Scoping verification: Only carrier assigned or broker staff can confirm
        load = LoadService.get_load_by_id(db, load_id, confirming_user)
        if confirming_user.account_type == "shipper":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Shippers cannot sign rate confirmations"
            )

        # Update confirmation details
        proposal.confirmed_by = confirming_user.id
        proposal.confirmed_at = datetime.utcnow()
        db.commit()

        # Trigger load state transition to 'Rate Confirmed' through state machine!
        StateMachineService.transition_status(db, load_id, "Rate Confirmed", confirming_user)

        AuditService.log_action(
            db=db,
            user_id=confirming_user.id,
            user_email=confirming_user.email,
            organization_id=confirming_user.org_id,
            action="RATE_CONFIRMED",
            target_type="rate_confirmation",
            target_id=str(proposal.id),
            details=f"Rate confirmation v{version} signed by {confirming_user.email} (load transitioned to Rate Confirmed)"
        )

        return proposal
