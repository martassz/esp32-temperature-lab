#include "MaxSensor.h"

MaxSensor::MaxSensor(uint8_t csPin, uint8_t mosiPin, uint8_t misoPin, uint8_t clkPin) 
    : maxPeripheral(csPin, mosiPin, misoPin, clkPin) {}

void MaxSensor::begin() {
    // Inicializace pro 3-vodičové zapojení (změň na MAX31865_2WIRE nebo MAX31865_4WIRE podle potřeby)
    if (!maxPeripheral.begin(MAX31865_3WIRE)) { 
        statusOk = false;
        return;
    }
    statusOk = true;
}

float MaxSensor::readTemperature() {
    if (!statusOk) return NAN;
    return maxPeripheral.temperature(RNOMINAL, RREF);
}

float MaxSensor::readVoltage() {
    if (!statusOk) return NAN;
    uint16_t rtd = maxPeripheral.readRTD();
    return ((float)rtd / 32768.0f) * 3300.0f;
}