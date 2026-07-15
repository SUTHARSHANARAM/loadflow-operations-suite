import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine, SessionLocal
from app.models.role import Permission, Role, RolePermission
from app.models.org import Organization
from app.models.user import User
from app.auth.security import get_password_hash

PERMISSIONS = [
    "load.create",
    "load.assign_carrier",
    "load.override_compliance_flag",
    "rate.confirm",
    "load.update_status",
    "staff.manage",
    "pod.upload"
]

def init_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

    db = SessionLocal()
    try:
        # ── Seed Permissions ──────────────────────────────────────────
        print("Seeding permissions catalog...")
        for perm_name in PERMISSIONS:
            if not db.query(Permission).filter(Permission.permission_name == perm_name).first():
                db.add(Permission(permission_name=perm_name))
        db.commit()
        print("Permissions catalog seeded successfully!")

        # ── Skip or Re-seed if demo accounts already exist ────────────
        existing_broker = db.query(User).filter(User.email == "admin@broker.com").first()
        if existing_broker:
            # Verify if password hash matches the current security format
            from app.auth.security import verify_password
            if verify_password("Password123", existing_broker.password_hash):
                print("Demo accounts already exist and verified — skipping seed.")
                return
            else:
                print("Existing demo accounts found with invalid hash format — rebuilding...")
                db.delete(existing_broker)
                db.query(User).filter(User.email == "admin@carrier.com").delete()
                db.query(User).filter(User.email == "shipper@acme.com").delete()
                db.commit()

        # ── Broker Org + Admin ────────────────────────────────────────
        print("Seeding demo accounts...")
        broker_org = db.query(Organization).filter(Organization.name == "FastFreight Brokerage").first()
        if not broker_org:
            broker_org = Organization(name="FastFreight Brokerage", type="broker")
            db.add(broker_org)
            db.flush()

        all_perms = db.query(Permission).all()
        broker_admin_role = db.query(Role).filter(Role.org_id == broker_org.id, Role.role_name == "Broker Admin").first()
        if not broker_admin_role:
            broker_admin_role = Role(org_id=broker_org.id, role_name="Broker Admin")
            db.add(broker_admin_role)
            db.flush()
            for p in all_perms:
                db.add(RolePermission(role_id=broker_admin_role.id, permission_id=p.id))

        broker_admin = User(
            name="Broker Admin",
            email="admin@broker.com",
            password_hash=get_password_hash("Password123"),
            account_type="broker",
            org_id=broker_org.id,
            role_id=broker_admin_role.id
        )
        db.add(broker_admin)

        # ── Carrier Org + Admin ───────────────────────────────────────
        carrier_org = db.query(Organization).filter(Organization.name == "Swift Carriers LLC").first()
        if not carrier_org:
            carrier_org = Organization(name="Swift Carriers LLC", type="carrier")
            db.add(carrier_org)
            db.flush()
            # Also create compliance record for carrier
            from app.models.compliance import Compliance
            db.add(Compliance(carrier_id=carrier_org.id, authority_status="Inactive", approved_equipment="[]", approved_commodities="[]"))

        carrier_admin_role = db.query(Role).filter(Role.org_id == carrier_org.id, Role.role_name == "Carrier Admin").first()
        if not carrier_admin_role:
            carrier_admin_role = Role(org_id=carrier_org.id, role_name="Carrier Admin")
            db.add(carrier_admin_role)
            db.flush()
            for p in all_perms:
                db.add(RolePermission(role_id=carrier_admin_role.id, permission_id=p.id))

        carrier_admin = User(
            name="Carrier Admin",
            email="admin@carrier.com",
            password_hash=get_password_hash("Password123"),
            account_type="carrier",
            org_id=carrier_org.id,
            role_id=carrier_admin_role.id
        )
        db.add(carrier_admin)

        # ── Shipper Account ───────────────────────────────────────────
        shipper = User(
            name="Acme Shipper",
            email="shipper@acme.com",
            password_hash=get_password_hash("Password123"),
            account_type="shipper",
            org_id=None,
            role_id=None
        )
        db.add(shipper)

        db.commit()
        print("Demo accounts seeded successfully!")
        print("  Broker Admin  → admin@broker.com   / Password123")
        print("  Carrier Admin → admin@carrier.com  / Password123")
        print("  Shipper       → shipper@acme.com   / Password123")

    except Exception as e:
        print(f"Error during init: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()

