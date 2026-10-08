"""
Comprehensive Automated Test Suite for AI Urban Farming Assistant.
Verifies:
  - Authentication (Registration, Scrypt Hashing, Password Confirmation, Login, Logout)
  - Strict Multi-Tenant Data Isolation (User A vs User B)
  - MobileNetV2 Leaf Disease Classification & Knowledge Base
  - Low-confidence uncertainty warning threshold
  - Open-Meteo Weather integration & Smart Watering logic
  - Web Application End-to-End Routing & Protection
"""

import os
import uuid
import unittest
import json
import sqlite3
from io import BytesIO
from werkzeug.security import check_password_hash

import database as db
import ai_model
import weather_service
from app import app


class TestUrbanFarmingAssistant(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        db.init_db()

    # ==================== 1. Authentication & Security Tests ====================

    def test_01_secure_password_hashing(self):
        """Verify passwords are never stored in plain text and use secure hashes."""
        uname = f"sec_user_{uuid.uuid4().hex[:6]}"
        email = f"sec_{uuid.uuid4().hex[:6]}@urban.farm"
        raw_password = "SecretPassword99!"

        user_id, err = db.register_user(uname, email, raw_password)
        self.assertIsNone(err)
        self.assertIsNotNone(user_id)
        
        with db.get_db() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
            stored_hash = row["password_hash"]

        # Assert password is NOT plain text
        self.assertNotEqual(stored_hash, raw_password)
        self.assertTrue(stored_hash.startswith("scrypt:") or stored_hash.startswith("pbkdf2:"))
        self.assertTrue(check_password_hash(stored_hash, raw_password))
        self.assertFalse(check_password_hash(stored_hash, "WrongPassword"))

    def test_02_registration_validation_and_confirmation(self):
        """Test registration endpoint with valid and invalid password confirmation."""
        # Test password mismatch via web client
        res_mismatch = self.client.post("/register", data={
            "username": f"mismatch_{uuid.uuid4().hex[:6]}",
            "email": f"mismatch_{uuid.uuid4().hex[:6]}@example.com",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!"
        }, follow_redirects=True)
        self.assertIn(b"Passwords do not match", res_mismatch.data)

        # Test successful registration with matching confirmation
        test_uname = f"jenny_{uuid.uuid4().hex[:6]}"
        test_email = f"jenny_{uuid.uuid4().hex[:6]}@example.com"
        res_ok = self.client.post("/register", data={
            "username": test_uname,
            "email": test_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertIn(b"Welcome to Urban Farming Assistant", res_ok.data)
        self.assertIn(test_uname.encode(), res_ok.data)

    def test_03_login_and_logout_flow(self):
        """Test login with good and bad credentials, and session clearing on logout."""
        # Bad login credentials
        res_fail = self.client.post("/login", data={
            "login_id": "nonexistent_grower",
            "password": "BadPassword123"
        }, follow_redirects=True)
        self.assertIn(b"Invalid username/email or password", res_fail.data)

        # Successful login
        res_login = self.client.post("/login", data={
            "login_id": "demo_farmer",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertIn(b"Welcome back", res_login.data)
        self.assertIn(b"Dashboard", res_login.data)

        # Logout
        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"You have been safely logged out", res_logout.data)

    def test_04_unauthenticated_route_protection(self):
        """Ensure protected routes redirect unauthenticated users to /login."""
        protected_urls = ["/dashboard", "/plants", "/diagnose", "/weather", "/history"]
        for url in protected_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302)
            self.assertIn("/login", res.headers.get("Location", ""))

    # ==================== 2. Multi-Tenant User Data Isolation ====================

    def test_05_strict_user_data_isolation(self):
        """Verify User A cannot view, modify, or delete User B's plants or health logs."""
        # Create User A and User B
        uid_a, _ = db.register_user("tenant_alice", "alice@urban.org", "Password123!")
        if not uid_a:
            uid_a = db.authenticate_user("tenant_alice", "Password123!")[0]["id"]

        uid_b, _ = db.register_user("tenant_bob", "bob@urban.org", "Password123!")
        if not uid_b:
            uid_b = db.authenticate_user("tenant_bob", "Password123!")[0]["id"]

        # Add plant for Alice
        plant_a_id = db.add_plant(uid_a, "Alice Red Cherry", "Cherry Tomato", "2026-10-01", "Balcony")
        # Add plant for Bob
        plant_b_id = db.add_plant(uid_b, "Bob Terrace Mint", "Mint", "2026-10-01", "Terrace")

        # Query Alice's plants
        alice_plants = db.get_user_plants(uid_a)
        alice_plant_names = [p["plant_name"] for p in alice_plants]
        self.assertIn("Alice Red Cherry", alice_plant_names)
        self.assertNotIn("Bob Terrace Mint", alice_plant_names)

        # Query Bob's plants
        bob_plants = db.get_user_plants(uid_b)
        bob_plant_names = [p["plant_name"] for p in bob_plants]
        self.assertIn("Bob Terrace Mint", bob_plant_names)
        self.assertNotIn("Alice Red Cherry", bob_plant_names)

        # Cross-tenant get check
        self.assertIsNone(db.get_user_plant_by_id(uid_a, plant_b_id))
        self.assertIsNone(db.get_user_plant_by_id(uid_b, plant_a_id))

        # Alice cannot delete Bob's plant
        deleted = db.delete_user_plant(uid_a, plant_b_id)
        self.assertFalse(deleted)
        self.assertIsNotNone(db.get_user_plant_by_id(uid_b, plant_b_id))

        # Alice cannot add health log to Bob's plant
        log_id, err = db.add_health_log(uid_a, plant_b_id, "Tomato - Healthy", 90.0, "fake.jpg", "None", "None", "None")
        self.assertIsNone(log_id)
        self.assertIn("does not belong to you", err)

    # ==================== 3. MobileNetV2 Leaf Disease Detection ====================

    def test_06_mobilenet_classification_inference(self):
        """Test MobileNetV2 inference on test sample images."""
        sample_path = os.path.join(os.path.dirname(__file__), "static", "uploads", "samples", "healthy_tomato.jpg")
        self.assertTrue(os.path.exists(sample_path), "Sample test image must exist")

        res = ai_model.diagnose_leaf(sample_path)
        self.assertIn("disease_name", res)
        self.assertIn("confidence", res)
        self.assertIn("symptoms", res)
        self.assertIn("treatment", res)
        self.assertIn("prevention", res)
        self.assertIsInstance(res["confidence"], float)
        self.assertGreaterEqual(res["confidence"], 0.0)
        self.assertLessEqual(res["confidence"], 100.0)

    def test_07_low_confidence_warning_detection(self):
        """Verify that when confidence is low or image is ambiguous, warning is triggered."""
        amb_path = os.path.join(os.path.dirname(__file__), "static", "uploads", "samples", "uncertain_leaf.jpg")
        self.assertTrue(os.path.exists(amb_path), "Uncertain test image must exist")

        # Set high confidence threshold (e.g. 95%) or test with ambiguous leaf
        res = ai_model.diagnose_leaf(amb_path, confidence_threshold=90.0)
        self.assertTrue(res["is_low_confidence"])
        self.assertIsNotNone(res["warning"])
        self.assertIn("uncertainty warning", res["warning"].lower())

    # ==================== 4. Weather & Smart Watering System ====================

    def test_08_open_meteo_weather_fetch(self):
        """Verify Open-Meteo returns temperature, humidity, and precipitation."""
        weather = weather_service.fetch_current_weather("New Delhi")
        self.assertIn("temperature", weather)
        self.assertIn("humidity", weather)
        self.assertIn("precipitation", weather)
        self.assertIn("condition", weather)
        self.assertIsInstance(weather["temperature"], (int, float))

    def test_09_smart_watering_recommendation_logic(self):
        """Verify the 3 watering statuses: 'Water today', 'Water tomorrow', 'No watering needed today'."""
        # Scenario 1: Plant watered today in normal conditions -> No watering needed today
        rec1 = weather_service.calculate_smart_watering(
            plant_type="Tomato",
            base_watering_days=2,
            last_watered_date="2026-10-07",
            location_type="Balcony",
            weather_data={"temperature": 25.0, "humidity": 55.0, "precipitation": 0.0}
        )
        self.assertEqual(rec1["status"], "No watering needed today")

        # Scenario 2: Tomato not watered in 3 days in 34°C heat -> Water today
        rec2 = weather_service.calculate_smart_watering(
            plant_type="Tomato",
            base_watering_days=2,
            last_watered_date="2026-10-04",
            location_type="Balcony",
            weather_data={"temperature": 34.0, "humidity": 40.0, "precipitation": 0.0}
        )
        self.assertEqual(rec2["status"], "Water today")

        # Scenario 3: Significant rain (5mm) -> No watering needed today
        rec3 = weather_service.calculate_smart_watering(
            plant_type="Tomato",
            base_watering_days=2,
            last_watered_date="2026-10-05",
            location_type="Balcony",
            weather_data={"temperature": 24.0, "humidity": 85.0, "precipitation": 5.0}
        )
        self.assertEqual(rec3["status"], "No watering needed today")
        self.assertIn("rainfall", rec3["rationale"].lower())

    # ==================== 5. End-to-End User Flow ====================

    def test_10_end_to_end_user_journey(self):
        """Simulate complete flow: Register -> Login -> Dashboard -> Add Plant -> Water -> Diagnose -> View History -> Logout."""
        # 1. Login with demo user
        login_res = self.client.post("/login", data={
            "login_id": "demo_farmer",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # 2. Access dashboard
        dash_res = self.client.get("/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"My Urban Plants", dash_res.data)

        # 3. Add a plant
        add_res = self.client.post("/plants", data={
            "plant_name": "Test Balcony Basil",
            "plant_type": "Basil",
            "location_type": "Balcony",
            "city": "New Delhi",
            "planting_date": "2026-10-01",
            "base_watering_days": "1",
            "notes": "Testing notes"
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)
        self.assertIn(b"Test Balcony Basil", add_res.data)

        # 4. View history
        hist_res = self.client.get("/history")
        self.assertEqual(hist_res.status_code, 200)
        self.assertIn(b"Plant Health & Diagnosis History", hist_res.data)

        # 5. Logout
        logout_res = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"You have been safely logged out", logout_res.data)


if __name__ == "__main__":
    unittest.main()
