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
        // --- AGRESIVNÍ FILTRACE (HEAVY TRIMMED MEAN) ---
        // Zvýšíme počet vzorků na 101 pro lepší statistiku
        const int SAMPLES = 101; 
        int values[SAMPLES];
        
        for(int i = 0; i < SAMPLES; i++) {
            values[i] = analogReadMilliVolts(pin);
            // Zkrátíme pauzu na 300 us.
            // Celkem to potrvá cca 30-35 ms, což je stále rychlé,
            // ale dost dlouhé na to, aby se vyrušil brum sítě (50Hz) i PWM šum.
            delayMicroseconds(300); 
        }

        // Seřadíme pole (Bubble Sort)
        for(int i = 0; i < SAMPLES - 1; i++) {
            for(int j = 0; j < SAMPLES - i - 1; j++) {
                if (values[j] > values[j + 1]) {
                    int temp = values[j];
                    values[j] = values[j + 1];
                    values[j + 1] = temp;
                }
            }
        }

        // --- EXTRÉMNÍ OŘEZ ---
        // Zahodíme 25 nejmenších a 25 největších hodnot (tj. cca 25 % z každé strany).
        // Zbyde nám 51 nejstabilnějších hodnot uprostřed.
        long sum = 0;
        int count = 0;
        const int TRIM_COUNT = 25; 
        
        for(int i = TRIM_COUNT; i < (SAMPLES - TRIM_COUNT); i++) {
            sum += values[i];
            count++;
        }

        return (float)sum / (float)count;

    } else {
        // --- BEZ FILTRACE ---
        return (float)analogReadMilliVolts(pin);
    }
}