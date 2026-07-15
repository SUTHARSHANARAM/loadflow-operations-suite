import sys
import os
# Add current directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine, SessionLocal
from app.models.role import Permission

def init_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

    # Seed Permissions
    permissions_list = [
        "load.create",
        "load.assign_carrier",
        "load.override_compliance_flag",
        "rate.confirm",
        "load.update_status",
        "staff.manage",
        "pod.upload"
    ]

    db = SessionLocal()
    try:
        print("Seeding permissions catalog...")
        for perm_name in permissions_list:
            existing = db.query(Permission).filter(Permission.permission_name == perm_name).first()
            if not existing:
                perm = Permission(permission_name=perm_name)
                db.add(perm)
        db.commit()
        print("Permissions catalog seeded successfully!")
    except Exception as e:
        print(f"Error seeding permissions: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
