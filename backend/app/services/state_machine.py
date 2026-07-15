from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.load import Load
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.services.load_service import LoadService
from typing import List

STATUS_FLOW = [
    "Posted",
    "Carrier Assigned",
    "Rate Confirmed",
    "Dispatched",
    "In Transit",
    "Delivered",
    "POD Verified",
    "Closed"
]

class StateMachineService:
    @staticmethod
    def transition_status(db: Session, load_id: int, next_status: str, user: User) -> Load:
        # 1. Fetch load and check scoping
        load = LoadService.get_load_by_id(db, load_id, user)
        current_status = load.status

        # 2. Validate next status
        if next_status not in STATUS_FLOW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: '{next_status}'. Valid sequence is: {STATUS_FLOW}"
            )

        # 3. Enforce linear forward flow
        current_idx = STATUS_FLOW.index(current_status)
        next_idx = STATUS_FLOW.index(next_status)

        if next_idx <= current_idx:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition backwards or to same status. Current: '{current_status}', Target: '{next_status}'"
            )
        
        # Prevent skipping states
        if next_idx != current_idx + 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot skip statuses. Must transition sequentially. Next expected: '{STATUS_FLOW[current_idx + 1]}', Target: '{next_status}'"
            )

        # 4. Check specific transition requirements & permissions
        user_permissions = AuthService.get_user_permissions(db, user)

        # Shippers cannot update status
        if user.account_type == "shipper":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Shippers cannot change load status"
            )

        # E.g. Posted -> Carrier Assigned is handled by load assignment (we can also transition here but normally it's handled by assign_carrier)
        if next_status == "Carrier Assigned":
            if "load.assign_carrier" not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Requires 'load.assign_carrier' permission"
                )

        # Carrier Assigned -> Rate Confirmed
        elif next_status == "Rate Confirmed":
            # Check compliance flag block
            if load.compliance_flag:
                if "load.override_compliance_flag" in user_permissions:
                    # Log compliance override
                    AuditService.log_action(
                        db=db,
                        user_id=user.id,
                        user_email=user.email,
                        organization_id=user.org_id,
                        action="COMPLIANCE_OVERRIDDEN",
                        target_type="load",
                        target_id=str(load.id),
                        details=f"Compliance check warning bypassed by User {user.email} using override permission."
                    )
                else:
                    # Blocked!
                    AuditService.log_action(
                        db=db,
                        user_id=user.id,
                        user_email=user.email,
                        organization_id=user.org_id,
                        action="COMPLIANCE_BLOCK_TRIGGERED",
                        target_type="load",
                        target_id=str(load.id),
                        details=f"Blocked status update to Rate Confirmed for Load {load.id} due to non-compliant carrier."
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Transition blocked: Assigned carrier fails compliance requirements. Requires override permission."
                    )
            
            # Requires rate.confirm permission
            if "rate.confirm" not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Requires 'rate.confirm' permission to confirm rates"
                )

        # Other status updates (Dispatched, In Transit, Delivered, POD Verified, Closed)
        else:
            if "load.update_status" not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Requires 'load.update_status' permission"
                )

            # Delivered -> POD Verified requires pod_url to be present
            if next_status == "POD Verified" and not load.pod_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot verify POD: Proof of Delivery document has not been uploaded yet."
                )

        # 5. Execute transition and commit
        load.status = next_status
        db.commit()
        db.refresh(load)

        # Log transition
        AuditService.log_action(
            db=db,
            user_id=user.id,
            user_email=user.email,
            organization_id=user.org_id,
            action="STATUS_TRANSITION",
            target_type="load",
            target_id=str(load.id),
            old_value=current_status,
            new_value=next_status,
            details=f"Transitioned load status from '{current_status}' to '{next_status}'"
        )

        return load
