import sqlite3
from datetime import datetime

DB_PATH = "database/filaments.db"

def create_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS filaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT UNIQUE NOT NULL,
        tray_uid TEXT,
        tag_manufacturer TEXT,
        filament_type TEXT,
        filament_detailed_type TEXT,
        color_code TEXT,
        extra_color_info TEXT,
        filament_diameter REAL,
        spool_width REAL,
        spool_weight INTEGER,
        filament_length INTEGER,
        print_temp_min INTEGER,
        print_temp_max INTEGER,
        dry_temp INTEGER,
        dry_time_minutes INTEGER,
        dry_bed_temp INTEGER,
        nozzle_diameter INTEGER,
        xcam_info TEXT,
        manufacture_datetime_utc DATETIME,
        short_date TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

def insert_dummy_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    data = [
        (
            "04A7B3F2C8", "09F1A3BC67", "STMicroelectronics",
            "PLA", "PLA Basic", "#FFAA33", "Orange vif", 1.75,
            65.0, 1000, 330, 190, 220, 50, 240, 60, 0.4, "XCamV2",
            datetime(2025, 6, 15, 10, 30), "20250615"
        ),
        (
            "04B9D6E4F1", "09C2D7AB99", "NXP",
            "PETG", "PETG CF", "#222222", "Noir carbone", 1.75,
            70.0, 800, 260, 230, 250, 65, 180, 70, 0.6, "XCamV1",
            datetime(2025, 5, 20, 14, 10), "20250520"
        )
    ]

    c.executemany("""
    INSERT INTO filaments (
        uid, tray_uid, tag_manufacturer, filament_type, filament_detailed_type,
        color_code, extra_color_info, filament_diameter, spool_width, spool_weight,
        filament_length, print_temp_min, print_temp_max, dry_temp, dry_time_minutes,
        dry_bed_temp, nozzle_diameter, xcam_info, manufacture_datetime_utc, short_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
    insert_dummy_data()
