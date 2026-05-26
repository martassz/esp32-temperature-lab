#include "AdcSensor.h"

bool AdcSensor::begin() {
    analogReadResolution(12); // ESP32 interně 12 bitů
    
    if (!ads.begin(0x49)) {
        return false;
    }
    // GAIN_TWOTHIRDS: +/- 6.144V (1 bit = 0.1875 mV)
    ads.setGain(GAIN_TWOTHIRDS);
    return true;
}

void AdcSensor::setFilter(bool enabled) {
    _filterEnabled = enabled;
}

float AdcSensor::readAdsMilliVolts(uint8_t channel) {
    int16_t raw = ads.readADC_SingleEnded(channel);
    // computeVolts vrací V, násobíme 1000 na mV
    return ads.computeVolts(raw) * 1000.0f;
}

float AdcSensor::readEspMilliVolts(uint8_t pin) {
    if (_filterEnabled) {
        // Můžeš bezpečně zvýšit, paměťově je to na ESP32 v pohodě (200 intů = 800 bytů na stacku)
        const int SAMPLES = 200; 
        int values[SAMPLES];
        
        for(int i = 0; i < SAMPLES; i++) {
            values[i] = analogReadMilliVolts(pin);
            delayMicroseconds(300); 
            
            // Každých 50 vzorků předáme na chvíli řízení RTOSu (systému), 
            // aby mohl obsloužit watchdog a nespadlo to.
            if (i % 50 == 0) {
                yield(); 
            }
        }

        // --- RYCHLÉ TŘÍDĚNÍ ---
        // std::sort používá introsort s časovou složitostí O(N log N).
        // Bude to hotové zlomek milisekundy i pro stovky vzorků.
        std::sort(values, values + SAMPLES);

        // --- EXTRÉMNÍ OŘEZ ---
        long sum = 0;
        
        // Dynamicky spočítáme 25 % z celkového počtu, aby ořez fungoval 
        // správně bez ohledu na to, jaké SAMPLES zrovna nastavíš.
        const int TRIM_COUNT = SAMPLES / 4; 
        
        for(int i = TRIM_COUNT; i < (SAMPLES - TRIM_COUNT); i++) {
            sum += values[i];
        }
        
        int validCount = SAMPLES - (2 * TRIM_COUNT);
        return (float)sum / (float)validCount;

    } else {
        // --- BEZ FILTRACE ---
        return (float)analogReadMilliVolts(pin);
    }
}