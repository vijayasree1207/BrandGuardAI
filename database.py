import sqlite3
import os

DB_PATH = "data/brandguard.db"

def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT NOT NULL,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guidelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER,
            category TEXT NOT NULL,
            rule TEXT NOT NULL,
            severity TEXT NOT NULL,
            FOREIGN KEY (brand_id) REFERENCES brands(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER,
            content TEXT NOT NULL,
            score INTEGER,
            status TEXT,
            violations TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brands(id)
        )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS content_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_id INTEGER,
        review_status TEXT DEFAULT 'Pending',
        reviewer_notes TEXT,
        reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

    conn.commit()
    conn.close()