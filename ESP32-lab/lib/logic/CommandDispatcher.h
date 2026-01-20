#pragma once
#include <Arduino.h>
#include "../../lib/comm/SerialProtocol.h"
#include "../../lib/actuators/ActuatorController.h"
#include "../../lib/sensors/AdcSensor.h" // <-- PŘIDAT TENTO IMPORT

class CommandDispatcher {
public:
    // Upravený konstruktor přijímá i AdcSensor
    CommandDispatcher(SerialProtocol& protocol, ActuatorController& actuators, AdcSensor& adc)
        : _proto(protocol), _actuators(actuators), _adc(adc) {}

    void apply(const Command& cmd);
    void checkSafetyTimeout(); // <-- NOVÁ METODA

    bool isRunning() const { return _isRunning; }
    float getRateHz() const { return _rateHz; }

private:
    SerialProtocol& _proto;
    ActuatorController& _actuators;
    AdcSensor& _adc;

    bool _isRunning = false;
    float _rateHz = 2.0f;
    
    // Čas posledního přijatého příkazu (Watchdog)
    uint32_t _lastCommandTime = 0;
    static const uint32_t SAFETY_TIMEOUT_MS = 3000; // 3 sekundy ticho = stop
};