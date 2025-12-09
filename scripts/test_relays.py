#!/usr/bin/env python3
"""Test script for 8-channel relay module.

Physical pin to BCM GPIO mapping:
  GND: Pin 9
  IN1: Pin 7  -> GPIO 4
  IN2: Pin 11 -> GPIO 17
  IN3: Pin 13 -> GPIO 27
  IN4: Pin 15 -> GPIO 22
  IN5: Pin 19 -> GPIO 10
  IN6: Pin 21 -> GPIO 9
  IN7: Pin 23 -> GPIO 11
  IN8: Pin 8  -> GPIO 14
  VCC: Pin 4  (5V)

Note: Most relay modules are active-LOW (relay ON when GPIO is LOW).
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not available. Run on Raspberry Pi.")
    sys.exit(1)

# BCM GPIO pins for relays 1-8
RELAY_PINS = {
    "relay1": 4,   # IN1
    "relay2": 17,  # IN2
    "relay3": 27,  # IN3
    "relay4": 22,  # IN4
    "relay5": 10,  # IN5
    "relay6": 9,   # IN6
    "relay7": 11,  # IN7
    "relay8": 14,  # IN8
}

# Most relay modules are active-LOW
RELAY_ON = GPIO.LOW
RELAY_OFF = GPIO.HIGH


def setup():
    """Initialize GPIO pins."""
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    for name, pin in RELAY_PINS.items():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, RELAY_OFF)
        print(f"  {name}: GPIO {pin} initialized (OFF)")


def relay_on(name: str):
    """Turn relay ON."""
    pin = RELAY_PINS[name]
    GPIO.output(pin, RELAY_ON)
    print(f"  {name} (GPIO {pin}): ON")


def relay_off(name: str):
    """Turn relay OFF."""
    pin = RELAY_PINS[name]
    GPIO.output(pin, RELAY_OFF)
    print(f"  {name} (GPIO {pin}): OFF")


def test_sequential(delay: float = 0.5):
    """Test each relay sequentially."""
    print("\n=== Sequential Test ===")
    print("Testing each relay one by one...")

    for name in RELAY_PINS:
        relay_on(name)
        time.sleep(delay)
        relay_off(name)
        time.sleep(0.1)

    print("Sequential test complete!")


def test_all_on_off(delay: float = 2.0):
    """Turn all relays ON, then OFF."""
    print("\n=== All On/Off Test ===")

    print("Turning ALL relays ON...")
    for name in RELAY_PINS:
        relay_on(name)

    time.sleep(delay)

    print("Turning ALL relays OFF...")
    for name in RELAY_PINS:
        relay_off(name)

    print("All on/off test complete!")


def test_single(relay_name: str, duration: float = 2.0):
    """Test a single relay."""
    if relay_name not in RELAY_PINS:
        print(f"ERROR: Unknown relay '{relay_name}'")
        print(f"Available: {list(RELAY_PINS.keys())}")
        return

    print(f"\n=== Single Relay Test: {relay_name} ===")
    relay_on(relay_name)
    time.sleep(duration)
    relay_off(relay_name)
    print(f"Single relay test complete!")


def cleanup():
    """Cleanup GPIO."""
    print("\nCleaning up GPIO...")
    for name in RELAY_PINS:
        relay_off(name)
    GPIO.cleanup()


def main():
    print("=" * 50)
    print("SensorPi - 8-Channel Relay Test")
    print("=" * 50)
    print("\nRelay Pin Mapping:")
    for name, pin in RELAY_PINS.items():
        print(f"  {name}: GPIO {pin}")

    print("\nInitializing GPIO...")
    setup()

    try:
        if len(sys.argv) > 1:
            # Test specific relay
            relay_name = sys.argv[1]
            duration = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
            test_single(relay_name, duration)
        else:
            # Run full test suite
            test_sequential(0.5)
            time.sleep(1)
            test_all_on_off(2.0)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        cleanup()

    print("\n" + "=" * 50)
    print("Test complete!")


if __name__ == "__main__":
    main()
