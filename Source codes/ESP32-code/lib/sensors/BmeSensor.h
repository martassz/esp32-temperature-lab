#pragma once

#include <Arduino.h>
#include <Adafruit_BME280.h>

class BmeSensor {
public:
    // Evaluate standard device bus addresses automatically
    bool beginAuto();
    bool begin(uint8_t i2cAddress);

    float readTemperatureC();
    float readHumidity();
    bool isOk() const { return initialized; }
    uint8_t getAddress() const { return usedAddress; }

private:
    Adafruit_BME280 bme;
    bool initialized = false;
    uint8_t usedAddress = 0;
};