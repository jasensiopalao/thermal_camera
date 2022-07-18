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

import utime
from pyb import Pin
import time
from ustruct import pack
import sensor
from uctypes import bytearray_at

from utils.image import pixel2pixel

class Screen():
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

    def __init__(self, spi, alloc_screen_buff, width, height, pin_dc, framebuffer_swap_endianness=False, fast_byteswap=False):

        if alloc_screen_buff:
            self.screen_buff = sensor.alloc_extra_fb(width, height, sensor.RGB565)
        self.width = width
        self.height = height

        self.hspi = spi
        self.dc = Pin(pin_dc, Pin.OUT_PP)
        self.dc.value(0)
        self.framebuffer_swap_endianness = framebuffer_swap_endianness
        self.fast_byteswap = fast_byteswap

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
            (0x3a, b'\x55'),  # Pixel Format 55
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
        self.dc.value(True) #set data/command pin
        self.hspi.lock()
        if self.framebuffer_swap_endianness:
            if self.fast_byteswap:
                # Sacrify one pixel and avoid needing a byte swap
                # Make the count in the screen driver already increase by one
                #self.hspi.send(bytearray([0]))  # Displayed as black
                m = memoryview(data)
                self.hspi.send(bytearray([0]*19))
                #self.hspi.send(m[0:19])  # The ptr8 in the ST will already swap the bytes while accessing it
                self.hspi.send(m[20:])  # The ptr8 in the ST will already swap the bytes while accessing it
            else:
                pixel2pixel(data)
                self.hspi.send(data)
        else:
            self.hspi.send(data)
        self.hspi.release()
