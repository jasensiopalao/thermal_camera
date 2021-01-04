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

class AuxCamera():

    SPI_BUFFER_SIZE = 20
    TX_BUTTON_SHUTTER = 0
    TX_BUTTON_TOP = 1
    TX_BUTTON_MIDDLE = 2
    TX_BUTTON_BOTTOM = 3
    TX_VOLTAGE_H = 4
    TX_VOLTAGE_L = 5
    TX_PIN_INT = 6
    TX_SPI_ERROR = SPI_BUFFER_SIZE - 1

    SPI_ERROR_UNDEFINED = 0
    SPI_ERROR_NONE = (1<<0)
    SPI_ERROR_OVERFLOW = (1<<1)
    SPI_ERROR_OVERWRITE = (1<<2)
    SPI_ERROR_OUT_OF_INDEX = (1<<3)
    SPI_ERROR_PACKAGE_COUNT = (1<<4)

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

    def initialize(self):
        self._restart = True
        self._restart_complete = False
        self.sync()

    def sync(self):
        if self._verbose:
            print("Sync_start")
        value = self.transfer()
        i = 1
        while i < 10 and (self._restart or not self._restart_complete or not value):
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

        if (self._rx_buf[self.TX_SPI_ERROR] & 1) == 0:
            if self._verbose:
                print("Error byte null")
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

import micropython
micropython.alloc_emergency_exception_buf(100)

class InterruptHandler():

    def __init__(self, pin_interrupt, callback=None, **arguments):
        self._enabled = False
        self._calling_callback = False
        self.pin = pin_interrupt
        self._callback = None
        self._callback_arguments = {}
        self._allocation_scheduled_callback = self.scheduled_callback
        self._interrupt = None
        self.interrupt_time = utime.ticks_ms()
        if callback:
            self.enable(callback, arguments)

    def enable(self, callback=None, trigger=ExtInt.IRQ_FALLING, initial_check=False, **arguments):
        if self._interrupt:
            if not self._calling_callback:
                self._interrupt.enable()
        elif callback:
            self._callback = callback
            if arguments:
                self._callback_arguments = arguments
            print("Creating interrupt on pin", self.pin, "on", trigger)
            self._interrupt = ExtInt(
                self.pin, trigger, Pin.PULL_NONE, self.interrupt_callback
            )
            print()
        else:
            raise NotImplementedError("No callback defined")

        self._enabled = True

    def disable(self):
        self._enabled = False
        self._interrupt.disable()

    def time_since_interrupt(self):
        return utime.ticks_diff(utime.ticks_ms(), self.interrupt_time)

    def interrupt_callback(self, line=None):
        self.interrupt_time = utime.ticks_ms()
        if self._calling_callback:
            return
        if self._interrupt:
            self._interrupt.disable()
        self._calling_callback = True
        micropython.schedule(self._allocation_scheduled_callback, line)

    def scheduled_callback(self, line):
        self._callback_arguments["line"] = line
        self._callback(**self._callback_arguments)
        self._calling_callback = False
        if self._interrupt and self._enabled:
            self._interrupt.enable()

class Touch(object):
    """Serial interface for XPT2046 Touch Screen Controller."""

    # Command constants from ILI9341 datasheet
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

from pyb import Pin
import time
from ustruct import pack

