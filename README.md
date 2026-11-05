# Pyboard Magnetometer

Use a Pyboard and the Arduino 9 Axis Motion Shield (Bosch BNO055) as a magnetometer. Move it around, watch the values live and build a field map.

## Wiring

| Shield pin | Pyboard pin |
|---|---|
| 5V | V+ (VIN) |
| 3.3V | 3V3 |
| IOREF (if present) | 3V3 |
| GND | GND |
| SDA | X10 |
| SCL | X9 |

## Files

| File | Where it goes | What it does |
|---|---|---|
| `pyboard/bno055.py` | PYBFLASH drive | Driver: reads the magnetic field (µT), heading and calibration status from the BNO055 |
| `pyboard/main.py` | PYBFLASH drive | Streams data over USB at about 20 Hz. The USR button marks a grid point. Blue LED = calibrated, red LED = error |
| `pc/mag_map.py` | Your PC | Live plots, compass and field heatmap. Saves CSV logs |

## Setup

1. Copy both `pyboard/` files to the PYBFLASH drive, eject it and press RST.
2. On the PC, install the packages: `pip install pyserial matplotlib numpy`
3. Run `python pc/mag_map.py COM5 --rows 5 --cols 5 --spacing 10`, using your own port.
4. Wave the board in a figure-8 until the blue LED is on (mag cal 3/3).
5. Put the board on each grid point, facing the same way each time, and press USR (or SPACE in the plot window).

Logs are saved in the folder you run the script from: `mag_raw_<time>.csv` has every sample and `mag_points_<time>.csv` has the grid points.
