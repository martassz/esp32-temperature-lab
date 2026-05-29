#include <Arduino.h>
#include <Wire.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#include "BmeSensor.h"
#include "DallasSensor.h"
#include "AdcSensor.h"
#include "TmpSensor.h"
#include "SerialProtocol.h"
#include "../lib/actuators/ActuatorController.h"
#include "../lib/logic/CommandDispatcher.h"
#include "MaxSensor.h"

// Hardware pin definitions
static const uint8_t I2C_SDA = 21;
static const uint8_t I2C_SCL = 22;
static const uint8_t PIN_ONEWIRE = 4;
static const uint8_t PIN_MAX_CS   = 5;
static const uint8_t PIN_MAX_MOSI = 23;
static const uint8_t PIN_MAX_MISO = 25;
static const uint8_t PIN_MAX_CLK  = 26;

// Peripheral and communication controller instances
BmeSensor bme;
DallasBus dallas(PIN_ONEWIRE);
AdcSensor adc;
TmpSensor tmp;
ActuatorController actuators;
SerialProtocol proto;
MaxSensor pt1000(PIN_MAX_CS, PIN_MAX_MOSI, PIN_MAX_MISO, PIN_MAX_CLK);

CommandDispatcher dispatcher(proto, actuators, adc);

// Time tracking for periodic sampling
static uint32_t g_last_ms = 0;

// Hardware initialization status flags
bool g_bme_ok = false;
uint8_t g_dallas_count = 0;
bool g_adc_ok = false;
bool g_tmp_ok = false;
bool g_pt1000_ok = false;

void setup() {
    // Disable brownout detection to maximize stability under transient loads
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

    proto.begin(115200); 
    delay(1000); 
    
    Wire.begin(I2C_SDA, I2C_SCL, 100000); 

    // Hardware subsystem initialization
    actuators.begin();
    dallas.begin();
    pt1000.begin();
    
    // Verify module availability and establish state flags
    g_bme_ok = bme.beginAuto();
    g_adc_ok = adc.begin();
    g_tmp_ok = tmp.begin();
    g_pt1000_ok = pt1000.isOk(); 
    g_dallas_count = dallas.getSensorCount();

    Serial.println("=== Temp-Lab ESP32 Ready ===");
}

void loop() {
    // Service background non-blocking sensor conversions
    dallas.update();

    // Query and handle communication bus commands
    Command cmd;
    if (proto.readCommand(cmd)) {
        dispatcher.apply(cmd);

        // Broadcast current hardware inventory state upon validation request
        if (cmd.type == CommandType::Ping) {
            proto.sendHello(g_bme_ok, g_dallas_count, g_adc_ok, g_tmp_ok, g_pt1000_ok);
        }
    }

    // Verify system safety constraints are met
    dispatcher.checkSafetyTimeout();

    // Execute periodic measurement sequences when active
    if (dispatcher.isRunning() && dispatcher.getRateHz() > 0.0f) {
        uint32_t now = millis();
        uint32_t period = (uint32_t)(1000.0f / dispatcher.getRateHz());
        if (period == 0) period = 1;

        if (now - g_last_ms >= period) {
            g_last_ms = now;

            float t_tmp = tmp.readTemperatureC();
            float t_bme = bme.readTemperatureC();
            float h_bme = bme.readHumidity();
            float mv_ads_r   = adc.readAdsMilliVolts(AdcSensor::ADS_CH_RESISTOR);
            float mv_ads_ntc = adc.readAdsMilliVolts(AdcSensor::ADS_CH_NTC);
            float mv_esp_r   = adc.readEspMilliVolts(AdcSensor::PIN_ESP_RESISTOR);
            float mv_esp_ntc = adc.readEspMilliVolts(AdcSensor::PIN_ESP_NTC);
            float v_pt1000 = pt1000.readVoltage();
            float t_pt1000 = pt1000.readTemperature();

            // Stream parsed datasets to available telemetry links
            proto.sendData(now, t_tmp, t_bme, h_bme, dallas, 
                           mv_ads_r, mv_ads_ntc, 
                           mv_esp_r, mv_esp_ntc,
                           v_pt1000, t_pt1000);
        }
    }
    delay(1);
}