class TFT():
    st7735 = const(1)
    ili9341 = const(2)
    _SWRESET = const(0x01) # Software Reset
    _SLPOUT = const(0x11) # Sleep Out
    _COLMOD = const(0x3A) # Colour Mode
    _DISPON = const(0x29) # Display On
    _MADCTL = const(0x36) # Memory Data Access
    _CASET = const(0x2A) # Column Address Set
    _RASET = const(0x2B) # Row Address set
    _RAMWR = const(0x2C) #write to screen memory

    def send_spi(self,data, is_data):
        self.dc.value(is_data) #set data/command pin
        self.hspi.lock()
        self.hspi.write(data)
        self.hspi.release()

    def __init__(self, spi, pin_dc):
        self.hspi = spi
        self.dc = Pin(pin_dc, Pin.OUT_PP)
        self.dc.value(0)

    def initialize(self):

        self.send_spi(bytearray([0x01]), False)  # Software Reset
        utime.sleep_ms(10)


        lcd_hsd = (
            (0xcf, b'\x00\xc1\x30'),
            (0xed, b'\x64\x03\x12\x81'),
            (0xe8, b'\x85\x00\x7a'),
            (0xcb, b'\x39\x2c\x00\x34\x02'),
            (0xf7, b'\x20'),
            (0xea, b'\x00\x00'),
            (0xc0, b'\x21'),  # Power Control 1, VRH[5:0] b'\x23' 4.6 3.3
            (0xc1, b'\x11'),  # Power Control 2, SAP[2:0], BT[3:0]
            (0xc5, b'\x31\x3c'),  # VCM Control 1 \x3e\x28 b'\x18\x64'
            (0xc7, b'\x9f'),  # VCM Control 2 \x86
            (0x36, b'\xF8'),  # Memory Access Control
            (0x3a, b'\x55'),  # Pixel Format
            (0xb1, b'\x00\x1b'),  # FRMCTR1
            (0xb6, b'\x0a\x82\x27'),  # Display Function Control
            (0xf2, b'\x00'),  # 3Gamma Function Disable
            (0x26, b'\x01'),  # Gamma Curve Selected
            (0xe0, b'\x0f\x31\x2b\x0c\x0e\x08\x4e\xf1\x37\x07\x10\x03\x0e\x09\x00'), # Set Gamma
            (0xe1, b'\x00\x0e\x14\x03\x11\x07\x31\xc1\x48\x08\x0f\x0c\x31\x36\x0f')
        )  # Set Gamma


        lcd_tianma = (
            (0xcf, b'\x00\x83\x30'),
            (0xed, b'\x64\x03\x12\x81'),
            (0xe8, b'\x85\x01\x79'),
            (0xcb, b'\x39\x2c\x00\x34\x02'),
            (0xf7, b'\x20'),
            (0xea, b'\x00\x00'),
            (0xc0, b'\x1d'),  # Power Control 1, VRH[5:0] b'\x23' 4.6 3.3
            (0xc1, b'\x11'),  # Power Control 2, SAP[2:0], BT[3:0]
            (0xc5, b'\x33\x34'),  # VCM Control 1 \x3e\x28 b'\x18\x64'
            (0xc7, b'\xbe'),  # VCM Control 2 \x86
            (0x36, b'\xF8'),  # Memory Access Control
            (0x3a, b'\x55'),  # Pixel Format
            (0xb1, b'\x00\x1b'),  # FRMCTR1
            (0xb6, b'\x0a\x82\x27'),  # Display Function Control
            (0xf2, b'\x00'),  # 3Gamma Function Disable
            (0x26, b'\x01'),  # Gamma Curve Selected
            (0xe0, b'\x0f\x31\x2b\x0c\x0e\x08\x4e\xf1\x37\x07\x10\x03\x0e\x09\x00'), # Set Gamma
            (0xe1, b'\x00\x0e\x14\x03\x11\x07\x31\xc1\x48\x08\x0f\x0c\x31\x36\x0f')
        )  # Set Gamma

        lcd_lg = (
            (0xcb, b'\x39\x2c\x00\x34\x02'),
            (0xcf, b'\x00\xc1\x30'),
            (0xe8, b'\x85\x00\x78'),
            (0xea, b'\x00\x00'),
            (0xed, b'\x64\x03\x12\x81'),
            (0xf7, b'\x20'),
            (0xc0, b'\x1b'),  # Power Control 1, VRH[5:0] b'\x23' 4.6 3.3
            (0xc1, b'\x10'),  # Power Control 2, SAP[2:0], BT[3:0]
            (0xc5, b'\x2d\x33'),  # VCM Control 1 \x3e\x28 b'\x18\x64'
            (0xc7, b'\xcf'),  # VCM Control 2 \x86
            (0x36, b'\xF8'),  # Memory Access Control
            (0x3a, b'\x55'),  # Pixel Format
            (0xb1, b'\x00\x1b'),  # FRMCTR1
            (0xb6, b'\x0a\x82\x27'),  # Display Function Control
            (0xf2, b'\x00'),  # 3Gamma Function Disable
            (0x26, b'\x01'),  # Gamma Curve Selected
            (0xe0, b'\x0f\x31\x2b\x0c\x0e\x08\x4e\xf1\x37\x07\x10\x03\x0e\x09\x00'), # Set Gamma
            (0xe1, b'\x00\x0e\x14\x03\x11\x07\x31\xc1\x48\x08\x0f\x0c\x31\x36\x0f')
        )  # Set Gamma
        # lcd_original lcd_tuned lcd_hsd lcd_tianma lcd_lg
        for command, data in lcd_tianma:
            self.send_spi(bytearray([command]), False)
            if data is not None:
                self.send_spi(data, True)
        self.send_spi(bytearray([0x11]), False)  # Sleep out
        utime.sleep_ms(120)
        self.send_spi(bytearray([0x29]), False)  # Display ON


    def set_window(self, x, y, width, height):
        x_end=x+width-1
        y_end=y+height-1
        self.send_spi(bytearray([_CASET]),False)  # set Column addr command
        self.send_spi(pack(">HH", x, x_end), True)  # x_end
        self.send_spi(bytearray([_RASET]),False)  # set Row addr command
        self.send_spi(pack(">HH", y, y_end), True)  # y_end

    def write_to_screen(self, data):
        self.send_spi(bytearray([_RAMWR]),False)  # set to write to RAM
        self.send_spi(data, True)                 # send data

