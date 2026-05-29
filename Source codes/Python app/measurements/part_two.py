from measurements.part_one import PartOneMeasurement

class PartTwoMeasurement(PartOneMeasurement):
    DISPLAY_NAME = "Část 2: Časová odezva"
    DURATION_S = 600.0  

    def __init__(self, serial_mgr, **kwargs):
        # Programmatically disable hardware ADC filters for raw response analysis
        # Inherits operational logic from PartOne while restricting configuration parameters.
        kwargs['adc_filter'] = False
        
        super().__init__(serial_mgr, **kwargs)