# Laboratory Exercise Platform for Ambient Temperature Measurement

This project is a comprehensive solution for a Bachelor's thesis and laboratory exercise focused on measuring ambient temperature using various methods. It consists of a hardware station based on the ESP32 microcontroller and a desktop application for data visualization and analysis.

The platform allows students to compare accuracy, resolution, and time response of different sensor types (Digital, Analog, Passive components) under controlled conditions.

## Project Goals

This repository implements the practical part of the laboratory exercise design:
1.  **Sensor Comparison:** Verification of accuracy and dynamic response of sensors (BME280, TMP117, DS18B20, Thermistors).
2.  **Data Acquisition:** Using ESP32 for reliable data logging via JSON over Serial.
3.  **Temperature Control:** Platform for controlled ambient temperature change (Heating/Cooling).
4.  **Visualization:** Desktop GUI for real-time plotting and data export.

## Repository Structure

* `App/` - Python desktop application (GUI) for control and visualization.
* `ESP32-lab/` - C++ Firmware for the ESP32 microcontroller (PlatformIO project).

---

## Hardware Specification

**Microcontroller:** ESP32 DevKit v1

### Supported Sensors
The firmware supports the following sensors connected simultaneously:
* **BME280** (I2C): Combined temperature, humidity, and pressure sensor.
* **TMP117** (I2C): High-precision reference temperature sensor.
* **DS18B20** (OneWire): Digital temperature sensor (supports multiple sensors on one bus).
* **ADS1115** (I2C): External 16-bit ADC for precise analog measurements (NTC/Resistor).
* **Internal ADC**: Used for basic voltage measurements on ESP32 pins.

### Actuators (Temperature Control)
* **Heater:** Resistive load controlled via PWM.
* **Cooler:** Peltier module or Fan controlled via PWM.

### Pinout Configuration

| Component         | Interface      | ESP32 Pin | Notes |
|-------------------|----------------|-----------|-------|
| **BME280** | I2C SDA        | GPIO 21   | |
| **TMP117** | I2C SCL        | GPIO 22   | |
| **ADS1115** | I2C            | 21 / 22   | Address 0x49 (configurable) |
| **DS18B20** | OneWire        | GPIO 4    | Requires 4k7 pull-up resistor |
| **Heater (MOSFET)**| PWM Channel 0 | GPIO 18   | |
| **Cooler (MOSFET)**| PWM Channel 1 | GPIO 19   | |
| **Internal ADC** | Analog Input   | GPIO 34   | Resistor divider measurement |
| **Internal ADC** | Analog Input   | GPIO 35   | NTC Thermistor divider measurement |

---

## Software Application

The desktop application provides a user-friendly interface for the laboratory exercise.

### Features
* **Connection Manager:** Auto-detection of COM ports and handshake with ESP32.
* **Real-time Plotting:** High-performance graphing using `pyqtgraph`.
* **Sensor Selection:** Ability to toggle specific sensors for visualization.
* **Actuator Control:** Manual PWM slider for Heater and Cooler control.
* **Data Export:** Export measured data to CSV format for further processing (Excel/MATLAB).
* **Measurement Modes:** Supports different measurement scenarios (e.g., "Part 1: Resistive Sensors", "Slow Measurement").

### Dependencies
The application is built with Python 3.11+ and requires the following libraries:
* `PySide6` (Qt for Python)
* `pyqtgraph`
* `pyserial`

---

## Installation and Usage

### 1. Firmware (ESP32)
1.  Install **VS Code** with the **PlatformIO** extension.
2.  Open the `ESP32-lab` folder.
3.  Connect the ESP32 via USB.
4.  Build and Upload the firmware (PlatformIO automatically handles libraries: Adafruit BME280, DallasTemperature, etc.).

### 2. Desktop App (PC)
1.  Ensure Python 3.11 is installed.
2.  Navigate to the `App` directory.
3.  Install dependencies:
    ```bash
    pip install PySide6 pyqtgraph pyserial
    ```
4.  Run the application:
    ```bash
    python main.py
    ```

## Communication Protocol

The PC and ESP32 communicate via USB Serial (115200 baud) using a JSON-based protocol.

**Data Packet Example (ESP -> PC):**
```json
{
  "type": "data",
  "t_ms": 12500,
  "T_BME": 24.50,
  "T_TMP": 24.55,
  "V_ADS_NTC": 1150.2,
  "T_DS0": 24.25
}
