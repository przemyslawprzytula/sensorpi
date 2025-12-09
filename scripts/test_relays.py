#!/usr/bin/env python3
"""Test script for 8-channel relay module.

Physical pin to BCM GPIO mapping:
  GND: Pin 9
  IN1: Pin 7  -> GPIO 4  -> water_valve (12V)
  IN2: Pin 11 -> GPIO 17 -> hot_air_exhaust
  IN3: Pin 13 -> GPIO 27 -> heater
  IN4: Pin 15 -> GPIO 22 -> ground_exchanger_low
  IN5: Pin 19 -> GPIO 10 -> ground_exchanger_high
  IN6: Pin 21 -> GPIO 9  -> pwr_12v (powers water_valve, grow_led_1, grow_led_2)
  IN7: Pin 23 -> GPIO 11 -> grow_led_1
  IN8: Pin 8  -> GPIO 14 -> grow_led_2
  VCC: Pin 4  (5V)

Note: Most relay modules are active-LOW (relay ON when GPIO is LOW).

Dependencies:
  - pwr_12v (relay6) must be ON when water_valve, grow_led_1 or grow_led_2 is ON
  - ground_exchanger_high requires ground_exchanger_low to be ON (for high speed)
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not available. Run on Raspberry Pi.")
    sys.exit(1)

# BCM GPIO pins with meaningful names
RELAY_PINS = {
    "water_valve": 4,            # IN1 - 12V water valve
    "hot_air_exhaust": 17,       # IN2 - Hot air vent exhaust
    "heater": 27,                # IN3 - Heater
    "ground_exchanger_low": 22,  # IN4 - Ground exchanger vent (low speed)
    "ground_exchanger_high": 10, # IN5 - Ground exchanger vent (high speed)
    "pwr_12v": 9,                # IN6 - 12V power supply
    "grow_led_1": 11,            # IN7 - Grow LED bed 1
    "grow_led_2": 14,            # IN8 - Grow LED bed 2
}

RELAY_NAMES = {
    "water_valve": "12V Water Valve",
    "hot_air_exhaust": "Hot Air Vent Exhaust",
    "heater": "Heater",
    "ground_exchanger_low": "Ground Exchanger (Low)",
    "ground_exchanger_high": "Ground Exchanger (High)",
    "pwr_12v": "12V Power Supply",
    "grow_led_1": "Grow LED Bed 1",
    "grow_led_2": "Grow LED Bed 2",
}

# Most relay modules are active-LOW
RELAY_ON = GPIO.LOW
RELAY_OFF = GPIO.HIGH


def setup():
    """Initialize GPIO pins."""
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    for relay_id, pin in RELAY_PINS.items():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, RELAY_OFF)
        name = RELAY_NAMES.get(relay_id, relay_id)
        print(f"  {relay_id}: GPIO {pin} - {name} (OFF)")


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
