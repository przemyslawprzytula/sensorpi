#!/usr/bin/env python3
"""Migration script: Convert from single-table to 2-table schema.

This script:
1. Creates the new 'sensors' table
2. Migrates sensor metadata from sensor_readings to sensors
3. Recreates sensor_readings with the lean schema
4. Migrates reading data with FK references
"""
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text


def get_db_url():
    config_path = Path(__file__).parent.parent / "config" / "settings.json"
    with open(config_path) as f:
        config = json.load(f)
    db = config["database"]
    return f"mysql+pymysql://{db['username']}:{db['password']}@{db['host']}:{db['port']}/{db['database']}"


def migrate():
    engine = create_engine(get_db_url())

    with engine.connect() as conn:
        # Check if migration is needed
        result = conn.execute(text("SHOW TABLES LIKE 'sensors'"))
        if result.fetchone():
            print("Migration already applied (sensors table exists)")
            return

        print("Starting migration to 2-table schema...")

        # 1. Create new sensors table
        print("Creating sensors table...")
        conn.execute(text("""
            CREATE TABLE sensors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sensor_id VARCHAR(64) NOT NULL UNIQUE,
                sensor_type ENUM('temperature', 'humidity', 'light') NOT NULL,
                measurement VARCHAR(32) NOT NULL,
                unit VARCHAR(16) NOT NULL,
                location VARCHAR(64),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 2. Migrate distinct sensors from old sensor_readings
        print("Extracting sensor metadata...")
        conn.execute(text("""
            INSERT INTO sensors (sensor_id, sensor_type, measurement, unit, location)
            SELECT DISTINCT
                sensor_id,
                sensor_type,
                measurement,
                unit,
                location
            FROM sensor_readings
        """))

        # 3. Rename old table
        print("Backing up old sensor_readings table...")
        conn.execute(text("RENAME TABLE sensor_readings TO sensor_readings_old"))

        # 4. Create new lean sensor_readings table
        print("Creating new sensor_readings table...")
        conn.execute(text("""
            CREATE TABLE sensor_readings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sensor_fk INT NOT NULL,
                value DOUBLE NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sensor_fk) REFERENCES sensors(id),
                INDEX ix_sensor_readings_sensor_recorded (sensor_fk, recorded_at)
            )
        """))

        # 5. Migrate readings with FK lookup
        print("Migrating reading data...")
        conn.execute(text("""
            INSERT INTO sensor_readings (sensor_fk, value, recorded_at)
            SELECT
                s.id,
                sro.value,
                sro.recorded_at
            FROM sensor_readings_old sro
            JOIN sensors s ON s.sensor_id = sro.sensor_id
        """))

        # 6. Verify migration
        old_count = conn.execute(text("SELECT COUNT(*) FROM sensor_readings_old")).fetchone()[0]
        new_count = conn.execute(text("SELECT COUNT(*) FROM sensor_readings")).fetchone()[0]
        sensor_count = conn.execute(text("SELECT COUNT(*) FROM sensors")).fetchone()[0]

        print(f"\nMigration summary:")
        print(f"  Sensors created: {sensor_count}")
        print(f"  Old readings: {old_count}")
        print(f"  New readings: {new_count}")

        if old_count == new_count:
            print("\nMigration successful! You can drop the old table with:")
            print("  DROP TABLE sensor_readings_old;")
        else:
            print("\nWARNING: Row count mismatch! Please verify before dropping old table.")

        conn.commit()
        print("\nDone!")


if __name__ == "__main__":
    migrate()
