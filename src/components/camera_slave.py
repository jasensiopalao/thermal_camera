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

from pyb import Pin
import sensor

class CameraSlave():

    control = None
    rx_image_width = 320
    rx_image_height = 240
    spi = None
    rx_buff = None
    tx_buff = None

    def __init__(self, spi, width, height, alloc_tx_buff=False, alloc_rx_buff=False, pin_data_ready=None, sync_cancel_condition=None):
        self.spi = spi
        if alloc_tx_buff:
            self.tx_buff = sensor.alloc_extra_fb(width, height, sensor.RGB565)
        if alloc_rx_buff:
            self.rx_buff = sensor.alloc_extra_fb(width, height, sensor.RGB565)
        self.pin_data_ready = Pin(pin_data_ready, Pin.IN)
        if not sync_cancel_condition:
            self.sync_cancel_condition = lambda: False
        else:
            self.sync_cancel_condition = sync_cancel_condition

        self.control = CameraSlaveControl()

    def sync(self, ignore_busy=False):
        if not ignore_busy:
            while self.pin_data_ready and self.pin_data_ready.value() == 1:
                if self.sync_cancel_condition():
                    return False
        if self.tx_buff is not None and self.rx_buff is not None:
            self.spi.send_recv(self.tx_buff.bytearray(), self.rx_buff.bytearray())
        elif self.tx_buff is not None:
            self.spi.send(self.tx_buff.bytearray())
        elif self.rx_buff is not None:
            self.spi.recv(self.rx_buff.bytearray())

        self.spi.send(self.control.buff)

        return True

    def increase_column_offset(self):
        self.control.column_offset += 1

    def decrease_column_offset(self):
        self.control.column_offset -= 1

    def increase_row_offset(self):
        self.control.row_offset += 1

    def decrease_row_offset(self):
        self.control.row_offset -= 1

    def increase_column_factor(self):
        self.control.column_zoom_numerator += 1
        self.control.column_zoom_denominator = 20

    def decrease_column_factor(self):
        self.control.column_zoom_numerator -= 1
        self.control.column_zoom_denominator = 20

    def increase_row_factor(self):
        self.control.row_zoom_numerator += 1
        self.control.row_zoom_denominator = 20

    def decrease_row_factor(self):
        self.control.row_zoom_numerator -= 1
        self.control.row_zoom_denominator = 20


class CameraSlaveControl():
    COLUMN_OFFSET = const(0)
    ROW_OFFSET = const(1)
    COLUMN_ZOOM_NUMERATOR = const(2)
    COLUMN_ZOOM_DENOMINATOR = const(3)
    ROW_ZOOM_NUMERATOR = const(4)
    ROW_ZOOM_DENOMINATOR = const(5)

    def __init__(self):
        self.buff = bytearray(6)

    @property
    def column_offset(self):
        return self.buff[COLUMN_OFFSET]

    @column_offset.setter
    def column_offset(self, column_offset):
        self.buff[COLUMN_OFFSET] = column_offset

    @property
    def row_offset(self):
        return self.buff[ROW_OFFSET]

    @row_offset.setter
    def row_offset(self, row_offset):
        self.buff[ROW_OFFSET] = row_offset

    @property
    def column_zoom_numerator(self):
        return self.buff[COLUMN_ZOOM_NUMERATOR]

    @column_zoom_numerator.setter
    def column_zoom_numerator(self, column_zoom_numerator):
        self.buff[COLUMN_ZOOM_NUMERATOR] = column_zoom_numerator


    @property
    def column_zoom_denominator(self):
        return self.buff[COLUMN_ZOOM_DENOMINATOR]

    @column_zoom_denominator.setter
    def column_zoom_denominator(self, column_zoom_denominator):
        self.buff[COLUMN_ZOOM_DENOMINATOR] = column_zoom_denominator

    @property
    def row_zoom_numerator(self):
        return self.buff[ROW_ZOOM_NUMERATOR]

    @row_zoom_numerator.setter
    def row_zoom_numerator(self, row_zoom_numerator):
        self.buff[ROW_ZOOM_NUMERATOR] = row_zoom_numerator

    @property
    def row_zoom_denominator(self):
        return self.buff[ROW_ZOOM_DENOMINATOR]

    @row_zoom_denominator.setter
    def row_zoom_denominator(self, row_zoom_denominator):
        self.buff[ROW_ZOOM_DENOMINATOR] = row_zoom_denominator
