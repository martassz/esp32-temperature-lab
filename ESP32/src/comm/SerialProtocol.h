#pragma once

#include <Arduino.h>
#include "../sensors/DallasSensor.h"  // kvůli DallasBus

enum class CommandType {
    None,
    Start,
    Stop,
    SetRate
};

struct Command {
    CommandType type = CommandType::None;
    float rateHz = 0.0f;  // platné jen pro SetRate
};

class SerialProtocol {
public:
    void begin(unsigned long baud = 115200);

    // Přečte vstup ze Serialu, pokud najde kompletní příkaz, vrátí true a vyplní cmd
    bool readCommand(Command& cmd);

    // ACK + chyby
    void sendAckSetRate(float rateHz);
    void sendAck(const char* cmd);
    void sendError(const char* msg);

    // Datová zpráva s měřením
    void sendData(uint32_t t_ms,
                  float t_bme,
                  DallasBus& dallas);

private:
    String _buffer;

    void processLine(const String& line, Command& cmd);
};
