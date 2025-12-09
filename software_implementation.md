# Software Implementation Plan

## Project Structure

```
sensorpi/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Configuration management
│   └── database.py          # Database connection settings
├── sensors/
│   ├── __init__.py
│   ├── base_sensor.py       # Abstract sensor base class
│   ├── mcp9808_sensor.py    # Temperature sensor implementation
│   ├── tsl2591x_sensor.py   # Light sensor implementation
│   ├── si7021_sensor.py     # Temp/Humidity sensor implementation
│   └── aht20_sensor.py      # Temp/Humidity sensor implementation
├── controllers/
│   ├── __init__.py
│   ├── relay_controller.py  # Relay control logic
│   └── device_manager.py    # Device state management
├── automation/
│   ├── __init__.py
│   ├── rule_engine.py       # Automation rule processing
│   ├── scheduler.py         # Task scheduling
│   └── manual_override.py   # Manual control handling
├── database/
│   ├── __init__.py
│   ├── models.py            # SQLAlchemy ORM models
│   ├── repository.py        # Data access layer
│   └── migrations/          # Database migration scripts
├── api/
│   ├── __init__.py
│   ├── app.py               # Flask/FastAPI application
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── sensors.py       # Sensor data endpoints
│   │   ├── controls.py      # Device control endpoints
│   │   └── analytics.py      # Historical data endpoints
│   └── websocket.py         # Real-time updates
├── web/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/
│       ├── index.html       # Main dashboard
│       ├── controls.html    # Manual control interface
│       └── analytics.html   # Historical data view
├── services/
│   ├── __init__.py
│   ├── data_collector.py    # Main data collection service
│   ├── system_monitor.py    # Health monitoring
│   └── logger.py            # Centralized logging
├── tests/
│   ├── __init__.py
│   ├── test_sensors.py
│   ├── test_controllers.py
│   └── test_automation.py
├── scripts/
│   ├── setup.sh             # System setup script
│   ├── install_services.sh  # Service installation
│   └── backup_database.sh   # Database backup
├── requirements.txt         # Python dependencies
├── systemd/
│   ├── sensor-collector.service
│   └── web-api.service
├── README.md
└── main.py                  # Application entry point
```

## Core Components Implementation

### 1. Sensor Base Class

```python
# sensors/base_sensor.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class BaseSensor(ABC):
    def __init__(self, sensor_id: str, i2c_address: int, location: str = ""):
        self.sensor_id = sensor_id
        self.i2c_address = i2c_address
        self.location = location
        self.last_reading = None
        self.last_error = None
        
    @abstractmethod
    def read_data(self) -> Dict[str, Any]:
        """Read sensor data and return formatted dictionary"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize sensor connection"""
        pass
    
    def is_healthy(self) -> bool:
        """Check if sensor is responding correctly"""
        return self.last_error is None
    
    def get_reading_with_metadata(self) -> Dict[str, Any]:
        """Get reading with timestamp and metadata"""
        data = self.read_data()
        return {
            'sensor_id': self.sensor_id,
            'timestamp': datetime.utcnow().isoformat(),
            'location': self.location,
            'data': data,
            'healthy': self.is_healthy()
        }
```

### 2. Sensor Manager

```python
# sensors/sensor_manager.py
from typing import List, Dict
import logging
from .mcp9808_sensor import MCP9808Sensor
from .tsl2591x_sensor import TSL2591XSensor
from .si7021_sensor import Si7021Sensor
from .aht20_sensor import AHT20Sensor

class SensorManager:
    def __init__(self):
        self.sensors: List[BaseSensor] = []
        self.logger = logging.getLogger(__name__)
        
    def initialize_sensors(self, sensor_config: Dict) -> bool:
        """Initialize all configured sensors"""
        try:
            # Initialize MCP9808 sensors
            for i, config in enumerate(sensor_config.get('mcp9808', [])):
                sensor = MCP9808Sensor(
                    sensor_id=f"mcp9808_{i+1}",
                    i2c_address=config['address'],
                    location=config.get('location', f"location_{i+1}")
                )
                if sensor.initialize():
                    self.sensors.append(sensor)
                else:
                    self.logger.error(f"Failed to initialize MCP9808 sensor at {config['address']}")
            
            # Initialize other sensors...
            # Similar pattern for TSL2591X, Si7021, AHT20
            
            return len(self.sensors) > 0
            
        except Exception as e:
            self.logger.error(f"Sensor initialization failed: {e}")
            return False
    
    def read_all_sensors(self) -> List[Dict]:
        """Read data from all sensors"""
        readings = []
        for sensor in self.sensors:
            try:
                reading = sensor.get_reading_with_metadata()
                readings.append(reading)
            except Exception as e:
                self.logger.error(f"Failed to read from {sensor.sensor_id}: {e}")
                
        return readings
```

