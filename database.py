
import sqlite3
import os

DB_PATH = "data/brandguard.db"


def get_connection():
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

    # --------------------------------------
    # 1. BRANDS TABLE
    # --------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT NOT NULL,
            description TEXT
        )
    """)

    # --------------------------------------
    # 2. BRAND GUIDELINES TABLE
    # --------------------------------------

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

    # --------------------------------------
    # 3. CONTENT HISTORY TABLE
    # --------------------------------------

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

    # --------------------------------------
    # 4. CONTENT REVIEWS TABLE
    # --------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER,
            review_status TEXT DEFAULT 'Pending',
            reviewer_notes TEXT,
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------
    # 5. APPROVED BRAND FACTS TABLE
    # --------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brand_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL,
            fact TEXT NOT NULL,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brands(id)
        )
    """)

    # ======================================
    # ROUND 3: CAMPAIGN MANAGEMENT
    # ======================================

    # --------------------------------------
    # 6. CAMPAIGNS TABLE
    # --------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL,
            campaign_name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (brand_id)
            REFERENCES brands(id)
        )
    """)

    # --------------------------------------
    # 7. CAMPAIGN ASSETS TABLE
    # --------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaign_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            asset_name TEXT NOT NULL,
            channel TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (campaign_id)
            REFERENCES campaigns(id)
            ON DELETE CASCADE
        )
    """)

    # --------------------------------------
    # 8. ASSET VERSIONS TABLE
    # --------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asset_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            score INTEGER,
            compliance_status TEXT,
            violations TEXT,
            version_note TEXT,

            review_status TEXT DEFAULT 'Pending',
            reviewer_notes TEXT,
            reviewed_at TIMESTAMP,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (asset_id)
            REFERENCES campaign_assets(id)
            ON DELETE CASCADE,

            UNIQUE (asset_id, version_number)
        )
    """)

    # --------------------------------------
    # INDEXES FOR FASTER CAMPAIGN SEARCH
    # --------------------------------------

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_campaigns_brand
        ON campaigns(brand_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_assets_campaign
        ON campaign_assets(campaign_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_versions_asset
        ON asset_versions(asset_id)
    """)

    conn.commit()
    conn.close()

# ======================================
# ROUND 3: ASSET MANAGEMENT FUNCTIONS
# ======================================

import json


def create_campaign(brand_id, campaign_name, description=""):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO campaigns (brand_id, campaign_name, description)
        VALUES (?, ?, ?)
    """, (brand_id, campaign_name, description))

    campaign_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return campaign_id


def create_asset(campaign_id, asset_name, channel):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO campaign_assets
        (campaign_id, asset_name, channel)
        VALUES (?, ?, ?)
    """, (campaign_id, asset_name, channel))

    asset_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return asset_id


def save_asset_version(
    asset_id,
    content,
    score=None,
    compliance_status="Not Analysed",
    violations=None,
    version_note="",
    review_status="Pending"
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(MAX(version_number), 0) + 1
        FROM asset_versions
        WHERE asset_id = ?
    """, (asset_id,))

    version_number = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO asset_versions (
            asset_id,
            version_number,
            content,
            score,
            compliance_status,
            violations,
            version_note,
            review_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        asset_id,
        version_number,
        content,
        score,
        compliance_status,
        json.dumps(violations or []),
        version_note,
        review_status
    ))

    version_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return version_id, version_number


def get_campaigns(brand_id=None):
    conn = get_connection()

    if brand_id is not None:
        rows = conn.execute("""
            SELECT id, campaign_name, description, status
            FROM campaigns
            WHERE brand_id = ?
            ORDER BY id DESC
        """, (brand_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, campaign_name, description, status
            FROM campaigns
            ORDER BY id DESC
        """).fetchall()

    conn.close()
    return rows


def get_campaign_assets(campaign_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT id, asset_name, channel, created_at
        FROM campaign_assets
        WHERE campaign_id = ?
        ORDER BY id DESC
    """, (campaign_id,)).fetchall()

    conn.close()
    return rows


def get_asset_versions(asset_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            id,
            version_number,
            content,
            score,
            compliance_status,
            violations,
            version_note,
            review_status,
            reviewer_notes,
            created_at
        FROM asset_versions
        WHERE asset_id = ?
        ORDER BY version_number DESC
    """, (asset_id,)).fetchall()

    conn.close()
    return rows
