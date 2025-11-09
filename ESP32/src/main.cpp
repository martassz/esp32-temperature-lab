#include <Arduino.h>
#include <Wire.h>

#include "sensors/BmeSensor.h"
#include "sensors/DallasSensor.h"

// DOIT ESP32 DevKit V1
static const uint8_t I2C_SDA_PIN = 21;
static const uint8_t I2C_SCL_PIN = 22;
static const uint8_t DALLAS_PIN  = 4;

BmeSensor bme;
DallasBus dallas(DALLAS_PIN);

void setup() {
    Serial.begin(115200);
    delay(500);

    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);

    bool bme_ok = bme.beginAuto();
    dallas.begin();

    Serial.println("=== Temp-lab ESP32 ready ===");
    Serial.print("BME280: ");
    Serial.println(bme_ok ? "OK" : "NENI");
    Serial.print("Dallas senzoru: ");
    Serial.println(dallas.getSensorCount());
    Serial.println("Prikaz 'T' => T_BME=..; T_DS0=..; ...;");
    Serial.println("=====================================");
}

void loop() {
    if (Serial.available() > 0) {
        char c = (char)Serial.read();
        if (c == 'T') {
            float t_bme = bme.readTemperatureC();

            Serial.print("T_BME=");
            if (isnan(t_bme)) Serial.print("nan");
            else Serial.print(t_bme, 4);

            uint8_t count = dallas.getSensorCount();
            for (uint8_t i = 0; i < count; ++i) {
                float t = dallas.getTemperatureC(i);

                Serial.print("; T_DS");
                Serial.print(i);
                Serial.print("=");

                if (isnan(t)) Serial.print("nan");
                else Serial.print(t, 4);
            }

            Serial.println(";");
        }
    }

    delay(2);
}