from ucollections import namedtuple

class Menu():

    Entity = namedtuple("Entity", ("text", "action"))
    NoText = None
    NoAction = None

    def __init__(self):
        self.ancestor = []
        self._structure = {}
        self.active = self._structure
        self.entity_order = []
        self.cursor = 0
        self.cursor_display_start = 0
        self.cursor_display_end = 0
        self.cursor_items = []
        self.cursor_entity = None
        self.cursor_lines = 6
        self.state = ""
        self.page = ""

    def cursor_text(self):
        if not self.cursor_entity:
            return ""
        return self.string_callback(self.cursor_entity.text)

    def cursor_action(self):
        if not self.cursor_entity:
            return ""
        return self.string_callback(self.cursor_entity.action)

    def cursor_increment(self):
        self.cursor += 1
        self.cursor_update()

    def cursor_decrement(self):
        self.cursor -= 1
        self.cursor_update()

    def cursor_update(self):
        cursor_max = len(self.active["items"]) - 1
        # Wrap around
        if self.cursor < 0:
            self.cursor = cursor_max
        if self.cursor > cursor_max:
            self.cursor = 0
        self.cursor_entity = self.cursor_items[self.cursor]
        half_lines = round(self.cursor_lines)//2
        self.cursor_display_start = max(0, self.cursor - half_lines,  )
        self.cursor_display_end = min(cursor_max, self.cursor_display_start + self.cursor_lines )

    def cursor_load(self):
        self.cursor = 0
        self.cursor_entity = None
        self.cursor_items = []
        if "items" in self.active:
            print("Load list")
            self.cursor_items = self.active["items"]
            if self.active["items"]:
                self.cursor_update()

    def state_load(self):
        if "state" in self.active:
            self.state = self.active["state"]
        if "page" in self.active:
            self.page = self.active["page"]
        else:
            self.page = ""
    @property
    def structure(self):
        return self._structure

    @structure.setter
    def structure(self, structure):
        self._structure = structure
        self.reset()

    def reset(self):
        self.ancestor.clear()
        self.active = self.structure
        self.cursor_load()
        self.state_load()

    def enter(self, submenu):
        print("From level. Title: ", self.get_title())
        self.ancestor.append(self.active)
        self.active = submenu
        print("Enter sublevel. Title: ", self.get_title())
        self.cursor_load()
        self.state_load()

    def back(self):
        if self.ancestor:
            print("Exit sublevel. Title: ", self.get_title())
            self.active = self.ancestor.pop()
        print("Back to sublevel. Title: ", self.get_title())
        self.cursor_load()
        self.state_load()

    def string_callback(self, parameters):
        if isinstance(parameters, str):
            return parameters
        if isinstance(parameters, tuple):
            function, arguments = parameters
            return function(**arguments)
        elif callable(parameters):
            return parameters()
        elif isinstance(parameters, dict):
            return self.enter(submenu=parameters)
        elif isinstance(parameters, list):
            for parameter in parameters:
                self.string_callback(parameter)

    def get_title(self):
        if "title" in self.active:
            string = self.string_callback(self.active["title"])
        else:
            string = " --- "
        if string is None:
            string = ""
        return string

    def generate_entity_line(self, entity):
        if entity.text is None:
            return ""

        string = "\n"
        if isinstance(entity.text, dict):
            raise NotImplementedError("Dictionary not allowed in text field")
        text = self.string_callback(entity.text)

        if text is None:
            return string

        if entity is self.cursor_entity:
            string += "@ "
        else:
            string += "-  "
        string += text
        return string

    def generate_text(self):
        string = self.get_title()

        for name in self.entity_order:
            if name not in self.active:
                continue
            string += self.generate_entity_line(self.active[name])

        if self.cursor_items:
            string += "\nOptions:"
            for entity in self.cursor_items[self.cursor_display_start:(self.cursor_display_end+1)]:
                string += self.generate_entity_line(entity)

        return string

    def process_action(self, name):
        if name not in self.active:
            return False
        entity = self.active[name]
        if not entity.action:
            return False
        action = entity.action
        return self.string_callback(action)

