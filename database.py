"""
Database module for KrishiNova — Urban Farming & Garden Business Platform.
Handles SQLite schema, migrations, password hashing, user/business data isolation,
and multi-language preferences (English, Gujarati, Hindi, Telugu).
"""

import sqlite3
import os
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "urban_farming.db")

# Default Plant Preferences
DEFAULT_PLANT_PREFERENCES = {
    "tomato": {"opt_min": 18.0, "opt_max": 27.0, "min": 10.0, "max": 35.0, "water_days": 2, "sunlight": "Full Sun (6-8 hrs)"},
    "cherry tomato": {"opt_min": 18.0, "opt_max": 28.0, "min": 10.0, "max": 35.0, "water_days": 2, "sunlight": "Full Sun (6-8 hrs)"},
    "bell pepper": {"opt_min": 20.0, "opt_max": 30.0, "min": 15.0, "max": 36.0, "water_days": 3, "sunlight": "Full Sun (6 hrs)"},
    "chilli": {"opt_min": 20.0, "opt_max": 32.0, "min": 15.0, "max": 36.0, "water_days": 3, "sunlight": "Full Sun (6-8 hrs)"},
    "pepper": {"opt_min": 20.0, "opt_max": 30.0, "min": 15.0, "max": 36.0, "water_days": 3, "sunlight": "Full Sun (6 hrs)"},
    "basil": {"opt_min": 18.0, "opt_max": 30.0, "min": 12.0, "max": 35.0, "water_days": 1, "sunlight": "Partial to Full Sun (4-6 hrs)"},
    "mint": {"opt_min": 15.0, "opt_max": 25.0, "min": 8.0, "max": 30.0, "water_days": 1, "sunlight": "Partial Shade (3-4 hrs)"},
    "coriander": {"opt_min": 15.0, "opt_max": 24.0, "min": 8.0, "max": 28.0, "water_days": 2, "sunlight": "Morning Sun / Partial Shade"},
    "cilantro": {"opt_min": 15.0, "opt_max": 24.0, "min": 8.0, "max": 28.0, "water_days": 2, "sunlight": "Morning Sun / Partial Shade"},
    "spinach": {"opt_min": 12.0, "opt_max": 22.0, "min": 5.0, "max": 26.0, "water_days": 2, "sunlight": "Partial Sun (4 hrs)"},
    "lettuce": {"opt_min": 12.0, "opt_max": 22.0, "min": 5.0, "max": 26.0, "water_days": 2, "sunlight": "Partial Shade (3-5 hrs)"},
    "cucumber": {"opt_min": 20.0, "opt_max": 30.0, "min": 15.0, "max": 35.0, "water_days": 2, "sunlight": "Full Sun (6-8 hrs)"},
    "strawberry": {"opt_min": 15.0, "opt_max": 25.0, "min": 6.0, "max": 30.0, "water_days": 2, "sunlight": "Full Sun (6 hrs)"},
    "succulent": {"opt_min": 18.0, "opt_max": 32.0, "min": 10.0, "max": 40.0, "water_days": 7, "sunlight": "Bright Indirect to Full Sun"},
    "cactus": {"opt_min": 18.0, "opt_max": 35.0, "min": 8.0, "max": 42.0, "water_days": 8, "sunlight": "Direct Sunlight"},
    "aloe vera": {"opt_min": 18.0, "opt_max": 30.0, "min": 10.0, "max": 38.0, "water_days": 7, "sunlight": "Bright Indirect Sun"},
    "other": {"opt_min": 18.0, "opt_max": 28.0, "min": 10.0, "max": 35.0, "water_days": 2, "sunlight": "Medium to Full Sun"}
}


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def get_existing_columns(cursor, table_name):
    """Returns set of column names for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row["name"].lower() for row in cursor.fetchall()}


def init_db():
    """Initializes tables and safely runs non-destructive migrations."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Base Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'home_gardener',
                preferred_language TEXT DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Base Plants table
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
                growth_stage TEXT DEFAULT 'Vegetative',
                soil_moisture TEXT DEFAULT 'Moderate',
                preferred_temp_min REAL DEFAULT 10.0,
                preferred_temp_max REAL DEFAULT 35.0,
                preferred_temp_optimal_min REAL DEFAULT 18.0,
                preferred_temp_optimal_max REAL DEFAULT 27.0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # 3. Base Health logs table
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

        # 4. Plant preferences reference table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plant_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_key TEXT UNIQUE NOT NULL,
                crop_name TEXT NOT NULL,
                optimal_temp_min REAL NOT NULL,
                optimal_temp_max REAL NOT NULL,
                absolute_temp_min REAL NOT NULL,
                absolute_temp_max REAL NOT NULL,
                base_watering_days INTEGER DEFAULT 2,
                sunlight_need TEXT,
                common_diseases TEXT,
                care_tips TEXT
            )
        """)

        # 5. Weather alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plant_id INTEGER,
                business_id INTEGER,
                severity TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                affected_name TEXT NOT NULL,
                weather_value TEXT,
                preferred_range TEXT,
                explanation TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                expected_time TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                is_resolved INTEGER DEFAULT 0,
                dedup_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
            )
        """)

        # 6. Watering logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watering_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                watered_date TEXT NOT NULL,
                soil_moisture_before TEXT,
                amount_ml INTEGER DEFAULT 500,
                notes TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 7. Businesses table (Nursery / Garden Business Platform)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                business_type TEXT DEFAULT 'Plant Nursery & Garden Centre',
                address TEXT,
                city TEXT DEFAULT 'New Delhi',
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 8. Business members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'staff',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(business_id, user_id),
                FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 9. Nursery Inventory Items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL,
                plant_name TEXT NOT NULL,
                species TEXT,
                category TEXT DEFAULT 'Vegetable',
                quantity INTEGER DEFAULT 0,
                low_stock_threshold INTEGER DEFAULT 5,
                purchase_cost REAL DEFAULT 0.0,
                selling_price REAL DEFAULT 0.0,
                supplier TEXT,
                location_zone TEXT DEFAULT 'Greenhouse A',
                health_status TEXT DEFAULT 'Healthy',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
            )
        """)

        # 10. Inventory movements (Sales, Restocks, Wastage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                business_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity_change INTEGER NOT NULL,
                previous_qty INTEGER NOT NULL,
                new_qty INTEGER NOT NULL,
                unit_price REAL DEFAULT 0.0,
                notes TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE CASCADE,
                FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 11. Commercial Plant Batches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plant_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL,
                batch_name TEXT NOT NULL,
                plant_type TEXT NOT NULL,
                growing_area TEXT DEFAULT 'Greenhouse A',
                quantity INTEGER DEFAULT 20,
                health_status TEXT DEFAULT 'Good',
                manager_reviewed INTEGER DEFAULT 0,
                review_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
            )
        """)

        # 12. Sales Records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                item_id INTEGER,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_amount REAL NOT NULL,
                estimated_cogs REAL DEFAULT 0.0,
                notes TEXT,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_plants_user ON plants(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_plant ON health_logs(plant_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user ON weather_alerts(user_id, is_resolved)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_biz ON inventory_items(business_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_batches_biz ON plant_batches(business_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_biz ON sales_records(business_id)")
        conn.commit()

        # Run non-destructive column migrations on existing tables
        _run_column_migrations(cursor)
        _seed_default_preferences(cursor)
        conn.commit()


def _run_column_migrations(cursor):
    """Adds missing columns safely to preexisting tables."""
    # Check users table
    u_cols = get_existing_columns(cursor, "users")
    if "role" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'home_gardener'")
    if "preferred_language" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN preferred_language TEXT DEFAULT 'en'")

    # Check plants table
    p_cols = get_existing_columns(cursor, "plants")
    if "growth_stage" not in p_cols:
        cursor.execute("ALTER TABLE plants ADD COLUMN growth_stage TEXT DEFAULT 'Vegetative'")
    if "soil_moisture" not in p_cols:
        cursor.execute("ALTER TABLE plants ADD COLUMN soil_moisture TEXT DEFAULT 'Moderate'")
    if "preferred_temp_min" not in p_cols:
        cursor.execute("ALTER TABLE plants ADD COLUMN preferred_temp_min REAL DEFAULT 10.0")
    if "preferred_temp_max" not in p_cols:
        cursor.execute("ALTER TABLE plants ADD COLUMN preferred_temp_max REAL DEFAULT 35.0")
    if "preferred_temp_optimal_min" not in p_cols:
        cursor.execute("ALTER TABLE plants ADD COLUMN preferred_temp_optimal_min REAL DEFAULT 18.0")
    if "preferred_temp_optimal_max" not in p_cols:
        cursor.execute("ALTER TABLE plants ADD COLUMN preferred_temp_optimal_max REAL DEFAULT 27.0")

    # Check weather_alerts table for dedup_hash
    a_cols = get_existing_columns(cursor, "weather_alerts")
    if "dedup_hash" not in a_cols:
        cursor.execute("ALTER TABLE weather_alerts ADD COLUMN dedup_hash TEXT")


def _seed_default_preferences(cursor):
    """Seeds default plant preferences table if empty."""
    cursor.execute("SELECT COUNT(*) FROM plant_preferences")
    if cursor.fetchone()[0] == 0:
        pref_data = [
            ("tomato", "Tomato (Roma, Cherry, Beefsteak)", 18.0, 27.0, 10.0, 35.0, 2, "Full Sun (6-8 hrs)", "Early Blight, Late Blight, Bacterial Spot", "Mulch container soil, water early morning at root base."),
            ("bell pepper", "Bell Pepper / Capsicum", 20.0, 30.0, 15.0, 36.0, 3, "Full Sun (6 hrs)", "Anthracnose, Bacterial Leaf Spot", "Requires steady warmth. Avoid cold draughts on high balconies."),
            ("chilli", "Chilli / Hot Pepper", 20.0, 32.0, 15.0, 36.0, 3, "Full Sun (6-8 hrs)", "Leaf Curl, Mites", "Prefers well-draining potting mix. Allow top 2cm soil to dry between waterings."),
            ("basil", "Sweet Basil", 18.0, 30.0, 12.0, 35.0, 1, "Partial to Full Sun", "Fusarium Wilt, Downy Mildew", "Pinch top flower buds to promote bushy leaves. Bottom-water to keep foliage dry."),
            ("mint", "Spearmint / Peppermint", 15.0, 25.0, 8.0, 30.0, 1, "Partial Shade", "Rust, Powdery Mildew", "Vigorous runner. Keep in dedicated container with damp rich organic compost."),
            ("coriander", "Coriander / Cilantro", 15.0, 24.0, 8.0, 28.0, 2, "Partial Sun / Cool Light", "Damping Off, Bacterial Blight", "Bolts rapidly in high heat (>28°C). Provide afternoon shade on terraces."),
            ("spinach", "Spinach / Baby Greens", 12.0, 22.0, 5.0, 26.0, 2, "Partial Sun (4 hrs)", "Downy Mildew, Leaf Miner", "Thrives in cool balconies. Harvest outer leaves regularly."),
            ("lettuce", "Crisphead & Leaf Lettuce", 12.0, 22.0, 5.0, 26.0, 2, "Partial Shade", "Tip Burn, Sclerotinia", "Sensitive to extreme heat. Keep soil uniformly moist."),
            ("cucumber", "Container Cucumber", 20.0, 30.0, 15.0, 35.0, 2, "Full Sun", "Powdery Mildew, Downy Mildew", "Provide sturdy vertical trellis on balcony railings for fruit support."),
            ("strawberry", "Balcony Strawberry", 15.0, 25.0, 6.0, 30.0, 2, "Full Sun", "Botrytis Gray Mold, Leaf Spot", "Keep berries off wet potting soil using straw mulch or hanging planter."),
            ("succulent", "Succulents & Cacti", 18.0, 32.0, 10.0, 40.0, 7, "Bright Light", "Stem Rot, Mealybugs", "Drench thoroughly then allow soil to completely dry out before watering again.")
        ]
        cursor.executemany("""
            INSERT INTO plant_preferences (crop_key, crop_name, optimal_temp_min, optimal_temp_max, absolute_temp_min, absolute_temp_max, base_watering_days, sunlight_need, common_diseases, care_tips)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, pref_data)


def get_plant_preference(crop_type):
    """Retrieve plant preferences by crop type or fallback to defaults."""
    key = (crop_type or "").lower().strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM plant_preferences WHERE crop_key = ? OR crop_name LIKE ?", (key, f"%{key}%"))
        row = cursor.fetchone()
        if row:
            return dict(row)

    # Fallback to in-memory map
    fallback = DEFAULT_PLANT_PREFERENCES.get(key, DEFAULT_PLANT_PREFERENCES["other"])
    return {
        "crop_key": key,
        "crop_name": crop_type or "Urban Crop",
        "optimal_temp_min": fallback["opt_min"],
        "optimal_temp_max": fallback["opt_max"],
        "absolute_temp_min": fallback["min"],
        "absolute_temp_max": fallback["max"],
        "base_watering_days": fallback["water_days"],
        "sunlight_need": fallback["sunlight"],
        "common_diseases": "Foliar blight, leaf spots",
        "care_tips": "Ensure adequate container drainage and balanced soil feeding."
    }


# ==================== User Management ====================

def register_user(username, email, password, role='home_gardener', preferred_language='en'):
    """Registers a new user with secure scrypt hashing and preferred language."""
    username = (username or '').strip()
    email = (email or '').strip().lower()
    lang = (preferred_language or 'en').lower().strip()
    if lang not in ['en', 'gu', 'hi', 'te']:
        lang = 'en'
    
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
                "INSERT INTO users (username, email, password_hash, role, preferred_language) VALUES (?, ?, ?, ?, ?)",
                (username, email, pwd_hash, role, lang)
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
    """Authenticates by username or email."""
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
        cursor.execute("SELECT id, username, email, role, preferred_language, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None


def update_user_language(user_id, language):
    """Updates user's preferred language (en, gu, hi, te)."""
    lang = (language or 'en').lower().strip()
    if lang not in ['en', 'gu', 'hi', 'te']:
        lang = 'en'
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET preferred_language = ? WHERE id = ?", (lang, user_id))
        conn.commit()
        return cursor.rowcount > 0


def update_user_role(user_id, role):
    """Update role for user (e.g. home_gardener, nursery_owner)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
        return cursor.rowcount > 0


# ==================== Plant Management ====================

def add_plant(user_id, plant_name, plant_type, planting_date, location_type='Balcony', city='New Delhi',
              base_watering_days=2, growth_stage='Vegetative', soil_moisture='Moderate', notes='',
              pref_min=None, pref_max=None, opt_min=None, opt_max=None):
    """Adds a plant strictly scoped to user_id, initializing custom preferences."""
    pref = get_plant_preference(plant_type)
    p_min = pref_min if pref_min is not None else pref["absolute_temp_min"]
    p_max = pref_max if pref_max is not None else pref["absolute_temp_max"]
    o_min = opt_min if opt_min is not None else pref["optimal_temp_min"]
    o_max = opt_max if opt_max is not None else pref["optimal_temp_max"]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO plants (
                user_id, plant_name, plant_type, location_type, city, planting_date,
                base_watering_days, last_watered_date, growth_stage, soil_moisture,
                preferred_temp_min, preferred_temp_max, preferred_temp_optimal_min, preferred_temp_optimal_max,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, date('now'), ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, plant_name.strip(), plant_type.strip(), location_type, city.strip(), planting_date,
            int(base_watering_days), growth_stage, soil_moisture,
            float(p_min), float(p_max), float(o_min), float(o_max),
            notes.strip()
        ))
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
    """Fetch single plant with strict user ownership check."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM plants WHERE id = ? AND user_id = ?", (plant_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_plant_preferences(user_id, plant_id, opt_min, opt_max, abs_min, abs_max, growth_stage, base_watering_days):
    """Update editable temperature ranges and growth stage for a specific plant."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE plants
            SET preferred_temp_optimal_min = ?,
                preferred_temp_optimal_max = ?,
                preferred_temp_min = ?,
                preferred_temp_max = ?,
                growth_stage = ?,
                base_watering_days = ?
            WHERE id = ? AND user_id = ?
        """, (float(opt_min), float(opt_max), float(abs_min), float(abs_max), growth_stage, int(base_watering_days), plant_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def update_plant_soil_moisture(user_id, plant_id, moisture_level):
    """Update user-recorded soil moisture (Dry, Moderate, Moist, Wet)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE plants SET soil_moisture = ? WHERE id = ? AND user_id = ?
        """, (moisture_level, plant_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def record_watering_event(user_id, plant_id, watered_date=None, soil_moisture_before="Moderate", amount_ml=500, notes=""):
    """Records watering event in watering_logs and updates plants table."""
    with get_db() as conn:
        cursor = conn.cursor()
        date_val = watered_date or "date('now')"
        # Update plant
        cursor.execute("""
            UPDATE plants
            SET last_watered_date = date('now'), soil_moisture = 'Moist'
            WHERE id = ? AND user_id = ?
        """, (plant_id, user_id))
        
        # Insert log
        cursor.execute("""
            INSERT INTO watering_logs (plant_id, user_id, watered_date, soil_moisture_before, amount_ml, notes)
            VALUES (?, ?, date('now'), ?, ?, ?)
        """, (plant_id, user_id, soil_moisture_before, int(amount_ml), notes.strip()))
        conn.commit()
        return cursor.rowcount > 0


def update_plant_watering(user_id, plant_id, watered_date=None):
    """Legacy helper for compatibility."""
    return record_watering_event(user_id, plant_id, watered_date=watered_date)


def delete_user_plant(user_id, plant_id):
    """Delete plant and all cascaded data."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM plants WHERE id = ? AND user_id = ?", (plant_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


# ==================== Health Logs Management ====================

def add_health_log(user_id, plant_id, disease, confidence, image_path, symptoms, treatment, prevention, notes=''):
    """Adds a diagnosis log verifying plant ownership."""
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
    """Gets diagnosis history strictly for plants owned by user_id."""
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


# ==================== Weather Alerts Management ====================

def create_weather_alert(user_id, severity, alert_type, affected_name, explanation, recommended_action,
                         expected_time, weather_value=None, preferred_range=None, plant_id=None, business_id=None, dedup_hash=None):
    """
    Inserts a weather alert if a duplicate does not already exist within the last 12 hours.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        # Deduplication check
        if dedup_hash:
            cursor.execute("""
                SELECT id FROM weather_alerts
                WHERE user_id = ? AND dedup_hash = ? AND is_resolved = 0
                  AND created_at >= datetime('now', '-12 hours')
                LIMIT 1
            """, (user_id, dedup_hash))
            if cursor.fetchone():
                return None  # Duplicate detected, suppress duplicate alert

        cursor.execute("""
            INSERT INTO weather_alerts (
                user_id, plant_id, business_id, severity, alert_type, affected_name,
                weather_value, preferred_range, explanation, recommended_action,
                expected_time, dedup_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, plant_id, business_id, severity, alert_type, affected_name,
            weather_value, preferred_range, explanation, recommended_action,
            expected_time, dedup_hash
        ))
        conn.commit()
        return cursor.lastrowid


def get_user_weather_alerts(user_id, active_only=False, limit=20):
    """Fetches user alerts sorted by severity and timestamp."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM weather_alerts WHERE user_id = ?"
        params = [user_id]
        if active_only:
            query += " AND is_resolved = 0"
        query += " ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'Warning' THEN 2 ELSE 3 END, created_at DESC"
        if limit:
            query += f" LIMIT {int(limit)}"
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def get_unread_alert_count(user_id):
    """Returns count of active unresolved & unread alerts."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM weather_alerts WHERE user_id = ? AND is_resolved = 0 AND is_read = 0", (user_id,))
        return cursor.fetchone()[0]


def mark_alert_read(user_id, alert_id):
    """Marks an alert as read."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE weather_alerts SET is_read = 1 WHERE id = ? AND user_id = ?", (alert_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def mark_alert_resolved(user_id, alert_id):
    """Marks an alert as resolved."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE weather_alerts SET is_resolved = 1, is_read = 1 WHERE id = ? AND user_id = ?", (alert_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def mark_all_alerts_read(user_id):
    """Marks all user alerts as read."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE weather_alerts SET is_read = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


# ==================== Business Platform Management ====================

def get_or_create_user_business(user_id, default_name=None):
    """Retrieves or auto-initializes the business associated with user."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Check if user owns a business
        cursor.execute("SELECT * FROM businesses WHERE owner_id = ? LIMIT 1", (user_id,))
        biz = cursor.fetchone()
        if biz:
            return dict(biz)
        
        # Check if user is a member of any business
        cursor.execute("""
            SELECT b.* FROM businesses b
            JOIN business_members bm ON bm.business_id = b.id
            WHERE bm.user_id = ? LIMIT 1
        """, (user_id,))
        biz = cursor.fetchone()
        if biz:
            return dict(biz)

        # Create new business for nursery owner
        user = get_user_by_id(user_id)
        name = default_name or f"{user['username'].capitalize()}'s Nursery & Garden Centre"
        cursor.execute("""
            INSERT INTO businesses (owner_id, name, business_type, city)
            VALUES (?, ?, 'Plant Nursery & Garden Centre', 'New Delhi')
        """, (user_id, name))
        biz_id = cursor.lastrowid

        # Add user as owner member
        cursor.execute("""
            INSERT INTO business_members (business_id, user_id, role)
            VALUES (?, ?, 'owner')
        """, (biz_id, user_id))
        
        # Update user role to nursery_owner if was home_gardener
        cursor.execute("UPDATE users SET role = 'nursery_owner' WHERE id = ?", (user_id,))
        conn.commit()

        cursor.execute("SELECT * FROM businesses WHERE id = ?", (biz_id,))
        return dict(cursor.fetchone())


def get_business_by_id(biz_id):
    """Fetch business details."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM businesses WHERE id = ?", (biz_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def user_has_business_access(user_id, biz_id):
    """Verifies user has permission to access business."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM businesses WHERE id = ? AND owner_id = ?
            UNION
            SELECT 1 FROM business_members WHERE business_id = ? AND user_id = ?
        """, (biz_id, user_id, biz_id, user_id))
        return cursor.fetchone() is not None


# --- Nursery Inventory Operations ---

def add_inventory_item(biz_id, plant_name, species, category, quantity, low_stock_threshold,
                       purchase_cost, selling_price, supplier, location_zone='Greenhouse A', health_status='Healthy', notes=''):
    """Adds a new stock item to nursery inventory."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory_items (
                business_id, plant_name, species, category, quantity,
                low_stock_threshold, purchase_cost, selling_price, supplier,
                location_zone, health_status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            biz_id, plant_name.strip(), species.strip(), category.strip(), int(quantity),
            int(low_stock_threshold), float(purchase_cost), float(selling_price),
            supplier.strip(), location_zone.strip(), health_status.strip(), notes.strip()
        ))
        conn.commit()
        return cursor.lastrowid


def get_business_inventory(biz_id, category=None, search=None, low_stock_only=False):
    """Fetches inventory items with optional search and category filters."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM inventory_items WHERE business_id = ?"
        params = [biz_id]

        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (plant_name LIKE ? OR species LIKE ? OR supplier LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term, term])
        if low_stock_only:
            query += " AND quantity <= low_stock_threshold"

        query += " ORDER BY plant_name ASC"
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def adjust_inventory_stock(biz_id, user_id, item_id, movement_type, quantity_change, unit_price=None, notes=""):
    """
    Adjusts inventory stock (Sale, Restock, Wastage, Adjustment) and records movement.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory_items WHERE id = ? AND business_id = ?", (item_id, biz_id))
        item = cursor.fetchone()
        if not item:
            return False, "Inventory item not found."

        prev_qty = item["quantity"]
        qty_diff = int(quantity_change)

        if movement_type == "Sale":
            if prev_qty < qty_diff:
                return False, f"Insufficient stock. Available: {prev_qty}, requested sale: {qty_diff}"
            new_qty = prev_qty - qty_diff
            price = unit_price if unit_price is not None else item["selling_price"]
            # Record sale record
            cogs = qty_diff * item["purchase_cost"]
            cursor.execute("""
                INSERT INTO sales_records (business_id, user_id, item_id, quantity, unit_price, total_amount, estimated_cogs, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (biz_id, user_id, item_id, qty_diff, float(price), float(price * qty_diff), float(cogs), notes.strip()))
        elif movement_type == "Restock":
            new_qty = prev_qty + qty_diff
            price = unit_price if unit_price is not None else item["purchase_cost"]
        elif movement_type in ["Wastage", "Damage"]:
            new_qty = max(0, prev_qty - qty_diff)
            price = 0.0
        else: # Adjustment
            new_qty = max(0, qty_diff)
            qty_diff = new_qty - prev_qty
            price = item["selling_price"]

        # Update item quantity
        cursor.execute("UPDATE inventory_items SET quantity = ? WHERE id = ?", (new_qty, item_id))

        # Insert movement log
        cursor.execute("""
            INSERT INTO inventory_movements (
                item_id, business_id, user_id, movement_type, quantity_change,
                previous_qty, new_qty, unit_price, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, biz_id, user_id, movement_type, qty_diff, prev_qty, new_qty, float(price), notes.strip()))

        conn.commit()
        return True, None


def update_inventory_health_status(biz_id, item_id, health_status):
    """Update health status of inventory stock (e.g. Healthy, Needs Inspection, Quarantined)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE inventory_items SET health_status = ? WHERE id = ? AND business_id = ?
        """, (health_status, item_id, biz_id))
        conn.commit()
        return cursor.rowcount > 0


# --- Commercial Plant Batches ---

def add_plant_batch(biz_id, batch_name, plant_type, growing_area, quantity=20, health_status="Good"):
    """Adds a commercial growing batch."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO plant_batches (business_id, batch_name, plant_type, growing_area, quantity, health_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (biz_id, batch_name.strip(), plant_type.strip(), growing_area.strip(), int(quantity), health_status))
        conn.commit()
        return cursor.lastrowid


def get_business_batches(biz_id):
    """Fetches all plant batches for a nursery."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM plant_batches WHERE business_id = ? ORDER BY created_at DESC", (biz_id,))
        return [dict(r) for r in cursor.fetchall()]


def review_plant_batch(biz_id, batch_id, health_status, manager_notes=""):
    """Manager signs off / updates health on a commercial crop batch."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE plant_batches
            SET health_status = ?, manager_reviewed = 1, review_notes = ?
            WHERE id = ? AND business_id = ?
        """, (health_status, manager_notes.strip(), batch_id, biz_id))
        conn.commit()
        return cursor.rowcount > 0


# --- Sales & Financial Summaries ---

def get_business_sales_history(biz_id, limit=50):
    """Fetches sales transaction records for business."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, i.plant_name, i.species, u.username AS recorded_by
            FROM sales_records s
            LEFT JOIN inventory_items i ON s.item_id = i.id
            JOIN users u ON s.user_id = u.id
            WHERE s.business_id = ?
            ORDER BY s.sale_date DESC
            LIMIT ?
        """, (biz_id, int(limit)))
        return [dict(r) for r in cursor.fetchall()]


def calculate_business_kpis(biz_id):
    """
    Computes real financial and operational metrics from inventory and recorded sales:
    - Total inventory items count
    - Total plants in stock
    - Total inventory purchase valuation
    - Total estimated retail sales valuation
    - Recorded revenue from real recorded sales
    - Estimated COGS from recorded sales
    - Estimated gross margin percentage
    - Low-stock items count
    - Health issue items count
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Inventory metrics
        cursor.execute("""
            SELECT
                COUNT(*) AS total_items,
                SUM(quantity) AS total_plants,
                SUM(quantity * purchase_cost) AS total_purchase_val,
                SUM(quantity * selling_price) AS total_retail_val,
                SUM(CASE WHEN quantity <= low_stock_threshold THEN 1 ELSE 0 END) AS low_stock_count,
                SUM(CASE WHEN health_status != 'Healthy' THEN 1 ELSE 0 END) AS health_issue_count
            FROM inventory_items
            WHERE business_id = ?
        """, (biz_id,))
        inv_row = cursor.fetchone()
        
        # Real recorded sales metrics
        cursor.execute("""
            SELECT
                COUNT(*) AS total_sales_count,
                SUM(total_amount) AS total_revenue,
                SUM(estimated_cogs) AS total_cogs
            FROM sales_records
            WHERE business_id = ?
        """, (biz_id,))
        sales_row = cursor.fetchone()

        total_plants = inv_row["total_plants"] or 0
        total_purchase_val = round(inv_row["total_purchase_val"] or 0.0, 2)
        total_retail_val = round(inv_row["total_retail_val"] or 0.0, 2)
        low_stock_count = inv_row["low_stock_count"] or 0
        health_issue_count = inv_row["health_issue_count"] or 0

        recorded_revenue = round(sales_row["total_revenue"] or 0.0, 2)
        recorded_cogs = round(sales_row["total_cogs"] or 0.0, 2)
        recorded_profit = round(recorded_revenue - recorded_cogs, 2)
        
        # Estimated margin based on inventory or recorded sales
        if recorded_revenue > 0:
            margin_pct = round(((recorded_revenue - recorded_cogs) / recorded_revenue) * 100.0, 1)
        elif total_retail_val > 0:
            margin_pct = round(((total_retail_val - total_purchase_val) / total_retail_val) * 100.0, 1)
        else:
            margin_pct = 0.0

        return {
            "total_plants_in_stock": total_plants,
            "total_skus": inv_row["total_items"] or 0,
            "inventory_cost_value": total_purchase_val,
            "inventory_retail_value": total_retail_val,
            "potential_gross_profit": round(total_retail_val - total_purchase_val, 2),
            "recorded_revenue": recorded_revenue,
            "recorded_profit": recorded_profit,
            "estimated_margin_pct": margin_pct,
            "low_stock_alerts": low_stock_count,
            "health_issues_count": health_issue_count
        }
