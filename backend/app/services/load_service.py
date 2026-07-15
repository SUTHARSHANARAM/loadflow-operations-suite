from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status
from app.models.load import Load
from app.models.user import User
from app.schemas import LoadCreate, LoadUpdate
from app.services.compliance_service import ComplianceService
from app.services.audit_service import AuditService
from typing import List, Optional

class LoadService:
    @staticmethod
    def get_load_by_id(db: Session, load_id: int, user: User) -> Load:
        load = db.query(Load).filter(Load.id == load_id).first()
        if not load:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")
        
        # Object-level scoping check
        if user.account_type == "shipper":
            if load.shipper_id != user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this load")
        elif user.account_type == "broker":
            if load.broker_id != user.org_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this load")
        elif user.account_type == "carrier":
            # Carrier staff see open (Posted) loads, or loads assigned to them
            if load.carrier_id != user.org_id and load.status != "Posted":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this load")
                
        return load

    @staticmethod
    def list_loads(
        db: Session,
        user: User,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Load]:
        query = db.query(Load)
        
        # 1. Scope query based on user account type
        if user.account_type == "shipper":
            query = query.filter(Load.shipper_id == user.id)
        elif user.account_type == "broker":
            query = query.filter(Load.broker_id == user.org_id)
        elif user.account_type == "carrier":
            query = query.filter(or_(Load.carrier_id == user.org_id, Load.status == "Posted"))

        # 2. Apply filters
        if origin:
            query = query.filter(Load.origin.ilike(f"%{origin}%"))
        if destination:
            query = query.filter(Load.destination.ilike(f"%{destination}%"))
        if status_filter:
            query = query.filter(Load.status == status_filter)
        if search:
            query = query.filter(
                or_(
                    Load.title.ilike(f"%{search}%"),
                    Load.origin.ilike(f"%{search}%"),
                    Load.destination.ilike(f"%{search}%"),
                    Load.commodity_type.ilike(f"%{search}%")
                )
            )
            
        return query.order_by(Load.created_at.desc()).all()

    @staticmethod
    def create_load(db: Session, schema: LoadCreate, broker_user: User) -> Load:
        # Validate that the shipper exists
        shipper = db.query(User).filter(User.id == schema.shipper_id, User.account_type == "shipper").first()
        if not shipper:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shipper ID selected")

        load = Load(
            title=schema.title,
            origin=schema.origin,
            destination=schema.destination,
            equipment_required=schema.equipment_required,
            commodity_type=schema.commodity_type,
            shipper_id=schema.shipper_id,
            broker_id=broker_user.org_id,
            status="Posted",
            compliance_flag=False
        )
        db.add(load)
        db.commit()
        db.refresh(load)

        AuditService.log_action(
            db=db,
            user_id=broker_user.id,
            user_email=broker_user.email,
            organization_id=broker_user.org_id,
            action="LOAD_CREATED",
            target_type="load",
            target_id=str(load.id),
            details=f"Load '{load.title}' posted. Origin: {load.origin}, Dest: {load.destination}"
        )
        return load

    @staticmethod
    def update_load(db: Session, load_id: int, schema: LoadUpdate, broker_user: User) -> Load:
        load = LoadService.get_load_by_id(db, load_id, broker_user)
        
        # Can only update before rate confirmed
        if load.status not in ["Posted", "Carrier Assigned"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Load details cannot be updated after rate confirmation"
            )

        if schema.shipper_id is not None:
            shipper = db.query(User).filter(User.id == schema.shipper_id, User.account_type == "shipper").first()
            if not shipper:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shipper ID")
            load.shipper_id = schema.shipper_id

        if schema.title is not None:
            load.title = schema.title
        if schema.origin is not None:
            load.origin = schema.origin
        if schema.destination is not None:
            load.destination = schema.destination
        if schema.equipment_required is not None:
            load.equipment_required = schema.equipment_required
        if schema.commodity_type is not None:
            load.commodity_type = schema.commodity_type
            
        db.commit()
        db.refresh(load)

        AuditService.log_action(
            db=db,
            user_id=broker_user.id,
            user_email=broker_user.email,
            organization_id=broker_user.org_id,
            action="LOAD_UPDATED",
            target_type="load",
            target_id=str(load.id),
            details=f"Updated details for Load {load.id}"
        )
        return load

    @staticmethod
    def assign_carrier(db: Session, load_id: int, carrier_org_id: int, broker_user: User) -> Load:
        load = LoadService.get_load_by_id(db, load_id, broker_user)
        
        if load.status != "Posted" and load.carrier_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Load already has an assigned carrier or has progressed past Posted"
            )
            
        # Verify carrier organization exists
        from app.models.org import Organization
        carrier_org = db.query(Organization).filter(Organization.id == carrier_org_id, Organization.type == "carrier").first()
        if not carrier_org:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid carrier organization ID")

        load.carrier_id = carrier_org_id
        load.status = "Carrier Assigned"
        
        # Check Compliance automatically
        is_compliant = ComplianceService.check_carrier_compliance(db, carrier_org_id, load)
        load.compliance_flag = not is_compliant
        
        db.commit()
        db.refresh(load)

        details = f"Assigned carrier '{carrier_org.name}' (ID: {carrier_org_id}) to Load {load.id}."
        if load.compliance_flag:
            details += " WARNING: Carrier compliance checks failed. Load flagged!"
            
        AuditService.log_action(
            db=db,
            user_id=broker_user.id,
            user_email=broker_user.email,
            organization_id=broker_user.org_id,
            action="CARRIER_ASSIGNED",
            target_type="load",
            target_id=str(load.id),
            details=details
        )
        return load