from pyb import SPI

class DynamicSPI():

    _spi = None
    _locked = None
    _hash_arguments = None
    _release_callback = None
    _release_callback_arguments = None
    _verbose = False

    def create(*args, **kwargs):
        if DynamicSPI._spi:
            DynamicSPI._spi.deinit()
            del DynamicSPI._spi
        DynamicSPI._spi = SPI(2, mode=SPI.MASTER, **kwargs)
        DynamicSPI._hash_arguments = hash(frozenset(kwargs.items()))
        return DynamicSPI._hash_arguments

    def __init__(self, pin_cs, start_delay=0, byte_delay=0, **arguments):
        self._hash_arguments = self.create(**arguments)
        self.pin_cs = Pin(pin_cs, Pin.OUT_PP)
        self.arguments = arguments
        self._allow_relock = False
        self.start_delay = start_delay
        self.byte_delay = byte_delay
        self.write = self.send

        # make sure that the CS line is high to not disturb other devices
        self.pin_cs.value(1)

    @property
    def locked(self):
        return DynamicSPI._locked is not None

    def lock(self, allow_relock=False, release_callback=None, **arguments):
        if self.locked and self._allow_relock and DynamicSPI._hash_arguments == self._hash_arguments:
            if self._verbose:
                print("Re-using")
        else:
            if self.locked:
                if release_callback:
                    if self._verbose:
                        print("SPI schedulled callback")

                    DynamicSPI._release_callback = release_callback
                    DynamicSPI._release_callback_arguments = arguments
                    return False
                else:
                    from pyb import LED
                    LED(1).on()
                    LED(2).on()
                    LED(3).on()
                    utime.sleep_ms(1000)
                    if self._verbose:
                        print("\n\nALREADY LOCKED", DynamicSPI._spi, DynamicSPI._locked)
                    raise NotImplementedError("ALREADY LOCKED")

            if DynamicSPI._hash_arguments != self._hash_arguments:
                if self._verbose:
                    print("Change to", self.arguments)
                self._hash_arguments = DynamicSPI.create(**self.arguments)

        self._allow_relock = allow_relock

        DynamicSPI._locked = self.arguments
        if self._verbose:
            print("Lock", self.arguments)
        self.pin_cs.value(0)
        utime.sleep_us(self.start_delay)
        return True

    def release(self):
        if not self.locked:
            print("It was not locked")
            raise NotImplementedError
        self._allow_relock = False
        self.pin_cs.value(1)
        release_callback = DynamicSPI._release_callback
        release_arguments = DynamicSPI._release_callback_arguments
        DynamicSPI._release_callback = None
        DynamicSPI._release_callback_arguments = None
        DynamicSPI._locked = None

        if self._verbose:
            print("Released", self.arguments)
        if release_callback:
            release_callback(**release_arguments)

    def send(self, send, **kwargs):
        auto_lock = not self.locked or self._allow_relock
        if auto_lock:
            if self._verbose:
                print("Autolock")
            self.lock()

        if self.byte_delay == 0:
            result=DynamicSPI._spi.send(send, **kwargs)
        else:
            end = len(send)
            send_mv = memoryview(send)
            for i in range(0, end):
                utime.sleep_us(self.byte_delay)
                DynamicSPI._spi.send(send_mv[i:(i+1)])
        if auto_lock:
            if self._verbose:
                print("Autorelease")
            self.release()

    def recv(self, receive, **kwargs):
        auto_lock = not self.locked or self._allow_relock
        if auto_lock:
            if self._verbose:
                print("Autolock")
            self.lock()

        if self.byte_delay == 0:
            result=DynamicSPI._spi.recv(receive, **kwargs)
        else:
            end = len(receive)
            receive_mv = memoryview(receive)
            for i in range(0, end):
                utime.sleep_us(self.byte_delay)
                DynamicSPI._spi.recv(receive_mv[i:(i+1)])
        if auto_lock:
            if self._verbose:
                print("Autorelease")
            self.release()

    def send_recv(self, send, receive, **kwargs):
        auto_lock = not self.locked or self._allow_relock
        if auto_lock:
            if self._verbose:
                print("Autolock")
            self.lock()

        if self.byte_delay == 0:
            result=DynamicSPI._spi.send_recv(send, receive, **kwargs)
        else:
            end = min(len(send), len(receive))
            send_mv = memoryview(send)
            receive_mv = memoryview(receive)
            for i in range(0, end):
                utime.sleep_us(self.byte_delay)
                DynamicSPI._spi.send_recv(send_mv[i:(i+1)], receive_mv[i:(i+1)])
        if auto_lock:
            if self._verbose:
                print("Autorelease")
            self.release()

