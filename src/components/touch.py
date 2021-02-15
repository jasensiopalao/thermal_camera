#MIT License

#Copyright (c) 2021 Jonatan Asensio Palao

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.

from micropython import const

class Touch(object):
    """Serial interface for XPT2046 Touch Screen Controller."""

    # Command constants from XPT2046 datasheet
    GET_Y = const(0b11010000)  # X position
    GET_X = const(0b10010000)  # Y position
    GET_Z1 = const(0b10110000)  # Z1 position
    GET_Z2 = const(0b11000000)  # Z2 position
    GET_TEMP0 = const(0b10000000)  # Temperature 0
    GET_TEMP1 = const(0b11110000)  # Temperature 1
    GET_BATTERY = const(0b10100000)  # Battery monitor
    GET_AUX = const(0b11100000)  # Auxiliary input to ADC

    def __init__(self, spi, width=320, height=240):
        self.spi = spi

        #self.cs.init(self.cs.OUT, value=1)
        self.rx_buf = bytearray(3)  # Receive buffer
        self.tx_buf = bytearray(3)  # Transmit buffer

        self.adc_range = 0x0FFF

        self.width = width
        self.height = height
        self.x_raw = 0
        self.y_raw = 0
        self.x_pixel = 0
        self.y_pixel = 0

        self.x_calibration_points = [598, 3428]
        self.y_calibration_points = [598, 3728]
        self.calibrate()

    def is_valid_measurement(self):
        return (0 < self.x_raw < self.adc_range) and (0 < self.y_raw < self.adc_range)

    def calibrate(self):
        if not self.x_calibration_points or not self.y_calibration_points:
            return
        self.x_offset = min(self.x_calibration_points)
        self.y_offset = min(self.y_calibration_points)
        x_range = max(self.x_calibration_points) - self.x_offset
        y_range = max(self.y_calibration_points) - self.y_offset
        self.x_factor = self.adc_range / (x_range)
        self.y_factor = self.adc_range / (y_range)
        self.x_calibration_points.clear()
        self.y_calibration_points.clear()

    def get_pixel(self):
        x, y = self.get_raw()

        x_norm = ((x - self.x_offset) * self.x_factor ) / self.adc_range
        x_pixel = round(x_norm * self.width)
        x_pixel = max(0, min(self.width, x_pixel)-1)

        y_norm = ((y - self.y_offset) * self.y_factor ) / self.adc_range
        y_pixel = round(y_norm * self.height)
        y_pixel = max(0, min(self.height, y_pixel)-1)

        return x_pixel, y_pixel

    def get_raw(self):
        self.x_raw = self.get_adc(self.GET_X)
        self.y_raw = self.get_adc(self.GET_Y)
        return (self.x_raw, self.y_raw)

    def get_adc(self, command):
        self.tx_buf[0] = command
        self.spi.send_recv(self.tx_buf, self.rx_buf)
        adc_reading = ((((self.rx_buf[1]) << 8) | (self.rx_buf[2])))
        adc_reading = adc_reading >> 3 & self.adc_range
        return adc_reading
