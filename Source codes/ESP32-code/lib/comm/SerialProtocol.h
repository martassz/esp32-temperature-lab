#pragma once
#include <Arduino.h>
#include <BluetoothSerial.h>
#include "../sensors/DallasSensor.h"

enum class CommandType {
    None, Start, Stop, SetRate, SetPwm, Ping, SetFilter 
};

struct Command {
    CommandType type = CommandType::None;
    int value = 0;         
    float rateHz = 0.0f;
    int pwmChannel = 0;    
    float pwmValue = 0.0f; 
};

class SerialProtocol {
public:
    void begin(unsigned long baud);
    void sendHello(bool bme_ok, uint8_t dallas_count, bool adc_ok, bool tmp_ok, bool pt1000_ok);
    bool readCommand(Command& cmd);
    void sendAck(const char* cmd);
    void sendAckSetRate(float rateHz);
    void sendError(const char* msg);
    void sendData(uint32_t t_ms, float t_tmp, float t_bme, float h_bme, DallasBus& dallas, float v1, float v2, float v3, float v4, float v_pt1000, float t_pt1000);

private:
    BluetoothSerial SerialBT;
    String _buffer;
    String _bufferBT;
    static const size_t MAX_BUFFER = 256;
    
    void processLine(const String& line, Command& cmd);
    void sendToBoth(const String& msg); 
};