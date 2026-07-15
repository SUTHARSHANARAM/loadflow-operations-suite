from sqlalchemy.orm import Session
from app.models.compliance import Compliance
from app.models.load import Load
from datetime import date, datetime
import json

class ComplianceService:
    @staticmethod
    def get_compliance(db: Session, carrier_id: int) -> Compliance:
        record = db.query(Compliance).filter(Compliance.carrier_id == carrier_id).first()
        if not record:
            record = Compliance(
                carrier_id=carrier_id,
                authority_status="Inactive",
                approved_equipment="[]",
                approved_commodities="[]"
            )
            db.add(record)
            db.commit()
            db.refresh(record)
        return record

    @staticmethod
    def update_compliance(
        db: Session, 
        carrier_id: int, 
        insurance_expiry: date = None, 
        authority_status: str = None, 
        approved_equipment: list = None, 
        approved_commodities: list = None
    ) -> Compliance:
        record = ComplianceService.get_compliance(db, carrier_id)
        
        if insurance_expiry is not None:
            record.insurance_expiry = insurance_expiry
        if authority_status is not None:
            record.authority_status = authority_status
        if approved_equipment is not None:
            record.approved_equipment = json.dumps(approved_equipment)
        if approved_commodities is not None:
            record.approved_commodities = json.dumps(approved_commodities)
            
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def check_carrier_compliance(db: Session, carrier_id: int, load: Load) -> bool:
        """
        Returns True if carrier is COMPLIANT, False if NON-COMPLIANT (triggers compliance_flag = True on load).
        """
        record = db.query(Compliance).filter(Compliance.carrier_id == carrier_id).first()
        if not record:
            return False

        # 1. Authority status check
        if record.authority_status != "Active":
            return False

        # 2. Insurance expiration check
        if not record.insurance_expiry:
            return False
        
        # Note: comparison between date and date
        if record.insurance_expiry < date.today():
            return False

        # 3. Equipment check
        try:
            approved_eqs = json.loads(record.approved_equipment) if record.approved_equipment else []
        except Exception:
            approved_eqs = []
        
        if load.equipment_required not in approved_eqs:
            return False

        # 4. Commodity check
        try:
            approved_coms = json.loads(record.approved_commodities) if record.approved_commodities else []
        except Exception:
            approved_coms = []

        if load.commodity_type not in approved_coms:
            return False

        return True
