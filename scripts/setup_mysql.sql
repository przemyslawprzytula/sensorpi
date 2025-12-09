-- MySQL Database Setup Script for SensorPi Greenhouse System
-- Run this script as root on the MySQL server (192.168.1.20)
-- Usage: mysql -u root -p < setup_mysql.sql

-- Create the database
CREATE DATABASE IF NOT EXISTS greenhouse
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Create dedicated user for the greenhouse application
CREATE USER IF NOT EXISTS 'greenhouse_user'@'192.168.1.200'
  IDENTIFIED BY 'tmpM9yJQq0iSbz5QECRD9bOG';

-- Also allow connections from localhost (for local testing)
CREATE USER IF NOT EXISTS 'greenhouse_user'@'localhost'
  IDENTIFIED BY 'tmpM9yJQq0iSbz5QECRD9bOG';

-- Grant privileges
GRANT ALL PRIVILEGES ON greenhouse.* TO 'greenhouse_user'@'192.168.1.200';
GRANT ALL PRIVILEGES ON greenhouse.* TO 'greenhouse_user'@'localhost';

-- Apply privilege changes
FLUSH PRIVILEGES;

-- Switch to the greenhouse database
USE greenhouse;

-- Sensor readings table
CREATE TABLE IF NOT EXISTS sensor_readings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sensor_id VARCHAR(64) NOT NULL,
    sensor_type VARCHAR(32) NOT NULL,
    measurement VARCHAR(32) NOT NULL,
    value DECIMAL(10, 4) NOT NULL,
    unit VARCHAR(16) NOT NULL,
    location VARCHAR(64),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sensor_id (sensor_id),
    INDEX idx_sensor_type (sensor_type),
    INDEX idx_measurement (measurement),
    INDEX idx_recorded_at (recorded_at),
    INDEX idx_location_time (location, recorded_at)
) ENGINE=InnoDB;

-- Relay state history table
CREATE TABLE IF NOT EXISTS relay_states (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    state ENUM('on', 'off') NOT NULL,
    triggered_by ENUM('automation', 'manual', 'failsafe', 'startup') NOT NULL,
    rule_name VARCHAR(128),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_id (device_id),
    INDEX idx_changed_at (changed_at)
) ENGINE=InnoDB;

-- Automation rules configuration table (optional - for web UI management)
CREATE TABLE IF NOT EXISTS automation_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    condition_type ENUM('threshold', 'schedule', 'combined') NOT NULL,
    config JSON NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    priority INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_device_id (device_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB;

-- System events log table
CREATE TABLE IF NOT EXISTS system_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(32) NOT NULL,
    severity ENUM('debug', 'info', 'warning', 'error', 'critical') NOT NULL,
    message TEXT NOT NULL,
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_type (event_type),
    INDEX idx_severity (severity),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- Insert initial system event
INSERT INTO system_events (event_type, severity, message)
VALUES ('system_init', 'info', 'Database initialized successfully');

SELECT 'Database setup completed successfully!' AS status;
