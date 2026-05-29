#include "AdcSensor.h"
#include <algorithm>

bool AdcSensor::begin() {
    analogReadResolution(12); 
    
    if (!ads.begin(0x49)) {
        return false;
    }
    ads.setGain(GAIN_TWOTHIRDS);
    return true;
}

void AdcSensor::setFilter(bool enabled) {
    _filterEnabled = enabled;
}

float AdcSensor::readAdsMilliVolts(uint8_t channel) {
    int16_t raw = ads.readADC_SingleEnded(channel);
    return ads.computeVolts(raw) * 1000.0f;
}

float AdcSensor::readEspMilliVolts(uint8_t pin) {
    if (_filterEnabled) {
        const int SAMPLES = 200; 
        int values[SAMPLES];
        
        // Populate sample buffer at controlled sequence intervals
        for(int i = 0; i < SAMPLES; i++) {
            values[i] = analogReadMilliVolts(pin);
            delayMicroseconds(300); 
            
            if (i % 50 == 0) {
                yield(); 
            }
        }

        // Apply statistical sort to prepare distribution subset
        std::sort(values, values + SAMPLES);

        long sum = 0;
        const int TRIM_COUNT = SAMPLES / 4; 
        
        // Calculate trimmed mean to mitigate high-frequency noise spikes
        for(int i = TRIM_COUNT; i < (SAMPLES - TRIM_COUNT); i++) {
            sum += values[i];
        }
        
        int validCount = SAMPLES - (2 * TRIM_COUNT);
        return (float)sum / (float)validCount;

    } else {
        return (float)analogReadMilliVolts(pin);
    }
}