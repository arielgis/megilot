import sqlite3
from datetime import datetime, timedelta
import os

DB_PATH = os.getenv("REGISTRATION_DB_PATH", "drone_registrations.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS registrations (
        sn TEXT NOT NULL,
        name TEXT NOT NULL,
        caltopo_token TEXT NOT NULL,
        email TEXT,
        registered_at TIMESTAMP NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        removal_code TEXT NOT NULL,
        permanent INTEGER DEFAULT 0,
        PRIMARY KEY (sn, caltopo_token),
        UNIQUE (caltopo_token, name)
    );
    """)
    
    conn.commit()
    conn.close()

def insert_registration(sn, name, token, email, removal_code, days_valid=7):
    now = datetime.utcnow()
    expires_at = now + timedelta(days=days_valid)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        c.execute("""
        INSERT INTO registrations (sn, name, caltopo_token, email, registered_at, expires_at, removal_code, permanent)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (sn, name, token, email, now.isoformat(), expires_at.isoformat(), removal_code))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError as e:
        return False, str(e)
    finally:
        conn.close()