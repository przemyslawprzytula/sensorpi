# Greenhouse Sensor Data Collector

A comprehensive Raspberry Pi 3-based greenhouse automation system that monitors environmental conditions and controls ventilation/LED systems based on sensor data and configurable parameters.

## Project Overview

This system transforms a Raspberry Pi 3 into an intelligent greenhouse controller that:
- Collects data from multiple I2C sensors (temperature, humidity, light)
- Controls ventilation fans and LED grow lights via an 8-channel relay module
- Stores data remotely in a MySQL database
- Provides a web-based interface for monitoring and manual control
- Implements rule-based automation with seasonal adjustments

## Hardware Components

### Sensors
- **Multiple MCP9808** - I2C temperature sensors (±0.5°C accuracy)
- **TSL2591X** - I2C light intensity sensor
- **Si7021** - I2C temperature and humidity sensor
- **AHT20** - I2C temperature and humidity sensor (STEMMA QT)

### Control Hardware
- **Raspberry Pi 3** - Main controller
- **TW-281** - 8-channel relay module for device control
- **Ventilation fans** - Climate control
- **LED grow lights** - Supplemental lighting

## Software Architecture

The system is built with a modular Python architecture:

- **Sensor Layer** - I2C communication and data collection
- **Control Layer** - Relay control and device management
- **Automation Engine** - Rule-based control with manual override
- **Database Layer** - Remote MySQL data storage
- **Web Interface** - Real-time dashboard and controls
- **API Layer** - RESTful endpoints for data access

## Key Features

### Data Collection
- Multi-sensor temperature monitoring at different heights
- Humidity tracking from multiple sensors
- Light intensity measurement at canopy level
- Configurable reading intervals (30-60 seconds)
- Data validation and error handling

### Automation Control
- Threshold-based ventilation control
- Time-based LED scheduling
- Manual override capabilities
- Seasonal adjustment support
- Emergency shutdown functionality

### Web Interface
- Real-time sensor data display
- Historical data visualization
- Manual device control
- Configuration management
- Mobile-responsive design

### Data Management
- Remote MySQL database storage
- Historical data retention (1 year)
- Data export capabilities
- Backup and recovery procedures

## Project Structure

```
sensorpi/
├── config/           # Configuration management
├── sensors/          # Sensor drivers and management
├── controllers/      # Relay control and device management
├── automation/       # Rule engine and automation logic
├── database/         # Database models and access layer
├── api/             # Web API endpoints
├── web/             # Frontend interface
├── services/        # Background services
├── tests/           # Unit and integration tests
├── scripts/         # Setup and maintenance scripts
└── systemd/         # Service configuration files
```

## Development Phases

### Phase 1: Foundation (Weeks 1-2)
- Hardware setup and sensor integration
- Database connection and basic web interface
- Core data collection functionality

### Phase 2: Core Automation (Weeks 3-4)
- Relay control system implementation
- Automation engine with rule-based control
- Manual override functionality
- Enhanced web interface

### Phase 3: Advanced Features (Weeks 5-6)
- Historical analytics and data visualization
- Real-time updates via WebSocket
- Advanced automation with seasonal patterns
- Mobile responsiveness

### Phase 4: Production Ready (Weeks 7-8)
- Comprehensive error handling and monitoring
- System documentation and deployment
- Testing and quality assurance
- Performance optimization

## Getting Started

### Prerequisites
- Raspberry Pi 3 with Raspberry Pi OS
- MySQL database server (remote)
- All hardware components listed above
- Basic knowledge of Python and Linux

### Installation
1. Clone the repository to your Raspberry Pi
2. Follow the hardware setup guide in `hardware_setup.md`
3. Run the setup script: `./scripts/setup.sh`
4. Configure database settings in `config/settings.py`
5. Start the services: `sudo systemctl start sensor-collector`

### Configuration
Edit `config/settings.json` to customize:
- Sensor addresses and locations
- Relay pin assignments
- Automation rules and thresholds
- Database connection parameters
- Web interface settings

## Documentation

- [`project_architecture.md`](project_architecture.md) - Detailed system architecture
- [`hardware_setup.md`](hardware_setup.md) - Hardware installation and wiring
- [`software_implementation.md`](software_implementation.md) - Code structure and implementation
- [`development_roadmap.md`](development_roadmap.md) - Development timeline and phases
- [`docs/pi_setup.md`](docs/pi_setup.md) - Raspberry Pi provisioning and deployment steps

## Safety Considerations

- Use proper enclosures for high-voltage connections
- Include emergency stop functionality
- Follow local electrical codes
- Implement proper grounding
- Add fuses for overcurrent protection

## Future Enhancements

- Machine learning for optimization
- Weather forecast integration
- Mobile app development
- Multi-greenhouse support
- Energy consumption monitoring
- Advanced analytics and reporting

## Contributing

This project is designed to be modular and extensible. Contributions are welcome for:
- New sensor integrations
- Automation rule improvements
- Web interface enhancements
- Documentation improvements
- Bug fixes and performance optimizations

## License

This project is open source and available under the MIT License.

## Support

For questions, issues, or contributions, please refer to the project documentation or create an issue in the project repository.