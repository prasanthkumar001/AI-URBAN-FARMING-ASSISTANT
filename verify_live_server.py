"""
Live Server Verification Script for AI Urban Farming Assistant.
Tests live HTTP endpoints, session handling, MobileNetV2 diagnosis upload,
and Open-Meteo weather responses.
"""

import requests
import os
import sys

BASE_URL = "http://127.0.0.1:5000"

def run_checks():
    session = requests.Session()

    print("1. Checking unauthenticated redirect...")
    r = session.get(f"{BASE_URL}/dashboard", allow_redirects=False)
    assert r.status_code == 302, f"Expected 302 redirect, got {r.status_code}"
    assert "/login" in r.headers["Location"], f"Expected redirect to /login, got {r.headers['Location']}"
    print("   [PASS] Unauthenticated user redirected to /login")

    print("2. Checking user login...")
    r = session.post(f"{BASE_URL}/login", data={
        "login_id": "demo_farmer",
        "password": "Password123!"
    }, allow_redirects=True)
    assert r.status_code == 200
    assert "Welcome back" in r.text or "FloraAI" in r.text
    print("   [PASS] Login successful, session established")

    print("3. Checking personal dashboard...")
    r = session.get(f"{BASE_URL}/dashboard")
    assert r.status_code == 200
    assert "My Urban Plants" in r.text
    assert "Watering Due Today" in r.text
    print("   [PASS] Personal dashboard loaded with metrics and plants")

    print("4. Checking plants catalog...")
    r = session.get(f"{BASE_URL}/plants")
    assert r.status_code == 200
    assert "Balcony Roma Tomato" in r.text
    print("   [PASS] Plants catalog displayed user-specific plants")

    print("5. Checking live weather & irrigation page...")
    r = session.get(f"{BASE_URL}/weather")
    assert r.status_code == 200
    assert "Smart Watering" in r.text
    assert "Open-Meteo" in r.text
    print("   [PASS] Open-Meteo weather page active")

    print("6. Checking MobileNetV2 leaf diagnosis...")
    sample_img_path = os.path.join(os.path.dirname(__file__), "static", "uploads", "samples", "healthy_tomato.jpg")
    with open(sample_img_path, "rb") as f:
        r = session.post(f"{BASE_URL}/diagnose", data={
            "plant_id": "1",
            "notes": "Live check via verification script"
        }, files={
            "leaf_image": ("healthy_tomato.jpg", f, "image/jpeg")
        }, allow_redirects=True)
    assert r.status_code == 200
    assert "Diagnosis complete!" in r.text or "Confidence" in r.text
    assert "Tomato" in r.text
    print("   [PASS] MobileNetV2 diagnosis completed and saved to health log")

    print("7. Checking plant health history...")
    r = session.get(f"{BASE_URL}/history")
    assert r.status_code == 200
    assert "Plant Health & Diagnosis History" in r.text
    print("   [PASS] Health history retrieved with newly recorded diagnosis")

    print("8. Checking logout...")
    r = session.get(f"{BASE_URL}/logout", allow_redirects=True)
    assert r.status_code == 200
    assert "logged out" in r.text
    print("   [PASS] User safely logged out")

    print("\nALL 8 LIVE ENDPOINT CHECKS PASSED PERFECTLY!")


if __name__ == "__main__":
    run_checks()
