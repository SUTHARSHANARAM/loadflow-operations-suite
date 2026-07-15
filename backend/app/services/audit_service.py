from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog

class AuditService:
    @staticmethod
    def log_action(
        db: Session,
        user_id: int = None,
        user_email: str = None,
        organization_id: int = None,
        action: str = "",
        target_type: str = None,
        target_id: str = None,
        old_value: str = None,
        new_value: str = None,
        details: str = None
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            user_email=user_email,
            organization_id=organization_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            old_value=old_value,
            new_value=new_value,
            details=details
        )
        try:
            db.add(log)
            db.commit()
            db.refresh(log)
        except Exception as e:
            db.rollback()
            print(f"[AUDIT LOG SYSTEM ERROR] Failed to write audit log: {e}")
        
        # Output log denial or action directly to console
        print(f"[AUDIT LOG] Action: {action} | User: {user_email} | Org: {organization_id} | Target: {target_type} ({target_id}) | Details: {details}")
        return log

    @staticmethod
    def get_logs(db: Session, org_id: int = None, limit: int = 100):
        query = db.query(AuditLog)
        if org_id is not None:
            query = query.filter(AuditLog.organization_id == org_id)
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
