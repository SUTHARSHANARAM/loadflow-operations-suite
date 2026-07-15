import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db
from app.main import app
from app.models.role import Permission, Role, RolePermission
from app.models.user import User

# Test Database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_loadflow.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency for tests
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True, scope="module")
def setup_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
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
    db = TestingSessionLocal()
    for perm_name in permissions_list:
        existing = db.query(Permission).filter(Permission.permission_name == perm_name).first()
        if not existing:
            perm = Permission(permission_name=perm_name)
            db.add(perm)
    db.commit()
    db.close()
    
    yield
    
    # Tear down tables
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_loadflow.db"):
        try:
            os.remove("./test_loadflow.db")
        except Exception:
            pass

client = TestClient(app)

def test_onboarding_and_authentication():
    # 1. Register Broker Admin
    response = client.post("/api/auth/register", json={
        "name": "Broker Admin",
        "email": "admin@broker.com",
        "password": "password123",
        "account_type": "broker",
        "org_name": "Broker Org"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@broker.com"
    assert data["account_type"] == "broker"
    assert "load.create" in data["permissions"] # Admin role must contain all permissions

    # 2. Login Broker Admin
    response = client.post("/api/auth/login", json={
        "email": "admin@broker.com",
        "password": "password123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Register Carrier Admin
    response = client.post("/api/auth/register", json={
        "name": "Carrier Admin",
        "email": "admin@carrier.com",
        "password": "password123",
        "account_type": "carrier",
        "org_name": "Carrier Org"
    })
    assert response.status_code == 200

    # 4. Register Shipper
    response = client.post("/api/auth/register", json={
        "name": "Shipper Client",
        "email": "shipper@shipper.com",
        "password": "password123",
        "account_type": "shipper"
    })
    assert response.status_code == 200
    shipper_id = response.json()["id"]

    return headers, shipper_id

def test_rbac_and_compliance():
    # Register Broker Admin
    resp = client.post("/api/auth/login", json={
        "email": "admin@broker.com",
        "password": "password123"
    })
    broker_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    # Register Shipper
    resp = client.post("/api/auth/login", json={
        "email": "shipper@shipper.com",
        "password": "password123"
    })
    shipper_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    shipper_me = client.get("/api/auth/me", headers=shipper_headers).json()
    shipper_id = shipper_me["id"]

    # Register Carrier
    resp = client.post("/api/auth/login", json={
        "email": "admin@carrier.com",
        "password": "password123"
    })
    carrier_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    carrier_me = client.get("/api/auth/me", headers=carrier_headers).json()
    carrier_org_id = carrier_me["org_id"]

    # 1. Post a load as Broker
    resp = client.post("/api/loads", headers=broker_headers, json={
        "title": "Electronics Shipment",
        "origin": "Los Angeles",
        "destination": "San Francisco",
        "equipment_required": "Reefer",
        "commodity_type": "Food",
        "shipper_id": shipper_id
    })
    assert resp.status_code == 200
    load_id = resp.json()["id"]

    # 2. Scoping check: Shipper should see it, but other shippers won't
    resp = client.get(f"/api/loads/{load_id}", headers=shipper_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Electronics Shipment"

    # 3. Scoping check: Carrier should see it because its status is Posted (available)
    resp = client.get(f"/api/loads/{load_id}", headers=carrier_headers)
    assert resp.status_code == 200

    # 4. Assign carrier to load
    resp = client.post(f"/api/loads/{load_id}/assign", headers=broker_headers, json={
        "carrier_id": carrier_org_id
    })
    assert resp.status_code == 200
    assert resp.json()["carrier_id"] == carrier_org_id
    # Since carrier has default inactive compliance (no expiry, inactive authority), compliance_flag should be True!
    assert resp.json()["compliance_flag"] is True

    # 5. Create a staff user with role that has "rate.confirm" and "load.update_status" but NOT "load.override_compliance_flag"
    # Get permissions list
    perms_resp = client.get("/api/rbac/permissions", headers=broker_headers)
    assert perms_resp.status_code == 200
    perms_list = perms_resp.json()
    rate_confirm_id = next(p["id"] for p in perms_list if p["permission_name"] == "rate.confirm")
    update_status_id = next(p["id"] for p in perms_list if p["permission_name"] == "load.update_status")

    # Create role
    role_resp = client.post("/api/rbac/roles", headers=broker_headers, json={
        "role_name": "Dispatcher",
        "permission_ids": [rate_confirm_id, update_status_id]
    })
    assert role_resp.status_code == 200
    dispatcher_role_id = role_resp.json()["id"]

    # Create staff user
    staff_resp = client.post("/api/rbac/staff", headers=broker_headers, json={
        "name": "Broker Dispatcher",
        "email": "dispatcher@broker.com",
        "password": "password123",
        "role_id": dispatcher_role_id
    })
    assert staff_resp.status_code == 200

    # Login as staff user
    staff_login_resp = client.post("/api/auth/login", json={
        "email": "dispatcher@broker.com",
        "password": "password123"
    })
    staff_headers = {"Authorization": f"Bearer {staff_login_resp.json()['access_token']}"}

    # Attempt to transition to Rate Confirmed - should fail because dispatcher does not have override permission!
    resp = client.post(f"/api/loads/{load_id}/status", headers=staff_headers, json={
        "status": "Rate Confirmed"
    })
    assert resp.status_code == 400
    assert "Transition blocked" in resp.json()["detail"]

    # 6. Update compliance record to make it active and valid
    # But wait, carrier has expired insurance or no insurance. Let's set Active authority and future expiry.
    resp = client.put(f"/api/compliance/carrier/{carrier_org_id}", headers=carrier_headers, json={
        "insurance_expiry": "2030-12-31",
        "authority_status": "Active",
        "approved_equipment": ["Reefer", "Flatbed"],
        "approved_commodities": ["Food", "General"]
    })
    assert resp.status_code == 200
    assert resp.json()["authority_status"] == "Active"

    # Now, check compliance again. Wait! Since compliance was updated, let's assign them again or override.
    # To check compliance automatically after updating it, let's re-assign or make sure the status transition works if compliance is now valid.
    # Wait, the status transition check evaluates compliance flag. Since the compliance flag is stored on the Load, let's verify if the state machine transition evaluates it dynamically.
    # Wait, in the state_machine.py code:
    # `if load.compliance_flag:` -> wait, load.compliance_flag was set to True at assignment time! If compliance record changes, the compliance flag is still True unless updated, or we re-assign.
    # Let's check: does update_compliance change the load flag? No, but let's re-run compliance check or let's use the override feature!
    # Let's test the override feature first. Let's propose a rate first.
    # Propose rate:
    resp = client.post(f"/api/rates/load/{load_id}", headers=broker_headers, json={
        "rate": 1500.00,
        "accessorials": 200.00
    })
    assert resp.status_code == 200
    rate_version = resp.json()["version"]

    # Confirm rate proposal as carrier admin (who has override/rate.confirm permission)
    # Wait! If they confirm it, the state machine transition to 'Rate Confirmed' will run.
    # Since compliance flag is True on the load, it will block it UNLESS confirming user has `load.override_compliance_flag`.
    # Let's verify that the Carrier Admin (who has ALL permissions since they are org admin) can override it.
    resp = client.post(f"/api/rates/load/{load_id}/confirm/{rate_version}", headers=carrier_headers)
    assert resp.status_code == 200
    assert resp.json()["confirmed_by"] is not None

    # Load status should now be Rate Confirmed!
    resp = client.get(f"/api/loads/{load_id}", headers=broker_headers)
    assert resp.json()["status"] == "Rate Confirmed"
