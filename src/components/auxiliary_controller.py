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

import micropython, utime
from pyb import Pin, ExtInt

class AuxiliaryController():

    SPI_BUFFER_SIZE = 20
    TX_BUTTON_SHUTTER = 0
    TX_BUTTON_TOP = 1
    TX_BUTTON_MIDDLE = 2
    TX_BUTTON_BOTTOM = 3
    TX_VOLTAGE_H = 4
    TX_VOLTAGE_L = 5
    TX_PIN_INT = 6
    TX_TICKS_0 = 7
    TX_TICKS_1 = 8
    TX_TICKS_2 = 9
    TX_TICKS_3 = 10
    TX_SPI_ERROR = SPI_BUFFER_SIZE - 1

    SPI_ERROR_UNDEFINED = 0
    SPI_ERROR_NONE = (1<<0)
    SPI_ERROR_OVERFLOW = (1<<1)
    SPI_ERROR_OVERWRITE = (1<<2)
    SPI_ERROR_OUT_OF_INDEX = (1<<3)
    SPI_ERROR_PACKAGE_COUNT = (1<<4)

    tick_to_time = (1/(32768)*2**16)

    def __init__(self, spi):
        self._verbose = False
        self._rx_buf = bytearray( [0] * (self.SPI_BUFFER_SIZE + 1))
        self._tx_buf = bytearray( [0] * (self.SPI_BUFFER_SIZE + 1))
        self._rx_mv = memoryview(self._rx_buf)
        self._tx_mv = memoryview(self._tx_buf)
        self._spi = spi
        self.package_count = 0
        self.battery_millivolts = 0
        self._restart = True
        self._restart_complete = False

    def initialize(self, timeout_ms=1000):
        self._restart = True
        self._restart_complete = False
        return self.sync(timeout_ms=timeout_ms)

    def ticks(self):
        count = (
            (self._rx_buf[self.TX_TICKS_0]) +
            (self._rx_buf[self.TX_TICKS_1] << 8) +
            (self._rx_buf[self.TX_TICKS_2] << 16) +
            (self._rx_buf[self.TX_TICKS_3] << 24)
        )
        return count

    def time(self):
        return self.tick_to_time * self.ticks()

    def sync(self, timeout_ms=1000):
        start_time = utime.ticks_ms()
        if self._verbose:
            print("Sync_start")
        value = self.transfer()
        i = 1
        while (utime.ticks_diff(utime.ticks_ms(), start_time) < timeout_ms) and (self._restart or not self._restart_complete or not value):
            value = self.transfer()
            i += 1
        if self._verbose:
            print("sync end ", value, i)
        return value

    def prepare_next_package(self):
        self._tx_buf[self.SPI_BUFFER_SIZE] += 1
        if self._tx_buf[self.SPI_BUFFER_SIZE] >= 254:  # PIC would try to ++
            self._tx_buf[self.SPI_BUFFER_SIZE] = 0
        if self._restart:
            self._restart = False
            print("Restarting count")
            self._tx_buf[self.SPI_BUFFER_SIZE] = 0
        else:
            if self._verbose:
                print("Next package", self._tx_buf[self.SPI_BUFFER_SIZE])
        return self._tx_buf[self.SPI_BUFFER_SIZE]

    def check_package_validity(self):
        if self._tx_buf[self.SPI_BUFFER_SIZE] == 0:
            return True
        return self._tx_buf[self.SPI_BUFFER_SIZE] == self._rx_buf[self.SPI_BUFFER_SIZE]

    def number_package_received(self):
        return self._rx_buf[self.SPI_BUFFER_SIZE]

    def transfer(self):
        self._spi.lock()
        try:

            self.prepare_next_package()
            i = self.size

            self._spi.send_recv(self._tx_mv[i:(i+1)], self._rx_mv[i:(i+1)])

            if not self.check_package_validity():
                self._restart = True
                self._restart_complete = False
                if not self._verbose:
                    return False

            self._spi.send_recv(self._tx_mv[0:self.size], self._rx_mv[0:self.size])

        except Exception as e:
            print(e)
            raise
        finally:
            self._spi.release()

        self.battery_millivolts = int(
            (self._rx_buf[self.TX_VOLTAGE_H] << 8) | (self._rx_buf[self.TX_VOLTAGE_L])
        )

        if self._verbose:
            self.print_data()

        if not self.check_package_validity() and self._verbose:
            print("exit", self._tx_buf[self.size], self._rx_buf[self.size])
            return False

        if self._rx_buf[self.TX_SPI_ERROR] != 1:
            print("Error byte: ", self._rx_buf[self.TX_SPI_ERROR])
            return False

        if self._rx_buf[self.SPI_BUFFER_SIZE] == 1:
            if self._verbose:
                print("Restart complete")
            self._restart_complete = True
        return True

    def print_data(self):
        print(
            '[{}]'.format(self._tx_buf[self.SPI_BUFFER_SIZE]),
            ' '.join('{:02x}'.format(x) for x in self._rx_buf),
            "battery", self.battery_millivolts,
            "time", self.time(),
            "Errors {0:b}".format(self._rx_buf[self.TX_SPI_ERROR]),
        )

    @property
    def size(self):
        return self.SPI_BUFFER_SIZE

    @property
    def button_shutter(self):
        return self._rx_buf[self.TX_BUTTON_SHUTTER]

    @property
    def button_top(self):
        return self._rx_buf[self.TX_BUTTON_TOP]

    @property
    def button_middle(self):
        return self._rx_buf[self.TX_BUTTON_MIDDLE]

    @property
    def button_bottom(self):
        return self._rx_buf[self.TX_BUTTON_BOTTOM]

    @property
    def active_flags(self):
        return self._rx_buf[self.TX_PIN_INT]
