#include "TmpSensor.h"

bool TmpSensor::begin() {
    if (!tmp117.begin(0x48)) {
        return tmp117.begin();
    }
    return true;
}

float TmpSensor::readTemperatureC() {
    sensors_event_t temp;
    tmp117.getEvent(&temp);
    return temp.temperature;
}