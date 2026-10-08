"""
Database module for AI Urban Farming Assistant.
Handles SQLite schema, connection management, password hashing, and user data isolation.
"""

import sqlite3
import os
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "urban_farming.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database tables with indexes and foreign keys."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Plants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plant_name TEXT NOT NULL,
                plant_type TEXT NOT NULL,
                location_type TEXT DEFAULT 'Balcony',
                city TEXT DEFAULT 'New Delhi',
                planting_date TEXT NOT NULL,
                base_watering_days INTEGER DEFAULT 2,
                last_watered_date TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # 3. Health logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                disease TEXT NOT NULL,
                confidence REAL NOT NULL,
                image_path TEXT,
                symptoms TEXT,
                treatment TEXT,
                prevention TEXT,
                notes TEXT,
                diagnosis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_plants_user ON plants(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_plant ON health_logs(plant_id)")
        conn.commit()


# ==================== User Management ====================

def register_user(username, email, password):
    """
    Registers a new user with securely hashed password.
    Returns (user_id, None) on success, or (None, error_message) on failure.
    """
    username = (username or '').strip()
    email = (email or '').strip().lower()
    
    if not username:
        return None, "Username is required."
    if len(username) < 3:
        return None, "Username must be at least 3 characters long."
    if not email or '@' not in email or '.' not in email:
        return None, "Please enter a valid email address."
    if not password or len(password) < 6:
        return None, "Password must be at least 6 characters long."
        
    pwd_hash = generate_password_hash(password, method='scrypt')
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, pwd_hash)
            )
            conn.commit()
            return cursor.lastrowid, None
    except sqlite3.IntegrityError as e:
        err_msg = str(e).lower()
        if 'users.username' in err_msg or 'unique constraint failed: users.username' in err_msg:
            return None, "This username is already registered. Please choose another."
        elif 'users.email' in err_msg or 'unique constraint failed: users.email' in err_msg:
            return None, "An account with this email already exists."
        return None, "Username or email is already taken."


def authenticate_user(login_id, password):
    """
    Authenticates by username or email.
    Returns (user_dict, None) on success, or (None, error_message) on failure.
    """
    login_id = (login_id or '').strip()
    if not login_id or not password:
        return None, "Please provide both credentials."
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (login_id, login_id.lower())
        )
        user = cursor.fetchone()
        
    if not user:
        return None, "Invalid username/email or password."
        
    if not check_password_hash(user['password_hash'], password):
        return None, "Invalid username/email or password."
        
    return dict(user), None


def get_user_by_id(user_id):
    """Retrieve user dictionary by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None


# ==================== Plant Management (Isolated per user) ====================

def add_plant(user_id, plant_name, plant_type, planting_date, location_type='Balcony', city='New Delhi', base_watering_days=2, notes=''):
    """Adds a plant strictly scoped to the given user_id."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO plants (user_id, plant_name, plant_type, location_type, city, planting_date, base_watering_days, last_watered_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, date('now'), ?)
        """, (user_id, plant_name.strip(), plant_type.strip(), location_type, city.strip(), planting_date, int(base_watering_days), notes.strip()))
        conn.commit()
        return cursor.lastrowid


def get_user_plants(user_id):
    """Gets all plants belonging to a specific user with health stats."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*,
                   (SELECT COUNT(*) FROM health_logs hl WHERE hl.plant_id = p.id) AS total_diagnoses,
                   (SELECT hl.disease FROM health_logs hl WHERE hl.plant_id = p.id ORDER BY hl.diagnosis_date DESC LIMIT 1) AS last_diagnosis,
                   (SELECT hl.confidence FROM health_logs hl WHERE hl.plant_id = p.id ORDER BY hl.diagnosis_date DESC LIMIT 1) AS last_confidence,
                   (SELECT hl.diagnosis_date FROM health_logs hl WHERE hl.plant_id = p.id ORDER BY hl.diagnosis_date DESC LIMIT 1) AS last_diagnosis_date
            FROM plants p
            WHERE p.user_id = ?
            ORDER BY p.created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_user_plant_by_id(user_id, plant_id):
    """
    Fetch a single plant strictly verifying ownership by user_id.
    Prevents unauthorized cross-tenant data access.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM plants WHERE id = ? AND user_id = ?
        """, (plant_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_plant_watering(user_id, plant_id, watered_date=None):
    """Mark a plant as watered today (user-isolated)."""
    with get_db() as conn:
        cursor = conn.cursor()
        if watered_date:
            cursor.execute("""
                UPDATE plants SET last_watered_date = ? WHERE id = ? AND user_id = ?
            """, (watered_date, plant_id, user_id))
        else:
            cursor.execute("""
                UPDATE plants SET last_watered_date = date('now') WHERE id = ? AND user_id = ?
            """, (plant_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_user_plant(user_id, plant_id):
    """Delete a plant and its health logs, strictly checking user ownership."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM plants WHERE id = ? AND user_id = ?", (plant_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


# ==================== Health Logs Management ====================

def add_health_log(user_id, plant_id, disease, confidence, image_path, symptoms, treatment, prevention, notes=''):
    """
    Adds a diagnosis log after ensuring the plant belongs to user_id.
    """
    # Verify ownership
    plant = get_user_plant_by_id(user_id, plant_id)
    if not plant:
        return None, "Plant not found or does not belong to you."
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO health_logs (plant_id, disease, confidence, image_path, symptoms, treatment, prevention, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (plant_id, disease, float(confidence), image_path, symptoms, treatment, prevention, notes))
        conn.commit()
        return cursor.lastrowid, None


def get_user_health_logs(user_id, plant_id=None):
    """
    Gets diagnosis history strictly for plants owned by user_id.
    Optionally filters by specific plant_id.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if plant_id:
            cursor.execute("""
                SELECT hl.*, p.plant_name, p.plant_type, p.location_type
                FROM health_logs hl
                JOIN plants p ON hl.plant_id = p.id
                WHERE p.user_id = ? AND p.id = ?
                ORDER BY hl.diagnosis_date DESC
            """, (user_id, plant_id))
        else:
            cursor.execute("""
                SELECT hl.*, p.plant_name, p.plant_type, p.location_type
                FROM health_logs hl
                JOIN plants p ON hl.plant_id = p.id
                WHERE p.user_id = ?
                ORDER BY hl.diagnosis_date DESC
            """, (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
