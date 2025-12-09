# Raspberry Pi 3 Setup Guide

Follow these steps to prepare the Raspberry Pi environment for the SensorPi project.

## 1. Base Operating System
1. Download the latest Raspberry Pi OS Lite (64-bit) image.
2. Flash the image to a microSD card using Raspberry Pi Imager or balenaEtcher.
3. (Optional) Enable SSH by creating an empty file named `ssh` in the boot partition.
4. Configure Wi-Fi by creating `wpa_supplicant.conf` in the boot partition when required.
5. Insert the microSD card into the Raspberry Pi, connect sensors/relays, and power on.

## 2. First Boot Configuration
```bash
# Update base system
sudo apt update && sudo apt full-upgrade -y

# Set timezone and locale
sudo raspi-config nonint do_change_locale en_US.UTF-8
sudo raspi-config nonint do_change_timezone Europe/Warsaw

# Enable I2C interface
sudo raspi-config nonint do_i2c 0

# Enable SSH for remote access
sudo raspi-config nonint do_ssh 0

# Reboot to apply changes
sudo reboot
```

## 3. Install System Dependencies
```bash
sudo apt install -y python3-pip python3-venv python3-dev git \
    libffi-dev libssl-dev build-essential pkg-config \
    i2c-tools screen
```

Verify that all I2C devices are visible:
```bash
sudo i2cdetect -y 1
```

## 4. Clone the Repository
```bash
cd /opt
sudo git clone https://github.com/your-org/sensorpi.git
sudo chown -R $USER:$USER sensorpi
cd sensorpi
```

## 5. Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Environment Configuration
1. Copy the example configuration:
   ```bash
   cp config/settings.example.json config/settings.json
   ```
2. Edit `config/settings.json` to match your database credentials, sensor addresses, and relay pins.
3. Export database credentials securely if preferred:
   ```bash
   export SENSORPI_CONFIG=/opt/sensorpi/config/settings.json
   ```

## 7. Database Preparation
1. Ensure the remote MySQL server is reachable from the Raspberry Pi.
2. Create the database and user:
   ```sql
   CREATE DATABASE greenhouse CHARACTER SET utf8mb4;
   CREATE USER 'greenhouse_user'@'%' IDENTIFIED BY 'StrongPassword';
   GRANT ALL PRIVILEGES ON greenhouse.* TO 'greenhouse_user'@'%';
   FLUSH PRIVILEGES;
   ```
3. Run migrations (initial schema):
   ```bash
   source .venv/bin/activate
   python -m sensorpi.database.migrate
   ```
   *(Migration script to be added in a later phase.)*

## 8. Service Installation
1. Install the systemd unit files (see `systemd/` directory for templates).
2. Reload systemd and enable services:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable sensorpi-collector.service
   sudo systemctl start sensorpi-collector.service
   ```
3. Check service status:
   ```bash
   sudo systemctl status sensorpi-collector.service
   ```

## 9. Verification
- Confirm logs with `journalctl -u sensorpi-collector.service -f`.
- Check that new rows appear in the `sensor_readings` table.
- Validate that relay channels can switch loads safely using manual tests.

## 10. Maintenance Tips
- Keep the system updated (`sudo apt update && sudo apt upgrade`).
- Schedule automatic reboots if stability issues arise (`sudo systemctl enable --now systemd-timesyncd`).
- Use `tmux` or `screen` for manual debugging sessions.
- Regularly back up `/opt/sensorpi/config/settings.json` and `.env` files.
