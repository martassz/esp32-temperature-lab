#pragma once
#include <Arduino.h>

class ActuatorController {
public:
    // Power MOSFET gate interface assignments
    static const uint8_t PIN_HEATER = 18;
    static const uint8_t PIN_COOLER = 19;

    // Hardware timer channel allocations
    static const uint8_t CH_HEATER = 0;
    static const uint8_t CH_COOLER = 1;

    void begin();
    void setHeater(float percent);
    void setCooler(float percent);
    void stopAll();
};