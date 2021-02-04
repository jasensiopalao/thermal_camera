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

# SPI with the Openmv with Thermal camera as the master device and the OpenMV Cam as the slave.
#
# OpenMV Cam Master Out Slave In (P0)
# OpenMV Cam Master In Slave Out (P1)
# OpenMV Cam Serial Clock        (P2)
# OpenMV Cam Slave Select        (P3)

from pyb import Pin, SPI

pin_busy = Pin.board.P7
pin_spi_ss = Pin.board.P3
pins_spi_bus = [
    Pin.board.P0,
    Pin.board.P1,
    Pin.board.P2,
]
def set_pins_to_spi_af(pins):
    for pin in pins:
        Pin(pin, Pin.AF_PP, af=Pin.AF5_SPI2)

def set_pins_to_high_impedance(pins):
    for pin in pins:
        Pin(pin, Pin.AF_PP, af=Pin.AF5_SPI2)

input_spi_ss = Pin(pin_spi_ss, Pin.IN)
output_busy = Pin(pin_busy, Pin.OUT_PP)
output_busy.value(1)

def setup_spi():
    return SPI(2, SPI.SLAVE, polarity=0, phase=0)
spi = setup_spi()
set_pins_to_high_impedance(pins_spi_bus)

from camera_slave_control import CameraSlaveControl
import gc

from pyb import LED, USB_VCP
import sensor, image, utime, time

sensor.reset()                      # Reset and initialize the sensor.
sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.QVGA)   # Set frame size to QVGA (320x240)
sensor.skip_frames(time = 2000)     # Wait for settings take effect.
clock = time.clock()                # Create a clock object to track the FPS.

red_led = LED(1)
red_led.off()
green_led = LED(2)
green_led.off()
blue_led = LED(3)
blue_led.off()

class DataTX():
    img_width = 320
    img_height = 240
    sent = False
    buff = None

dataTX = DataTX()
dataRX = DataTX()
dataTX.buff = sensor.alloc_extra_fb(DataTX.img_width, DataTX.img_height, sensor.RGB565)
dataRX.buff = sensor.alloc_extra_fb(DataTX.img_width, DataTX.img_height, sensor.RGB565)

usb = USB_VCP()

blue_led.on()
spi_error = False

@micropython.viper
def qvgafov2qvga(
    src: ptr16,
    dst: ptr16,
    column_offset: int,
    row_offset: int,
    column_zoom_numerator: int,
    column_zoom_denominator: int,
    row_zoom_numerator: int,
    row_zoom_denominator: int,
):
    """ Fast method to expand the FOI to the full dst frame buffer """
    columns = 320
    rows = 240
    image_size = columns * rows

    icolumn_src = column_offset
    irow_src = row_offset
    icolumn_dst = 0
    irow_dst = 0

    # assumption that the screen has double the lines of the image

    # assume column_zoom_denominator < column_zoom_numerator
    column_fraction_copy = column_zoom_numerator - column_zoom_denominator
    row_fraction_copy = row_zoom_numerator - row_zoom_denominator

    icolumn_action = 0
    irow_action = 0
    index_src = icolumn_src + irow_src * columns

    copies_per_column_copy = column_zoom_numerator // column_zoom_denominator
    columns_to_copy = 0  # Per block columns to be copied
    columns_copied = 0
    column_copied = 0

    copies_per_row_copy = row_zoom_numerator // row_zoom_numerator
    rows_to_copy = 0
    rows_copied = 0
    row_copied = 0
    #print(
        #"column_fraction_copy", column_fraction_copy, "copies_per_column_copy", copies_per_column_copy,
        #"row_fraction_copy", row_fraction_copy, "copies_per_row_copy", copies_per_row_copy
    #)
    while True:

        index_src = icolumn_src + irow_src * columns
        pixel = src[index_src]
        dst[icolumn_dst   + irow_dst   * columns] = pixel
        #print(icolumn_src, irow_src, icolumn_dst, irow_dst, "action", icolumn_action, irow_action, "copy", columns_to_copy, rows_to_copy)
        if columns_to_copy == 0 and column_copied != icolumn_src and columns_copied < column_fraction_copy:
            columns_to_copy = copies_per_column_copy

        if columns_to_copy > 0:
            columns_to_copy -= 1
            column_copied = icolumn_src
            columns_copied += 1
        else:
            icolumn_src += 1

        icolumn_action += 1
        if icolumn_action >= column_zoom_numerator:
            icolumn_action = 0
            columns_copied = 0

        icolumn_dst += 1
        if icolumn_dst >= columns or icolumn_src >= columns:
            icolumn_dst = 0
            icolumn_src = column_offset
            icolumn_action = 0
            columns_copied = 0

            #print(icolumn_src, irow_src, icolumn_dst, irow_dst, "action", icolumn_action, irow_action, "copy", columns_to_copy, rows_to_copy)

            if rows_to_copy == 0 and row_copied != irow_src and rows_copied < row_fraction_copy:
                rows_to_copy = copies_per_row_copy

            if rows_to_copy > 0:
                rows_to_copy -= 1
                row_copied = irow_src
                rows_copied += 1
            else:
                irow_src += 1

            irow_action += 1
            if irow_action >= row_zoom_numerator:
                irow_action = 0
                rows_copied = 0

            irow_dst += 1
            if irow_dst >= rows or irow_src >= rows:
                return


debug_image = False

control = CameraSlaveControl()
control.column_offset = 10
control.row_offset = 10
control.column_zoom_numerator = 22
control.column_zoom_denominator = 20
control.row_zoom_numerator = 22
control.row_zoom_denominator = 20

while(True):
    clock.tick()                    # Update the FPS clock.
    img = sensor.snapshot()         # Take a picture and return the image.
    if debug_image:
        utime.sleep_ms(3000)
    qvgafov2qvga(
        img,
        dataTX.buff,
        control.column_offset, # column_offset
        control.row_offset, # row_offset
        control.column_zoom_numerator,  # column_zoom_numerator
        control.column_zoom_denominator,  # column_zoom_denominator
        control.row_zoom_numerator,  # row_zoom_numerator
        control.row_zoom_denominator,  # row_zoom_denominator
    )
    if debug_image:
        dataTX.buff.draw_string(0,0,"cropped", color=127)
        if (usb.isconnected()):
            print(dataTX.buff.compressed_for_ide(), end="")
        utime.sleep_ms(3000)
        continue

    if (input_spi_ss.value() == 1):
        output_busy.value(0)
    start_time = utime.ticks_ms()
    refresh_image = False
    while (input_spi_ss.value() == 1):
        if utime.ticks_diff(utime.ticks_ms(), start_time) > 500:
            green_led.off()
            blue_led.off()
            if utime.ticks_diff(utime.ticks_ms(), start_time) > 1000:
                refresh_image = True
                break


    output_busy.value(1)
    if refresh_image:
        print("Refresh cached image during idle mode")
        continue

    set_pins_to_spi_af(pins_spi_bus)
    if not spi_error:
        green_led.on()
        blue_led.on()
    else:
        spi = setup_spi()

    try:
        spi.send_recv(dataTX.buff.bytearray(), dataRX.buff.bytearray(), timeout=5000)
        spi.recv(control.buff, timeout=1000)
        red_led.off()
    except OSError as err:
        spi_error = True
        red_led.on()
        green_led.off()
        blue_led.off()
        print("exception {}".format(err))

    set_pins_to_high_impedance(pins_spi_bus)
    while (input_spi_ss.value() == 0):
        pass

    print(clock.fps())              # Note: OpenMV Cam runs about half as fast when connected
                                    # to the IDE. The FPS should increase once disconnected.


