# Temperature Measurement and Data Logging Platform

ESP32 + Python desktop application for teaching temperature measurement methods, sensor comparison and basic data analysis.

This project implements a modular system for measuring, logging and analyzing temperature using multiple types of sensors. The system is intended for a laboratory exercise where students compare different temperature-measurement methods, sensor accuracy, sensitivity and dynamic behavior.

The platform consists of:

- ESP32 DevKit v1 firmware written in C++
- Python desktop application for real-time visualization and datalogging
- Multiple temperature sensors of different categories
- PWM-controlled heating and cooling elements

## Hardware Overview

Currently integrated sensors and components:

### Temperature sensors

- NTC thermistor, 10 kΩ
- Metal-film resistor, 10 kΩ (for temperature coefficient comparison)
- TMP117 (high-accuracy reference thermometer)
- DS18B20 (standard version)
- DS18B20 (waterproof version)
- BME280 (temperature and humidity)
- ADS1115 (16-bit ADC for NTC and resistor measurements)

### Actuators

- PWM fan
- Peltier module (TEC1-12706)
- Resistive heater
- MOSFET PWM driver module (LR7843)

### Microcontroller

- ESP32 DevKit v1 (USB communication, C++ firmware)

### PC Software

- Python desktop application
- USB serial communication
- Real-time plotting
- CSV logging

## Software Overview

### ESP32 Firmware (C++)

- Modular sensor drivers (I2C, ADC, OneWire)
- ADS1115 voltage sampling for NTC and metal-film resistor
- JSON messages sent over USB (CDC)
- PWM control for cooling/heating elements

### Python Application

- Serial port communication
- JSON parsing
- Real-time plotting of selected sensors
- CSV datalogging
- Basic post-processing and comparison of sensor data

## Project Goals

### Completed

- Basic ESP32 firmware
- USB JSON communication between ESP32 and PC
- ADS1115 integration for analog measurements
- TMP117, BME280 and DS18B20 sensor support
- Python application with real-time plotting

### Work in Progress

- Refinement of plotting (axis alignment, scaling, UI tweaks)
- Improving robustness of USB communication and reconnection
- Refactoring firmware into clearer modules
- CSV datalogging

### Planned

- Dew-point calculation tools in the Python application
- Simple calibration workflow for selected sensors
- Export of graphs directly from the application
- Detailed documentation for each laboratory task

## Citations

All external libraries, datasheets and referenced materials will be cited according to ČSN ISO 690 in the written thesis. A separate bibliography file will be added later.
