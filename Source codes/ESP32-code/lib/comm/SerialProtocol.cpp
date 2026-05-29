#include "SerialProtocol.h"

void SerialProtocol::begin(unsigned long baud) { 
    Serial.begin(baud); 
    while (!Serial && millis() < 2000); 
    
    SerialBT.begin("Porovnavani-Metod-ESP32");
}

void SerialProtocol::sendToBoth(const String& msg) {
    Serial.println(msg); 
    
    if (SerialBT.hasClient()) {
        SerialBT.println(msg);
    }
}

bool SerialProtocol::readCommand(Command& cmd) {
    cmd.type = CommandType::None;
    
    // Evaluate message fragments received over hardware interface
    while (Serial.available() > 0) {
        char c = (char)Serial.read();
        if (c == '\r') continue;
        if (c == '\n') {
            String line = _buffer;
            _buffer = "";
            line.trim();
            if (line.length() > 0) processLine(line, cmd);
            if (cmd.type != CommandType::None) return true;
        } else {
            if (_buffer.length() < MAX_BUFFER) _buffer += c;
            else _buffer = "";
        }
    }
    
    // Evaluate message fragments received over wireless connection
    while (SerialBT.available() > 0) {
        char c = (char)SerialBT.read();
        if (c == '\r') continue;
        if (c == '\n') {
            String line = _bufferBT;
            _bufferBT = "";
            line.trim();
            if (line.length() > 0) processLine(line, cmd);
            if (cmd.type != CommandType::None) return true;
        } else {
            if (_bufferBT.length() < MAX_BUFFER) _bufferBT += c;
            else _bufferBT = "";
        }
    }
    
    return false;
}

void SerialProtocol::processLine(const String& line, Command& cmd) {
    String up = line;
    up.trim(); up.toUpperCase();

    if (up == "START") { cmd.type = CommandType::Start; return; }
    if (up == "STOP")  { cmd.type = CommandType::Stop; return; }
    if (up == "PING")  { cmd.type = CommandType::Ping; return; } 
    
    if (up.startsWith("SET PWM")) {
        int idx = up.indexOf("SET PWM");
        if (idx >= 0) {
            String rest = line.substring(idx + 7);
            rest.trim();
            int space = rest.indexOf(' ');
            if (space > 0) {
                cmd.type = CommandType::SetPwm;
                cmd.pwmChannel = rest.substring(0, space).toInt();
                cmd.pwmValue = rest.substring(space + 1).toFloat();
            }
        }
        return;
    }

    if (up.startsWith("SET FILTER")) {
        cmd.type = CommandType::SetFilter;
        cmd.value = line.substring(11).toInt(); 
        return;
    }

    if (up.startsWith("SET RATE")) {
        int idx = up.indexOf("SET RATE");
        if (idx >= 0) {
            String rest = line.substring(idx + 8);
            rest.trim();
            float rate = rest.toFloat();
            if (rate > 0.0f) {
                cmd.type = CommandType::SetRate;
                cmd.rateHz = rate;
            }
        }
        return;
    }
}

void SerialProtocol::sendHello(bool bme_ok, uint8_t dallas_count, bool adc_ok, bool tmp_ok, bool pt1000_ok) {
    String msg = "{\"type\":\"hello\",\"device\":\"temp-lab-v2\",\"bme\":";
    msg += (bme_ok?"true":"false"); msg += ",\"dallas\":"; msg += dallas_count;
    msg += ",\"adc\":"; msg += (adc_ok?"true":"false"); msg += ",\"tmp\":"; 
    msg += (tmp_ok?"true":"false"); msg += ",\"pt1000\":"; msg += (pt1000_ok?"true":"false");
    msg += "}";
    sendToBoth(msg);
}

void SerialProtocol::sendAckSetRate(float rateHz) { 
    String msg = "{\"type\":\"ack\",\"cmd\":\"set_rate\",\"rate_hz\":";
    msg += String(rateHz, 4) + "}";
    sendToBoth(msg);
}

void SerialProtocol::sendAck(const char* cmd) { 
    sendToBoth(String("{\"type\":\"ack\",\"cmd\":\"") + cmd + "\"}"); 
}

void SerialProtocol::sendError(const char* msg) { 
    sendToBoth(String("{\"type\":\"error\",\"msg\":\"") + msg + "\"}"); 
}

void SerialProtocol::sendData(uint32_t t_ms, float t_tmp, float t_bme, float h_bme, DallasBus& dallas, float v1, float v2, float v3, float v4, float v_pt1000, float t_pt1000) {
    String msg = "{\"type\":\"data\",\"t_ms\":"; msg += t_ms;
    
    msg += ",\"T_TMP\":"; msg += isnan(t_tmp) ? "null" : String(t_tmp, 4);
    msg += ",\"T_BME\":"; msg += isnan(t_bme) ? "null" : String(t_bme, 4);
    msg += ",\"H_BME\":"; msg += isnan(h_bme) ? "null" : String(h_bme, 4);
    msg += ",\"V_ADS_R\":"; msg += String(v1, 2); msg += ",\"V_ADS_NTC\":"; msg += String(v2, 2);
    msg += ",\"V_ESP_R\":"; msg += String(v3, 2); msg += ",\"V_ESP_NTC\":"; msg += String(v4, 2);
    msg += ",\"V_PT1000\":"; msg += String(v_pt1000, 4);
    msg += ",\"T_PT1000\":"; msg += isnan(t_pt1000) ? "null" : String(t_pt1000, 4);
    
    uint8_t c = dallas.getSensorCount();
    for(uint8_t i=0; i<c; ++i) { 
        msg += ",\"T_DS"; msg += i; msg += "\":"; 
        float t = dallas.getTemperatureC(i); 
        msg += isnan(t) ? "null" : String(t, 4); 
    }
    msg += "}";
    
    sendToBoth(msg);
}