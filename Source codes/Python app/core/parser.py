from typing import Dict, Optional
import json


def parse_temp_line(line: str) -> Dict[str, float]:
    """
    Decodes legacy string-based telemetry payloads.
    Example expected syntax:
      T_BME=24.1234; T_DS0=23.5000; ...
      
    Automatically bypasses malformed pairs and 'nan' strings.
    Returns dictionary mapping of key-value parameters.
    """
    result: Dict[str, float] = {}

    if "T_BME" not in line:
        return result

    parts = [p.strip() for p in line.split(";") if p.strip()]
    for part in parts:
        if "=" not in part:
            continue
        key, val = [x.strip() for x in part.split("=", 1)]
        if not key:
            continue
        if val.lower() == "nan":
            continue
        try:
            result[key] = float(val.replace(",", "."))
        except ValueError:
            continue

    return result


def parse_json_message(line: str) -> Optional[dict]:
    """
    Validates and decodes incoming JSON structured payloads.
    Designed to parse standard structural outputs from the ESP32 framework.
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    if isinstance(obj, dict):
        return obj
    return None


def extract_data_values(msg: dict) -> Dict[str, float]:
    """
    Isolates purely numeric sensor measurements from standard data packets.
    Strips away overhead parameters such as payload type and timestamp arrays.
    """
    if msg.get("type") != "data":
        return {}

    result: Dict[str, float] = {}
    for key, val in msg.items():
        if key in ("type", "t_ms"):
            continue
        if isinstance(val, (int, float)):
            result[key] = float(val)

    return result