#include "CommandDispatcher.h"

void CommandDispatcher::apply(const Command& cmd) {
    _lastCommandTime = millis();

    switch (cmd.type) {
        case CommandType::Start:
            _isRunning = true;
            _proto.sendAck("start");
            break;

        case CommandType::Stop:
            _isRunning = false;
            _actuators.stopAll();
            _proto.sendAck("stop");
            break;

        case CommandType::SetFilter:
            _adc.setFilter(cmd.value == 1);
            _proto.sendAck("set_filter");
            break;
        
        case CommandType::Ping:
            break;

        case CommandType::SetRate:
            if (cmd.rateHz > 0.0f && cmd.rateHz <= 10.0f) {
                _rateHz = cmd.rateHz;
                _proto.sendAckSetRate(_rateHz);
            } else {
                _proto.sendError("invalid_rate");
            }
            break;

        case CommandType::SetPwm:
            if (cmd.pwmChannel == 0) {
                _actuators.setHeater(cmd.pwmValue);
            } else if (cmd.pwmChannel == 1) {
                _actuators.setCooler(cmd.pwmValue);
            }
            _proto.sendAck("set_pwm");
            break;
            
        default: break;
    }
}

void CommandDispatcher::checkSafetyTimeout() {
    // Fail-safe interlock routine preventing runaway states upon communication loss
    if (_isRunning && (millis() - _lastCommandTime > SAFETY_TIMEOUT_MS)) {
        _isRunning = false;
        _actuators.stopAll();
        _proto.sendError("safety_timeout"); 
    }
}