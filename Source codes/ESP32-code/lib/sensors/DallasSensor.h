#pragma once
#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>

class DallasBus {
public:
    explicit DallasBus(uint8_t dataPin);
    void begin();
    void update(); 
    uint8_t getSensorCount() const { return sensorCount; }
    float getTemperatureC(uint8_t index);
    bool isOk() const { return sensorCount > 0; }

private:
    static const uint8_t MAX_SENSORS = 4;
    uint8_t pin;
    OneWire oneWire;
    DallasTemperature sensors;
    uint8_t sensorCount = 0;
    DeviceAddress addresses[MAX_SENSORS];
    float lastTemps[MAX_SENSORS]; 
    uint32_t lastRequestTime = 0; 
    
    bool readAddress(uint8_t index, DeviceAddress &addr);
};