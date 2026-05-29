#include "ActuatorController.h"

void ActuatorController::begin() {
    // Configure asynchronous driver parameters to 1 kHz frequency at 10-bit resolution
    ledcSetup(CH_HEATER, 1000, 10);
    ledcAttachPin(PIN_HEATER, CH_HEATER);

    ledcSetup(CH_COOLER, 1000, 10);
    ledcAttachPin(PIN_COOLER, CH_COOLER);
    
    stopAll();
}

void ActuatorController::setHeater(float percent) {
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;
    
    uint32_t duty = (uint32_t)((percent / 100.0f) * 1023);
    
    // Prevent bridging conditions by enforcing mutual exclusion
    ledcWrite(CH_COOLER, 0);      
    ledcWrite(CH_HEATER, duty);
}

void ActuatorController::setCooler(float percent) {
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;

    uint32_t duty = (uint32_t)((percent / 100.0f) * 1023);
    
    // Prevent bridging conditions by enforcing mutual exclusion
    ledcWrite(CH_HEATER, 0);      
    ledcWrite(CH_COOLER, duty);
}

void ActuatorController::stopAll() {
    ledcWrite(CH_HEATER, 0);
    ledcWrite(CH_COOLER, 0);
}