from typing import Dict, List

from PySide6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg


class FixedAxis(pg.AxisItem):
    """
    Spodní osa, která vždy zobrazuje 0 a max_time.
    """
    def __init__(self, orientation, max_time: float, parent=None):
        super().__init__(orientation, parent)
        self._max_time = max_time

    def set_max_time(self, max_time: float):
        self._max_time = max_time
        self.picture = None
        self.update()

    def tickValues(self, minVal, maxVal, size):
        """
        Vygeneruje ticky tak, aby obsahovaly 0 a _max_time.
        """
        max_t = max(self._max_time, 0.0)
        if max_t <= 0:
            return []

        # krok tak, aby bylo rozumně málo popisků (<=6)
        candidates = [0.5, 1, 2, 5, 10, 20, 30, 60]
        step = max_t
        for c in candidates:
            if max_t / c <= 6:
                step = c
                break

        ticks = []
        x = 0.0
        while x < max_t:
            ticks.append(x)
            x += step

        if not ticks or abs(ticks[-1] - max_t) > 1e-6:
            ticks.append(max_t)

        return [(step, ticks)]

    def tickStrings(self, values, scale, spacing):
        labels = []
        for v in values:
            if abs(v - round(v)) < 1e-6:
                labels.append(str(int(round(v))))
            else:
                labels.append(f"{v:.1f}")
        return labels


class RealtimePlotWidget(QWidget):
    """
    Realtime graf:
      - X osa = čas [s] 0 .. time_window_s (pevně, podle měření)
      - více křivek (senzory) s odlišenými barvami
      - legenda (jedna položka pro každý senzor)
      - Y osa dynamicky: min(data) - 2 .. max(data) + 2
    """

    def __init__(self, time_window_s: float, parent=None):
        super().__init__(parent)

        self._time_window = time_window_s
        self._curves: Dict[str, pg.PlotDataItem] = {}
        self._data_x: Dict[str, List[float]] = {}
        self._data_y: Dict[str, List[float]] = {}

        layout = QVBoxLayout(self)

        # vlastní spodní osa, aby 0 a max byly vždy vidět
        self._bottom_axis = FixedAxis("bottom", max_time=self._time_window)
        self._plot = pg.PlotWidget(axisItems={"bottom": self._bottom_axis})

        self._plot.showGrid(x=True, y=True)
        self._plot.setLabel("bottom", "Čas", units="s")
        self._plot.setLabel("left", "Teplota", units="°C")

        # X pevně 0..time_window
        self._plot.setXRange(0, self._time_window)
        self._plot.setLimits(xMin=0, xMax=self._time_window)
        self._plot.enableAutoRange(x=False, y=True)

        # Legenda – addLegend se postará sám o křivky s name=...
        self._legend = self._plot.addLegend(offset=(10, 10))

        layout.addWidget(self._plot)

    # ---------- veřejné API ----------

    def clear(self):
        # odstranit staré křivky
        for curve in self._curves.values():
            self._plot.removeItem(curve)

        self._curves.clear()
        self._data_x.clear()
        self._data_y.clear()

        # vyčistit legendu, ale nevytvářet novou
        if self._legend is not None:
            self._legend.clear()

        # obnovit osu X
        self._plot.setXRange(0, self._time_window)
        self._plot.setLimits(xMin=0, xMax=self._time_window)
        self._bottom_axis.set_max_time(self._time_window)

    def add_point(self, t_s: float, values: Dict[str, float]):
        """
        Přidá body pro daný čas a sadu senzorů.
        values např.: {"T_BME": 24.1, "T_DS0": 23.7}
        """
        for sensor_key, val in values.items():
            if sensor_key not in self._curves:
                pretty = self._pretty_name(sensor_key)
                color = self._assign_color(len(self._curves))

                # DŮLEŽITÉ:
                # name=pretty → automaticky se přidá JEDNOU do legendy
                curve = self._plot.plot(
                    [], [],
                    pen=pg.mkPen(color=color, width=2),
                    symbol="x",
                    symbolSize=10,
                    symbolBrush=color,
                    name=pretty,
                )

                self._curves[sensor_key] = curve
                self._data_x[sensor_key] = []
                self._data_y[sensor_key] = []

            self._data_x[sensor_key].append(t_s)
            self._data_y[sensor_key].append(val)

        # ořez podle časového okna
        for sensor_key, curve in self._curves.items():
            xs = self._data_x[sensor_key]
            ys = self._data_y[sensor_key]
            if not xs:
                continue

            cutoff = max(0.0, xs[-1] - self._time_window)
            while xs and xs[0] < cutoff:
                xs.pop(0)
                ys.pop(0)

            curve.setData(xs, ys)

        # dynamická Y osa ±2 °C
        all_vals = [v for series in self._data_y.values() for v in series]
        if all_vals:
            y_min = min(all_vals) - 2.0
            y_max = max(all_vals) + 2.0
            if y_min == y_max:
                y_min -= 1.0
                y_max += 1.0
            self._plot.enableAutoRange(y=False)
            self._plot.setYRange(y_min, y_max, padding=0)

    def set_time_window(self, seconds: float):
        """
        Nastaví délku časové osy podle doby měření.
        """
        if seconds <= 0:
            return

        self._time_window = seconds
        self._plot.setXRange(0, self._time_window)
        self._plot.setLimits(xMin=0, xMax=self._time_window)
        self._bottom_axis.set_max_time(self._time_window)

    # ---------- interní pomocné metody ----------

    def _pretty_name(self, key: str) -> str:
        if key in ("T_BME", "T_BME280"):
            return "BME280"

        if key.startswith("T_DS"):
            idx_str = key[4:]
            if idx_str.isdigit():
                return f"DS18B20 #{int(idx_str) + 1}"
            return "DS18B20"

        return key

    def _assign_color(self, index: int):
        # stabilní barvy z pyqtgraph palety
        return pg.intColor(index, hues=8, values=255, maxValue=255)
