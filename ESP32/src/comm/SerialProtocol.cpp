#include "SerialProtocol.h"

void SerialProtocol::begin(unsigned long baud) {
    Serial.begin(baud);
    unsigned long start = millis();
    while (!Serial && (millis() - start < 2000)) {
        ; // některé hosty je potřeba chvilku počkat
    }

    // Úvodní zpráva pro PC aplikaci
    Serial.println("{\"type\":\"hello\",\"device\":\"temp-lab\",\"version\":\"1.0\"}");
}

bool SerialProtocol::readCommand(Command& cmd) {
    cmd.type = CommandType::None;
    cmd.rateHz = 0.0f;

    while (Serial.available() > 0) {
        char c = (char)Serial.read();

        if (c == '\n' || c == '\r') {
            if (_buffer.length() == 0) {
                continue;
            }
            String line = _buffer;
            _buffer = "";
            processLine(line, cmd);
            if (cmd.type != CommandType::None) {
                return true;
            }
        } else {
            if (_buffer.length() < 80) {
                _buffer += c;
            }
        }
    }

    return false;
}

void SerialProtocol::processLine(const String& lineIn, Command& cmd) {
    String line = lineIn;
    line.trim();
    if (line.length() == 0) {
        return;
    }

    // DEBUG (klidně si necháš, jestli chceš vidět příkazy):
    Serial.print("{\"debug_cmd\":\"");
    Serial.print(line);
    Serial.println("\"}");

    String upper = line;
    upper.toUpperCase();

    // --- START ---
    if (upper == "START") {
        cmd.type = CommandType::Start;
        return;
    }

    // --- STOP ---
    if (upper == "STOP") {
        cmd.type = CommandType::Stop;
        return;
    }

    // --- PING ---
    if (upper == "PING") {
        sendAck("ping");
        return;
    }

    // --- SET RATE X ---
    // Očekáváme "SET RATE 5" nebo "SET RATE 5.0"
    if (upper.startsWith("SET RATE")) {
        // Najdeme druhou mezeru
        int firstSpace = upper.indexOf(' ');                // za "SET"
        int secondSpace = upper.indexOf(' ', firstSpace+1); // za "RATE"

        if (secondSpace > 0 && secondSpace + 1 < line.length()) {
            String valStr = line.substring(secondSpace + 1);
            valStr.trim();

            float rate = valStr.toFloat();
            if (rate > 0.0f && rate <= 1000.0f) {
                cmd.type = CommandType::SetRate;
                cmd.rateHz = rate;
                return;
            } else {
                sendError("invalid_set_rate");
                return;
            }
        } else {
            sendError("invalid_set_rate");
            return;
        }
    }

    // --- neznámý příkaz ---
    sendError("unknown_command");
}

void SerialProtocol::sendAckSetRate(float rateHz) {
    Serial.print("{\"type\":\"ack\",\"cmd\":\"set_rate\",\"rate_hz\":");
    Serial.print(rateHz, 4);
    Serial.println("}");
}

void SerialProtocol::sendAck(const char* cmd) {
    Serial.print("{\"type\":\"ack\",\"cmd\":\"");
    Serial.print(cmd);
    Serial.println("\"}");
}

void SerialProtocol::sendError(const char* msg) {
    Serial.print("{\"type\":\"error\",\"msg\":\"");
    Serial.print(msg);
    Serial.println("\"}");
}

void SerialProtocol::sendData(uint32_t t_ms,
                              float t_bme,
                              DallasBus& dallas)
{
    Serial.print("{\"type\":\"data\",\"t_ms\":");
    Serial.print(t_ms);

    // BME280 teplota
    Serial.print(",\"T_BME\":");
    if (isnan(t_bme)) Serial.print("null");
    else Serial.print(t_bme, 4);

    // Dallas senzory
    uint8_t count = dallas.getSensorCount();
    for (uint8_t i = 0; i < count; ++i) {
        float t = dallas.getTemperatureC(i);
        Serial.print(",\"T_DS");
        Serial.print(i);
        Serial.print("\":");
        if (isnan(t)) Serial.print("null");
        else Serial.print(t, 4);
    }

    Serial.println("}");
}
