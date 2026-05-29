"""
App/core/sensors.py
Centralized repository managing sensor nomenclature, display prioritization, 
and associated metric unities across the entire application stack.
"""
import re

# --- DISPLAY PRIORITY MATRIX ---
# Lower index dictates higher layout precedence in dynamic rendering contexts.
# Excluded sensors (e.g., PWM values) automatically default to lowest priority.
SENSOR_ORDER = [
    "T_TMP",       
    "T_BME",       
    "T_PT1000",
    "T_DS",        
    "V_ADS_NTC",   
    "V_ADS_R",
    "V_ESP_NTC",   
    "V_ESP_R",
    "V_PT1000"
]

def get_sensor_name(key: str) -> str:
    """
    Translates raw hardware identifiers into human-readable UI labels.
    """
    # 1. Statically assigned identifier mapping
    mapping = {
        "T_TMP": "Referenční teplota (TMP117)",
        "T_BME": "Teplota (BME280)",
        "H_BME": "Vlhkost (BME280)",
        "T_PT1000": "Teplota (PT1000)",
        
        "V_ADS_NTC": "U - termistoru (Externí ADC)",
        "V_ADS_R":   "U - rezistoru (Externí ADC)",
        
        "V_ESP_NTC": "U - termistoru (Interní ESP32 ADC)",
        "V_ESP_R":   "U - rezistoru (Interní ESP32 ADC)",

        "V_PT1000":  "U - platina (PT1000)",
        
        "PWM_HEAT": "Výkon topení",
        "PWM_COOL": "Výkon chlazení",

        "Target": "Cílová teplota"
    }
    
    if key in mapping:
        return mapping[key]

    # 2. Dynamic generation for enumerated arrays
    
    # Process dynamically enumerated Dallas thermal probes
    if key.startswith("T_DS"):
        try:
            # Shift zero-indexed hardware assignments for UI clarity
            index = int(key.replace("T_DS", "")) + 1
            return f"Teplota (DS18B20 #{index})"
        except ValueError:
            return key 

    # General fallback resolution for auxiliary parameters
    if key.startswith("PWM"):
        if key == "PWM":
            return "Výkon PWM"
        else:
            return f"PWM {key.replace('PWM_', '')}"

    # 3. Final sanitization routine replacing raw syntax
    return key.replace("_", " ")

def get_sensor_unit(key: str) -> str:
    """
    Resolves the applicable scientific metric unit mapped to the provided sensor string.
    """
    if key.startswith("T_"):
        return "°C"
    
    if key == "H_BME":
        return "%"

    if key == "Target":
        return "°C"
    
    if key.startswith("V_") or "ADC" in key or "ESP" in key:
        return "mV"
        
    if "PWM" in key:
        return "%"
        
    return ""

def get_sensor_sort_key(key: str) -> float:
    """
    Computes numerical sort indexes using predefined hierarchy definitions.
    Designed for integration with built-in sorting methods (`key=get_sensor_sort_key`).
    """
    # 1. Exact resolution check against established priority hierarchy
    if key in SENSOR_ORDER:
        return float(SENSOR_ORDER.index(key))
    
    # 2. Sequential fallback parsing for dynamic array clusters
    for i, prefix in enumerate(SENSOR_ORDER):
        if key.startswith(prefix):
            # Enforce micro-sorting offset to prevent overwriting index order (e.g. DS0 before DS1)
            extra = 0.0
            try:
                nums = re.findall(r'\d+', key)
                if nums:
                    extra = int(nums[-1]) * 0.01
            except: pass
            
            return float(i) + extra

    # 3. Base case relegation for undefined components
    return 999.0