@micropython.viper
def qvga2qvga(src: ptr16, dst: ptr16, start_step: int, step_size: int):
    columns_image = 320
    rows_image = 240

    image_size = columns_image * rows_image
    index = start_step
    while index < image_size:
        dst[index] = src[index]
        index += step_size

@micropython.viper
def qqvga2qvga(src: ptr16, dst: ptr16):
    """ Fast method to increase the resolution from QQVGA to QVGA (approx time 7ms) """
    columns_image = 160
    rows_image = 120
    image_size = columns_image * rows_image
    icolumn_screen = 0
    icolumn_screen_1 = icolumn_screen + 1
    irow_screen = 0
    irow_screen_1 = irow_screen + 1

    columns_screen = 320
    # assumption that the screen has double the lines of the image

    index_image = 0
    while index_image < image_size:
        pixel = src[index_image]
        index_image += 1

        icolumn_screen_1 = icolumn_screen + 1
        irow_screen_index = irow_screen   * columns_screen
        dst[icolumn_screen   + irow_screen_index] = pixel
        dst[icolumn_screen_1 + irow_screen_index] = pixel
        irow_screen_index = irow_screen_1   * columns_screen
        dst[icolumn_screen   + irow_screen_index] = pixel
        dst[icolumn_screen_1 + irow_screen_index] = pixel

        icolumn_screen += 2

        if icolumn_screen >= columns_screen:
            icolumn_screen = 0
            irow_screen += 2
            irow_screen_1 = irow_screen + 1

@micropython.viper
def increase_image_viper(src: ptr16, dst: ptr16, pixels: int):
    columns_image = 160
    rows_image = 120
    icolumn_image = 0
    irow_image = 0
    icolumn_screen = 0
    irow_screen = 0
    icolumn_pixel = 0
    irow_pixel = 0

    columns_screen = 320

    icolumn_screen_1 = icolumn_screen + 1
    irow_screen_1 = irow_screen + 1
    while irow_image < rows_image:
        pixel = src[icolumn_image + irow_image * columns_image]

        irow_pixel = 0
        while irow_pixel < pixels:
            icolumn_pixel = 0
            while icolumn_pixel < pixels:
                dst[icolumn_screen + icolumn_pixel + (irow_screen + irow_pixel) * columns_screen] = pixel
                icolumn_pixel += 1
            irow_pixel += 1

        icolumn_image += 1
        if icolumn_image >= columns_image:
            icolumn_image = 0
            irow_image += 1
            irow_screen = 2 * irow_image
            irow_screen_1 = irow_screen + 1
        icolumn_screen = 2 * icolumn_image

import ujson

class Settings():
    def __init__(self, file_name):
        self.file_name = file_name
        self.dict = {}

    def read(self):
        try:
            with open(self.file_name, "r") as f:
                self.dict = ujson.load(f)
            if self.dict is None:
                print("Empty file")
                self.dict = {}
        except Exception as e:
            print("Exception", e)
            with open(self.file_name, "w") as f:
                ujson.dump(self.dict, f)

        print("read:", ujson.dumps(self.dict))

    def write(self):
        print("save:", ujson.dumps(self.dict))
        with open(self.file_name, "w") as f:
            ujson.dump(self.dict, f)