### 3. Relay Controller

```python
# controllers/relay_controller.py
import RPi.GPIO as GPIO
from typing import Dict, List
from enum import Enum
import logging

class RelayState(Enum):
    ON = 1
    OFF = 0

class RelayController:
    def __init__(self, relay_config: Dict):
        self.relay_pins = relay_config['pins']
        self.relay_names = relay_config.get('names', {})
        self.logger = logging.getLogger(__name__)
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Initialize all relay pins as OUTPUT
        for pin in self.relay_pins.values():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)  # Start with all relays OFF
    
    def set_relay(self, relay_id: str, state: RelayState) -> bool:
        """Control individual relay"""
        try:
            pin = self.relay_pins.get(relay_id)
            if pin is None:
                self.logger.error(f"Unknown relay ID: {relay_id}")
                return False
            
            GPIO.output(pin, state.value)
            self.logger.info(f"Relay {relay_id} set to {state.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to control relay {relay_id}: {e}")
            return False
    
    def get_relay_state(self, relay_id: str) -> RelayState:
        """Get current state of relay"""
        try:
            pin = self.relay_pins.get(relay_id)
            if pin is None:
                return RelayState.OFF
            
            state = GPIO.input(pin)
            return RelayState(state)
            
        except Exception as e:
            self.logger.error(f"Failed to read relay {relay_id} state: {e}")
            return RelayState.OFF
    
    def emergency_shutdown(self):
        """Turn off all relays immediately"""
        for relay_id in self.relay_pins.keys():
            self.set_relay(relay_id, RelayState.OFF)
    
    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup()
```

### 4. Automation Rule Engine

```python
# automation/rule_engine.py
from typing import Dict, List, Any
from datetime import datetime, time
import logging
from ..controllers.relay_controller import RelayController, RelayState

class AutomationRule:
    def __init__(self, rule_config: Dict):
        self.name = rule_config['name']
        self.device_type = rule_config['device_type']
        self.device_id = rule_config['device_id']
        self.condition_type = rule_config['condition_type']
        self.conditions = rule_config['conditions']
        self.is_active = rule_config.get('is_active', True)
        
    def evaluate(self, sensor_data: List[Dict]) -> bool:
        """Evaluate if rule conditions are met"""
        if not self.is_active:
            return False
            
        if self.condition_type == 'threshold':
            return self._evaluate_threshold(sensor_data)
        elif self.condition_type == 'schedule':
            return self._evaluate_schedule()
        elif self.condition_type == 'complex':
            return self._evaluate_complex(sensor_data)
        
        return False
    
    def _evaluate_threshold(self, sensor_data: List[Dict]) -> bool:
        """Evaluate threshold-based conditions"""
        for condition in self.conditions:
            sensor_type = condition['sensor_type']
            operator = condition['operator']  # '>', '<', '>=', '<='
            threshold = condition['threshold']
            
            # Find matching sensor data
            for reading in sensor_data:
                if reading['data'].get('type') == sensor_type:
                    value = reading['data'].get('value')
                    if value is not None:
                        if self._compare_values(value, operator, threshold):
                            return True
        
        return False
    
    def _evaluate_schedule(self) -> bool:
        """Evaluate time-based conditions"""
        current_time = datetime.now().time()
        
        for condition in self.conditions:
            start_time = time.fromisoformat(condition['start_time'])
            end_time = time.fromisoformat(condition['end_time'])
            
            if start_time <= current_time <= end_time:
                return True
        
        return False
    
    def _evaluate_complex(self, sensor_data: List[Dict]) -> bool:
        """Evaluate complex multi-condition rules"""
        # Implementation for complex logic combining multiple conditions
        pass
    
    def _compare_values(self, value: float, operator: str, threshold: float) -> bool:
        """Compare values based on operator"""
        if operator == '>':
            return value > threshold
        elif operator == '<':
            return value < threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        
        return False

class RuleEngine:
    def __init__(self, relay_controller: RelayController):
        self.relay_controller = relay_controller
        self.rules: List[AutomationRule] = []
        self.logger = logging.getLogger(__name__)
        self.manual_override = {}
        
    def load_rules(self, rules_config: List[Dict]):
        """Load automation rules from configuration"""
        self.rules = [AutomationRule(rule_config) for rule_config in rules_config]
    
    def process_rules(self, sensor_data: List[Dict]):
        """Process all automation rules"""
        for rule in self.rules:
            # Skip if manual override is active
            if rule.device_id in self.manual_override:
                continue
                
            should_activate = rule.evaluate(sensor_data)
            current_state = self.relay_controller.get_relay_state(rule.device_id)
            
            if should_activate and current_state == RelayState.OFF:
                self.relay_controller.set_relay(rule.device_id, RelayState.ON)
                self._log_control_event(rule, True)
            elif not should_activate and current_state == RelayState.ON:
                self.relay_controller.set_relay(rule.device_id, RelayState.OFF)
                self._log_control_event(rule, False)
    
    def set_manual_override(self, device_id: str, state: RelayState, duration_minutes: int = 60):
        """Set manual override for device control"""
        self.manual_override[device_id] = {
            'state': state,
            'expires_at': datetime.now().timestamp() + (duration_minutes * 60)
        }
        self.relay_controller.set_relay(device_id, state)
    
    def clear_expired_overrides(self):
        """Clear expired manual overrides"""
        current_time = datetime.now().timestamp()
        expired_devices = [
            device_id for device_id, override in self.manual_override.items()
            if override['expires_at'] <= current_time
        ]
        
        for device_id in expired_devices:
            del self.manual_override[device_id]
            self.logger.info(f"Manual override expired for {device_id}")
    
    def _log_control_event(self, rule: AutomationRule, activated: bool):
        """Log automation control events"""
        self.logger.info(
            f"Automation rule '{rule.name}' "
            f"{'activated' if activated else 'deactivated'} "
            f"device {rule.device_id}"
        )
```

