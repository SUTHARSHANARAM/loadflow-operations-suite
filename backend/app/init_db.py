import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine, SessionLocal
from app.models.role import Permission, Role, RolePermission
from app.models.org import Organization
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

        # ── Skip if demo accounts already exist ───────────────────────
        if db.query(User).filter(User.email == "admin@broker.com").first():
            print("Demo accounts already exist — skipping seed.")
            return

        # ── Broker Org + Admin ────────────────────────────────────────
        print("Seeding demo accounts...")
        broker_org = Organization(name="FastFreight Brokerage", type="broker")
        db.add(broker_org)
        db.flush()

        all_perms = db.query(Permission).all()
        broker_admin_role = Role(org_id=broker_org.id, role_name="Broker Admin")
        db.add(broker_admin_role)
        db.flush()
        for p in all_perms:
            db.add(RolePermission(role_id=broker_admin_role.id, permission_id=p.id))

        broker_admin = User(
            name="Broker Admin",
            email="admin@broker.com",
            password_hash=pwd_context.hash("Password123"),
            account_type="broker",
            org_id=broker_org.id,
            role_id=broker_admin_role.id
        )
        db.add(broker_admin)

        # ── Carrier Org + Admin ───────────────────────────────────────
        carrier_org = Organization(name="Swift Carriers LLC", type="carrier")
        db.add(carrier_org)
        db.flush()

        carrier_admin_role = Role(org_id=carrier_org.id, role_name="Carrier Admin")
        db.add(carrier_admin_role)
        db.flush()
        for p in all_perms:
            db.add(RolePermission(role_id=carrier_admin_role.id, permission_id=p.id))

        carrier_admin = User(
            name="Carrier Admin",
            email="admin@carrier.com",
            password_hash=pwd_context.hash("Password123"),
            account_type="carrier",
            org_id=carrier_org.id,
            role_id=carrier_admin_role.id
        )
        db.add(carrier_admin)

        # ── Shipper Account ───────────────────────────────────────────
        shipper = User(
            name="Acme Shipper",
            email="shipper@acme.com",
            password_hash=pwd_context.hash("Password123"),
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

