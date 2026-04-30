#include "DallasSensor.h"

DallasBus::DallasBus(uint8_t dataPin)
    : pin(dataPin),
      oneWire(dataPin),
      sensors(&oneWire) {}

void DallasBus::begin() {
    sensors.begin();
    sensors.setWaitForConversion(false); // <--- ZÁSADNÍ: Vypnutí blokování
    
    uint8_t count = sensors.getDeviceCount();
    if (count > MAX_SENSORS) {
        count = MAX_SENSORS;
    }
    sensorCount = 0;
    for (uint8_t i = 0; i < count; ++i) {
        DeviceAddress addr;
        if (readAddress(i, addr)) {
            memcpy(addresses[sensorCount], addr, sizeof(DeviceAddress));
            lastTemps[sensorCount] = NAN; // Výchozí hodnota
            sensorCount++;
        }
    }
    
    // Pošleme první žádost okamžitě po inicializaci
    if (sensorCount > 0) {
        sensors.requestTemperatures();
        lastRequestTime = millis();
    }
}

bool DallasBus::readAddress(uint8_t index, DeviceAddress &addr) {
    if (!sensors.getAddress(addr, index)) {
        return false;
    }
    if (addr[0] != 0x28) {
        return false;
    }
    return true;
}

// <--- PŘIDÁNO: Tato funkce se bude točit v hlavním loopu
void DallasBus::update() {
    if (sensorCount == 0) return;
    
    // Zkontrolujeme, zda už uplynulo 750 ms (čas pro 12bit převod)
    if (millis() - lastRequestTime >= 750) {
        // Přečteme hotové teploty do paměti (tohle trvá jen pár milisekund)
        for (uint8_t i = 0; i < sensorCount; ++i) {
            float t = sensors.getTempC(addresses[i]);
            if (t > -127.0f) {
                lastTemps[i] = t;
            } else {
                lastTemps[i] = NAN;
            }
        }
        // Hned pošleme žádost o další měření a jdeme dělat jinou práci
        sensors.requestTemperatures();
        lastRequestTime = millis();
    }
}

float DallasBus::getTemperatureC(uint8_t index) {
    if (index >= sensorCount || sensorCount == 0) {
        return NAN;
    }
    // <--- PŘIDÁNO: Už žádné čekání, vracíme rovnou z paměti!
    return lastTemps[index];
}