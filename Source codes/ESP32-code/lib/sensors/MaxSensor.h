#pragma once
#include <Arduino.h>
#include <Adafruit_MAX31865.h>

class MaxSensor {
public:
    explicit MaxSensor(uint8_t csPin, uint8_t mosiPin, uint8_t misoPin, uint8_t clkPin);
    void begin();
    float readTemperature();
    float readVoltage();
    bool isOk() const { return statusOk; }

private:
    Adafruit_MAX31865 maxPeripheral;
    bool statusOk = false;
    const float RREF = 4300.0f;     
    const float RNOMINAL = 1000.0f; 
};