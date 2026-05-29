#pragma once
#include <Arduino.h>
#include <Adafruit_ADS1X15.h>

class AdcSensor {
public:
    // Native microcontroller interface channels
    static const uint8_t PIN_ESP_RESISTOR = 34; 
    static const uint8_t PIN_ESP_NTC      = 35; 

    // Dedicated external converter input assignments
    static const uint8_t ADS_CH_RESISTOR  = 0;  
    static const uint8_t ADS_CH_NTC       = 1;  

    bool begin();
    float readAdsMilliVolts(uint8_t channel);
    float readEspMilliVolts(uint8_t pin);

    void setFilter(bool enabled);

private:
    Adafruit_ADS1115 ads;
    bool _filterEnabled = false;
};