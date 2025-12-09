#!/usr/bin/env python3
"""Quick test script to verify I2C sensor connectivity."""

import board
import busio

def test_i2c():
    """Test I2C bus and list detected devices."""
    print("Testing I2C bus...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        while not i2c.try_lock():
            pass

        devices = i2c.scan()
        i2c.unlock()

        print(f"Found {len(devices)} I2C devices:")
        for addr in devices:
            print(f"  - 0x{addr:02x} ({addr})")
        return devices
    except Exception as e:
        print(f"I2C Error: {e}")
        return []

def test_mcp9808(address=0x19):
    """Test MCP9808 temperature sensor."""
    print(f"\nTesting MCP9808 at address 0x{address:02x}...")
    try:
        import adafruit_mcp9808
        i2c = busio.I2C(board.SCL, board.SDA)
        sensor = adafruit_mcp9808.MCP9808(i2c, address=address)
        temp = sensor.temperature
        print(f"  Temperature: {temp:.2f} °C")
        return temp
    except Exception as e:
        print(f"  Error: {e}")
        return None

def test_tsl2591(address=0x29):
    """Test TSL2591 light sensor."""
    print(f"\nTesting TSL2591 at address 0x{address:02x}...")
    try:
        import adafruit_tsl2591
        i2c = busio.I2C(board.SCL, board.SDA)
        sensor = adafruit_tsl2591.TSL2591(i2c)
        lux = sensor.lux
        visible = sensor.visible
        infrared = sensor.infrared
        print(f"  Lux: {lux:.2f}")
        print(f"  Visible: {visible}")
        print(f"  Infrared: {infrared}")
        return lux
    except Exception as e:
        print(f"  Error: {e}")
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("SensorPi - Sensor Test Script")
    print("=" * 50)

    devices = test_i2c()

    # Test MCP9808 sensors at detected addresses
    if 0x19 in devices:
        test_mcp9808(0x19)
    if 0x1c in devices:
        test_mcp9808(0x1c)

    # Test TSL2591 light sensor
    if 0x29 in devices:
        test_tsl2591()

    print("\n" + "=" * 50)
    print("Test complete!")
