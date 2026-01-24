"""
App/core/sensors.py
Centrální definice názvů, jednotek a priority řazení senzorů.
"""
import re

# --- DEFINICE PRIORITNÍHO POŘADÍ ---
# Čím je senzor v seznamu výše, tím dříve se zobrazí.
# PWM zde není uvedeno, proto spadne automaticky na konec (priorita 999).
SENSOR_ORDER = [
    "T_TMP",       # 1. Referenční teplota (TMP117)
    "T_BME",       # 2. Teplota vzduchu (BME)
    "T_DS",        # 3. Dallasy (obecný prefix pro T_DS0, T_DS1...)
    "V_ADS_NTC",   # 4. Napětí přesná (Externí ADC)
    "V_ADS_R",
    "V_ESP_NTC",   # 5. Napětí hrubá (Interní ESP)
    "V_ESP_R"
]

def get_sensor_name(key: str) -> str:
    """
    Převede technický klíč na čitelný název pro uživatele.
    """
    # 1. Pevně definované názvy
    mapping = {
        # Teploty
        "T_TMP": "Referenční teplota (TMP117)",
        "T_BME": "Teplota (BME280)",
        
        # Napětí - Externí ADC
        "V_ADS_NTC": "U - termistoru (Externí ADC)",
        "V_ADS_R":   "U - rezistoru (Externí ADC)",
        
        # Napětí - Interní ESP32
        "V_ESP_NTC": "U - termistoru (Interní ESP32 ADC)",
        "V_ESP_R":   "U - rezistoru (Interní ESP32 ADC)",
        
        # PWM (zde definujeme název, i když je v řazení až na konci)
        "PWM_HEAT": "Výkon topení",
        "PWM_COOL": "Výkon chlazení",

        "Target": "Cílová teplota"
    }
    
    if key in mapping:
        return mapping[key]

    # 2. Dynamické názvy
    
    # Dallas senzory: T_DS0 -> Teplota (DS18B20 #1)
    if key.startswith("T_DS"):
        try:
            # Získáme index (0, 1...) a přičteme 1 pro hezčí číslování
            index = int(key.replace("T_DS", "")) + 1
            return f"Teplota (DS18B20 #{index})"
        except ValueError:
            return key 

    # PWM kanály obecně
    if key.startswith("PWM"):
        return f"PWM {key}"

    # 3. Fallback - odstraníme podtržítka
    return key.replace("_", " ")

def get_sensor_unit(key: str) -> str:
    """
    Vrátí jednotku pro daný typ senzoru.
    """
    # Teploty
    if key.startswith("T_"):
        return "°C"
    
    if key == "Target":
        return "°C"
    
    # Napětí (V_... nebo obsahující ADC/ESP)
    if key.startswith("V_") or "ADC" in key or "ESP" in key:
        return "mV"
        
    # PWM
    if "PWM" in key:
        return "%"
        
    return ""

def get_sensor_sort_key(key: str) -> float:
    """
    Vrátí číselnou hodnotu pro řazení (nižší číslo = dřívější pozice).
    Použijte jako key=get_sensor_sort_key v sorted().
    """
    # 1. Přesná shoda v prioritním seznamu
    if key in SENSOR_ORDER:
        return float(SENSOR_ORDER.index(key))
    
    # 2. Prefixy (pro Dallasy a jiné dynamické senzory)
    for i, prefix in enumerate(SENSOR_ORDER):
        if key.startswith(prefix):
            # Pokud je to T_DS0, chceme, aby byl za T_TMP a T_BME,
            # ale aby T_DS0 < T_DS1.
            # Proto přičteme malé číslo podle indexu senzoru.
            extra = 0.0
            try:
                # Najdeme všechna čísla v klíči
                nums = re.findall(r'\d+', key)
                if nums:
                    # Vezmeme poslední číslo a vydělíme 100
                    extra = int(nums[-1]) * 0.01
            except: pass
            
            return float(i) + extra

    # 3. Neznámé senzory a PWM nakonec
    return 999.0