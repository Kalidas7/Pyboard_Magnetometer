# Pyboard main.py - streams magnetometer data over USB
# Wiring: shield SCL -> X9, shield SDA -> X10
# LEDs: blue = magnetometer calibrated, green flash = point marked, red = error
# Press the USR button to record a grid point.
import time, pyb
from machine import I2C
from bno055 import BNO055

red, green, blue = pyb.LED(1), pyb.LED(2), pyb.LED(4)
sw = pyb.Switch()

try:
    imu = BNO055(I2C(1, freq=100000))
except OSError as e:
    while True:                     # keep reporting the error so the PC script shows it
        print("ERR,", e)
        red.toggle()
        time.sleep_ms(500)

prev = False
while True:
    try:
        mx, my, mz = imu.mag()
        h = imu.heading()
        cal = imu.calib()[3]
    except OSError:
        red.toggle()
        time.sleep_ms(50)
        continue
    red.off()
    print("D,%.2f,%.2f,%.2f,%.1f,%d" % (mx, my, mz, h, cal))

    if cal == 3:
        blue.on()
    else:
        blue.off()

    pressed = sw()
    if pressed and not prev:
        print("M")
        green.on()
    elif not pressed:
        green.off()
    prev = pressed

    time.sleep_ms(50)               # ~20 samples per second