## Database Models

```python
# database/models.py
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class SensorType(enum.Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    LIGHT = "light"

class DeviceType(enum.Enum):
    VENTILATION = "ventilation"
    LED = "led"

class TriggerSource(enum.Enum):
    AUTOMATION = "automation"
    MANUAL = "manual"
    SCHEDULE = "schedule"

class SensorReading(Base):
    __tablename__ = 'sensor_readings'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    sensor_id = Column(String(50), nullable=False)
    sensor_type = Column(Enum(SensorType), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(10), nullable=False)
    location = Column(String(50))

class ControlEvent(Base):
    __tablename__ = 'control_events'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    device_type = Column(Enum(DeviceType), nullable=False)
    device_id = Column(Integer, nullable=False)
    action = Column(String(10), nullable=False)  # 'on' or 'off'
    trigger_source = Column(Enum(TriggerSource), nullable=False)
    trigger_value = Column(String(100))

class SystemConfig(Base):
    __tablename__ = 'system_config'
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

## Configuration Management

```python
# config/settings.py
import os
import json
from typing import Dict, Any

class Settings:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "database": {
                "host": "localhost",
                "port": 3306,
                "database": "greenhouse",
                "username": "greenhouse_user",
                "password": "secure_password"
            },
            "sensors": {
                "mcp9808": [
                    {"address": 0x18, "location": "air_high"},
                    {"address": 0x19, "location": "air_mid"},
                    {"address": 0x1A, "location": "air_low"}
                ],
                "tsl2591x": {"address": 0x29, "location": "canopy"},
                "si7021": {"address": 0x40, "location": "ambient"},
                "aht20": {"address": 0x38, "location": "soil"}
            },
            "relays": {
                "pins": {
                    "ventilation_1": 17,
                    "ventilation_2": 18,
                    "led_1": 27,
                    "led_2": 22
                },
                "names": {
                    "ventilation_1": "Main Ventilation Fan",
                    "ventilation_2": "Auxiliary Ventilation",
                    "led_1": "Primary Grow Lights",
                    "led_2": "Supplemental LEDs"
                }
            },
            "automation": {
                "rules": [
                    {
                        "name": "Temperature Control",
                        "device_type": "ventilation",
                        "device_id": "ventilation_1",
                        "condition_type": "threshold",
                        "conditions": [
                            {
                                "sensor_type": "temperature",
                                "operator": ">",
                                "threshold": 25.0
                            }
                        ],
                        "is_active": True
                    }
                ]
            },
            "data_collection": {
                "interval_seconds": 60,
                "retry_attempts": 3,
                "batch_size": 10
            },
            "web_api": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": False
            }
        }
    
    def get(self, key: str, default=None):
        """Get configuration value by key"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def save(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self._config, f, indent=2)
```

## Dependencies

```txt
# requirements.txt
RPi.GPIO>=0.7.1
smbus2>=0.4.2
adafruit-circuitpython-mcp9808>=3.1.9
adafruit-circuitpython-tsl2591>=2.1.13
adafruit-circuitpython-si7021>=3.2.18
adafruit-circuitpython-ahtx0>=1.0.18
Flask>=2.3.0
Flask-SocketIO>=5.3.0
SQLAlchemy>=2.0.0
PyMySQL>=1.0.2
APScheduler>=3.10.0
python-dotenv>=1.0.0
requests>=2.28.0
pytest>=7.0.0
```

This implementation plan provides a solid foundation for your greenhouse automation system. The modular design allows for easy testing, maintenance, and future enhancements.