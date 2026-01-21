from measurements.part_one import PartOneMeasurement

class PartTwoMeasurement(PartOneMeasurement):
    DISPLAY_NAME = "Část 2: Časová odezva"
    DURATION_S = 600.0  # 10 minut pro sledování pomalé odezvy

    def __init__(self, serial_mgr, **kwargs):
        # Vynutíme vypnutí ADC filtru, i kdyby UI poslalo cokoliv jiného.
        # Tím využijeme logiku rodiče (PartOne), ale s našimi parametry.
        kwargs['adc_filter'] = False
        
        super().__init__(serial_mgr, **kwargs)