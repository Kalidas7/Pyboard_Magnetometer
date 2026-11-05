# Minimal BNO055 driver for MicroPython (Pyboard + Arduino 9 Axis Motion Shield)
import time, struct


class BNO055:
    def __init__(self, i2c, addr=None):
        self.i2c = i2c
        if addr is None:
            found = i2c.scan()
            for a in (0x28, 0x29):
                if a in found:
                    addr = a
                    break
            else:
                raise OSError("BNO055 not found. I2C scan = %s" % [hex(x) for x in found])
        self.addr = addr
        self._init()

    def _w(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg, bytes([val]))

    def _r(self, reg, n=1):
        return self.i2c.readfrom_mem(self.addr, reg, n)

    def _chip_id(self):
        try:
            return self._r(0x00)[0]
        except OSError:
            return -1

    def _wait_ready(self, ms=1500):
        t0 = time.ticks_ms()
        while self._chip_id() != 0xA0:
            if time.ticks_diff(time.ticks_ms(), t0) > ms:
                raise OSError("BNO055 not responding (chip id)")
            time.sleep_ms(10)

    def _init(self):
        self._wait_ready()
        self._w(0x3D, 0x00); time.sleep_ms(25)   # CONFIG mode
        self._w(0x3F, 0x20); time.sleep_ms(700)  # reset
        self._wait_ready()
        self._w(0x3E, 0x00)                      # normal power
        self._w(0x07, 0x00)                      # register page 0
        self._w(0x3F, 0x00); time.sleep_ms(10)
        self._w(0x3D, 0x0C); time.sleep_ms(30)   # NDOF fusion mode (mag auto-calibrates)

    def mag(self):
        """Magnetic field (x, y, z) in microtesla."""
        x, y, z = struct.unpack('<hhh', self._r(0x0E, 6))
        return x / 16, y / 16, z / 16

    def heading(self):
        """Compass heading in degrees (0-360)."""
        return struct.unpack('<h', self._r(0x1A, 2))[0] / 16

    def calib(self):
        """Calibration status (sys, gyro, accel, mag), each 0..3 (3 = fully calibrated)."""
        c = self._r(0x35)[0]
        return (c >> 6) & 3, (c >> 4) & 3, (c >> 2) & 3, c & 3
