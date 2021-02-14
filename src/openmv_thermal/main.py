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

camera_version = "1.8"


from utils.interrupt_handler import InterruptHandler
from utils.menu import Menu
from utils.settings import Settings
from utils.dynamic_spi import DynamicSPI
from utils.image import qvga2qvga, qqvga2qvga, qqgrey2qvga
from utils.rtc_time import time_datetime2string

from components.thermal import Thermal
from components.touch import Touch
from components.screen import Screen
from components.auxiliary_controller import AuxiliaryController
from components.camera_slave import CameraSlave

from helpers.user_settings import (
    load_control_settings,
    load_thermal_settings,
    load_camera_slave_calibration_settings,
    load_touch_calibration_settings,
)

from helpers.load_menu import load_menu
from helpers.sync_time import sync_time

from helpers.control import Control, CameraState, CameraPreview

import pyb

import gc
import utime, time
from time import sleep
import machine
from sys import exit

import sensor, image, uos
from pyb import LED, disable_irq

from pyb import Pin, ExtInt
import micropython

usb = pyb.USB_VCP()

class Logger():
    creation_time = 0
    def __init__(self):
        self.creation_time = utime.ticks_ms()
        self.last_print_time = utime.ticks_ms()
        print("Python heap size", gc.mem_alloc()+gc.mem_free())
        # machine.info(1)  # GC memory layout;
    def info(self, *args):
        self.last_print_time = utime.ticks_ms()
        boot_time = utime.ticks_diff(self.last_print_time, self.creation_time)
        print(utime.localtime(utime.time()), "Alloc", gc.mem_alloc(), "Free", gc.mem_free() ,": ", *args)

logger = Logger()
logger.info("Boot")

###################################################################################################
# FRAMEWORK   CODE            #####################################################################
###################################################################################################

def main():

    utime.sleep_ms(1000)
    ##############################################################################
    # CREATE COMPONENTS
    logger.info("uname", uos.uname())

    led_red = LED(1) # red led
    led_red.off()


    screen = Screen(
        spi=DynamicSPI(
            baudrate=54000000, pin_cs=Pin.board.P3, polarity=0, phase=0,
        ),
        alloc_screen_buff=True,
        width=320,
        height=240,
        pin_dc=Pin.board.P9,
        framebuffer_swap_endianness=True,
        fast_byteswap=False,
    )

    control = Control(logger=logger)
    thermal = Thermal(logger=logger)

    # SPI at 40000000 or start_delay=100 would lead to data corruption
    camera_slave = CameraSlave(
        spi=DynamicSPI(
            baudrate=30000000, pin_cs=Pin.board.P4, polarity=0, phase=0, start_delay=500,
        ),
        pin_data_ready=Pin.board.P5,
        width=screen.width,
        height=screen.height,
        alloc_rx_buff=True
    )

    touch = Touch(
        spi=DynamicSPI(
            baudrate=2000000, pin_cs=Pin.board.P7, polarity=0, phase=0, start_delay=10, byte_delay=10,
        )
    )

    auxiliary_controller = AuxiliaryController(
        spi=DynamicSPI(
            baudrate=2500000, pin_cs=Pin.board.P6, polarity=1, phase=0, start_delay=10, byte_delay=100,
        )
    )


    menu = Menu()
    settings = Settings("camera.json")
    time_settings = Settings("time.json")

    input_handler = InterruptHandler(
        pin_interrupt=Pin.board.P8, trigger=ExtInt.IRQ_FALLING
    )

    components = {
        "logger": logger,
        "auxiliary_controller": auxiliary_controller,
        "touch": touch,
        "control": control,
        "thermal": thermal,
        "menu": menu,
        "screen": screen,
        "settings": settings,
        "time_settings": time_settings,
        "input_handler": input_handler,
        "camera_slave": camera_slave,
    }

    #testing_bug3(**components)
    ###########################
    DynamicSPI._verbose = False
    auxiliary_controller._verbose = False

    ##############################################################################
    # INITIALIZE COMPONENTS

    logger.info("Loading menu...")
    load_menu(components)

    logger.info("Initializing screen...")
    screen.initialize()
    screen.set_window(0, 0, screen.width, screen.height)

    screen.screen_buff.draw_rectangle(0, 0, screen.width, screen.height, color=(30,30,30), fill=True)
    screen.write_to_screen(screen.screen_buff)
    utime.sleep_ms(100)
    display_intro = False
    try:
        image.Image(control.startup_img_name, copy_to_fb=screen.screen_buff)
        display_intro = True
    except Exception as e:
        logger.info("Could not display startup image {}".format(e))

    if display_intro:
        logger.info("Displaying intro")
        screen.screen_buff.draw_rectangle(0, 0, screen.width, 20, color=(30,30,30), fill=True)
        screen.screen_buff.draw_string(10,0, """Shutter Button is "Back" button""", color=(0,200,30), scale=2.0, mono_space=False)

        screen.screen_buff.draw_rectangle(0, round(screen.height*3/4), screen.width, round(screen.height*4/4), color=(30,30,30), fill=True)
        startup_text = "by JONATAN ASENSIO PALAO. v" + camera_version
        screen.screen_buff.draw_string(round(screen.width/11), round(screen.height*3.1/4), startup_text, color=(0,200,30), scale=2.0, mono_space=False)

        screen.screen_buff.draw_string(round(screen.width/11), round(screen.height*3.6/4), "LOADING... WAIT", color=(200,0,0), scale=2.0, mono_space=False)

        screen.write_to_screen(screen.screen_buff)

    logger.info("Initializing auxiliar processor...")
    if auxiliary_controller.initialize(timeout_ms=5000):
        logger.info("Initializtion complete. Last package number: ", auxiliary_controller.number_package_received())
    else:
        screen.screen_buff.draw_rectangle(0, 0, screen.width, screen.height, color=(30,30,30), fill=True)
        screen.screen_buff.draw_string(10,0, "Aux processor error", color=(255,0,0), scale=2.0, mono_space=False)
        screen.write_to_screen(screen.screen_buff)
        utime.sleep_ms(10000)
    control.battery_millivolts = auxiliary_controller.battery_millivolts
    absolute_seconds = auxiliary_controller.time()
    logger.info("Battery:", control.battery_millivolts, "mV", " Absolute seconds:", absolute_seconds)


    logger.info("Initializing time...")
    sync_time(logger, screen, time_settings, auxiliary_controller)

    logger.info("Loading settings...")

    load_camera_slave_calibration_settings(settings=settings, camera_slave=camera_slave)
    load_touch_calibration_settings(settings=settings, touch=touch)
    load_control_settings(settings=settings, control=control)
    load_thermal_settings(settings=settings, thermal=thermal)

    logger.info("Initializing thermal camera...")
    thermal.initialize()

    logger.info("Enabling input interrupts...")
    input_handler.enable(
        callback=input_interrupt, **components
    )


    logger.info("Running main loop...")
    loop(**components)


###################################################################################################
# APPLICATION CODE            #####################################################################
###################################################################################################

def input_interrupt(auxiliary_controller, touch, control, menu, screen, input_handler, **kwargs):
    #spi = auxiliary_controller._spi
    spi = touch.spi
    if not spi.lock(allow_relock=True, release_callback=input_handler.interrupt_callback, line="SPI"):
        #logger.info("SPI IN USE...")
        return

    x, y = touch.get_pixel() # get_raw
    if touch.is_valid_measurement():
        if "TOUCH_CALIBRATION" in menu.page:
            touch.x_calibration_points.append(touch.x_raw)
            touch.y_calibration_points.append(touch.y_raw)

        control.x = x
        control.y = y

        # return

    auxiliary_controller.sync()
    control.battery_millivolts = auxiliary_controller.battery_millivolts
    control.button_shutter = auxiliary_controller.button_shutter
    control.button_top = auxiliary_controller.button_top
    control.button_middle = auxiliary_controller.button_middle
    control.button_bottom = auxiliary_controller.button_bottom

    if control.button_shutter:
        menu.process_action("shutter")
    if control.button_top:
        menu.process_action("top")
    if control.button_middle:
        menu.process_action("middle")
    if control.button_bottom:
        menu.process_action("bottom")

    if auxiliary_controller.active_flags:
        logger.info("START ------------ after spi release:", kwargs)
        auxiliary_controller.print_data()
        logger.info(" END -------------")

def loop(control, thermal, screen, menu, input_handler, camera_slave, **kwargs):

    led_green = LED(2) # red led
    led_green.off()

    usb = pyb.USB_VCP()
    running_from_ide = usb.isconnected()


    def camera_slave_sync_cancel_condition():
        if control.preview is not CameraPreview.VISIBLE or menu.state is not CameraState.PREVIEW:
            logger.info("Cancel camera slave sync")
            return True
        return False

    camera_slave.sync_cancel_condition = camera_slave_sync_cancel_condition

    state = None
    camera_preview = None
    camera_playback_img_name = ""
    previous_text = ""
    screen_refresh_needed = True
    state_ticks_ms = utime.ticks_ms()

    menu.process_action("middle")
    while True:
        changed_state = state is not menu.state
        state = menu.state

        changed_preview = camera_preview is not control.preview
        camera_preview = control.preview

        # -----------------------------------------------------------------------------------------
        # INITIALIZATIONS
        if changed_state:
            state_ticks_ms = utime.ticks_ms()
            logger.info("Processing state change to ", menu.state)
            if menu.state is CameraState.PREVIEW:
                control.fps_reset()
            if menu.state is CameraState.PLAYBACK or menu.state is CameraState.POSTVIEW:
                #control.set_normal_resolution()
                control.update_playback_img_name(go_to_last=True)
                camera_playback_img_name = ""

        if changed_preview:
            control.fps_reset()
            logger.info("Processing preview change to ", control.preview)

        # -----------------------------------------------------------------------------------------
        # RUN TIME

        if state is CameraState.PREVIEW:
            control.fps_tick()
            screen_refresh_needed = True
            text = "\n" + menu.generate_text()

            if camera_preview is CameraPreview.THERMAL or camera_preview is CameraPreview.THERMAL_ANALYSIS or camera_preview is CameraPreview.THERMAL_GREY or camera_preview is CameraPreview.MIX:

                thermal.get_spotmeter_values()
                def map_g_to_temp(g):
                    return ((g * (thermal.temperature_max - thermal.temperature_min)) / 255.0) + thermal.temperature_min

                img = sensor.snapshot()
                img_touch_x = max(0,min(sensor.width() - 1, round(control.x * sensor.width()/screen.width) ))
                img_touch_y = max(0,min(sensor.height() - 1, round(control.y * sensor.height()/screen.height) ))
                pixel = "{:.2f}".format(map_g_to_temp(img.get_pixel(img_touch_x, img_touch_y)))

                if camera_preview is CameraPreview.THERMAL_GREY:
                    img.to_rgb565()
                elif camera_preview is CameraPreview.THERMAL or camera_preview is CameraPreview.MIX:
                    img.to_rainbow(color_palette=sensor.PALETTE_IRONBOW) # color it
                elif camera_preview is CameraPreview.THERMAL_ANALYSIS:
                    # Color tracking concept from lepton_object_temp_color_1.py in the OpenMV examples
                    # Color Tracking Thresholds (Grayscale Min, Grayscale Max)
                    threshold_list = [(200, 255)]

                    blob_stats = []
                    blobs = img.find_blobs(threshold_list, pixels_threshold=200, area_threshold=200, merge=True)
                    # Collect stats into a list of tuples
                    for blob in blobs:
                        blob_stats.append((blob.x(), blob.y(), map_g_to_temp(img.get_statistics(thresholds=threshold_list,
                                                                                                roi=blob.rect()).mean())))
                    img.to_rainbow(color_palette=sensor.PALETTE_IRONBOW) # color it
                    # Draw stuff on the colored image
                    for blob in blobs:
                        img.draw_rectangle(blob.rect())
                        img.draw_cross(blob.cx(), blob.cy())
                    for blob_stat in blob_stats:
                        img.draw_string(blob_stat[0], blob_stat[1] - 10, "%.2f C" % blob_stat[2], mono_space=False)

                qqvga2qvga(sensor.get_fb(), screen.screen_buff)

            if camera_preview is CameraPreview.VISIBLE or camera_preview is CameraPreview.MIX:
                input_handler.disable()
                sync_success = camera_slave.sync()
                input_handler.enable()
                if not sync_success:
                    logger.info("Failed sync")
                    screen.screen_buff.fill(c=(10,10,10))
                    screen.screen_buff.draw_string(screen.width//2, screen.height//2, "ERROR", c=(255,0,0))

                if camera_preview is CameraPreview.VISIBLE:
                    qvga2qvga(camera_slave.rx_buff, screen.screen_buff, 0, 1)
                    pixel = screen.screen_buff.get_pixel(control.x, control.y)
                elif camera_preview is CameraPreview.MIX:
                    qvga2qvga(camera_slave.rx_buff, screen.screen_buff, 0, 2)

            if menu.page != "ROOT" or control.always_pixel_pointer:
                screen.screen_buff.draw_rectangle(control.x-5, control.y-5, 10, 10, color=(255,0,255), thickness=1, fill=True)
                if menu.state is CameraState.PREVIEW:
                    text_y_offset = 50 if control.y < screen.height//2 else -50
                    screen.screen_buff.draw_string(control.x - 20, control.y + text_y_offset, "{}".format(pixel))

        if state is CameraState.PLAYBACK or state is CameraState.POSTVIEW:
            screen_refresh_needed = False

            if menu.page == "ANALYSIS":
                screen_refresh_needed = True

            text = menu.generate_text()
            if  previous_text != text:
                screen_refresh_needed = True

            if not control.playback_img_name:
                logger.info("No image to be loaded")
                menu.back()
                continue
            elif control.playback_img_name != camera_playback_img_name or screen_refresh_needed:
                camera_playback_img_name = control.playback_img_name
                logger.info("Displaying image...", control.playback_img_name, " and text ", text)
                try:
                    img = image.Image(control.playback_img_name, copy_to_fb=True)
                    qvga2qvga(sensor.get_fb(), screen.screen_buff, 0, 1)

                    if control.to_save_fb_as_startup:
                        control.save_fb_as_startup(screen.screen_buff)
                    img.to_grayscale()
                    try:
                        file_name = control.playback_img_name.split("/")[-1].split(".")[0]
                        file_name = file_name.split("_")
                        thermal.temperature_min = float(file_name[1]) / 100
                        thermal.temperature_max = float(file_name[2]) / 100
                    except Exception as e:
                        print("Could not get min and max from name", e)
                    print("file_name", file_name, thermal.temperature_min, thermal.temperature_max)
                except OSError as e:
                    screen.screen_buff.draw_rectangle(0, 0, screen.width, screen.height, color=(30,30,30), fill=True)
                    screen.screen_buff.draw_string(round(screen.width/6), round(screen.height/2.3), "ERROR LOADING...", color=(255,0,0), scale=2.0)
                    logger.info("Error while loading ", control.playback_img_name, ". Try Again. Error", e)


                if menu.page == "ANALYSIS":

                    def map_g_to_temp(g):
                        return ((g * (thermal.temperature_max - thermal.temperature_min)) / 255.0) + thermal.temperature_min

                    img_touch_x = max(0,min(sensor.width() - 1, round(control.x * sensor.width()/screen.width) ))
                    img_touch_y = max(0,min(sensor.height() - 1, round(control.y * sensor.height()/screen.height) ))
                    pixel = "{:.2f}".format(map_g_to_temp(img.get_pixel(img_touch_x, img_touch_y)))

                    screen.screen_buff.draw_rectangle(control.x-5, control.y-5, 10, 10, color=(255,0,255), thickness=1, fill=True)
                    text_y_offset = 50 if control.y < screen.height//2 else -50
                    screen.screen_buff.draw_string(control.x - 20, control.y + text_y_offset, "{}".format(pixel))

                screen_refresh_needed = True


            if state is CameraState.POSTVIEW and utime.ticks_diff(utime.ticks_ms(), state_ticks_ms) > 2000:
                menu.back()

        ########################################################################
        # INPUT TASKS which are BIG
        if control.to_save_img:
            control.save_img(screen.screen_buff, thermal.temperature_min, thermal.temperature_max)
            menu.process_action("postview")
            led_green.on()
            utime.sleep_ms(100)
            led_green.off()


        ########################################################################
        # DISPLAY IN SCREEN
        if menu.state is CameraState.PLAYBACK and menu.page == "MENU":
            screen.screen_buff.draw_rectangle(0,0,screen.width//2,screen.height,color=(0,0,0), fill=True)

        if screen_refresh_needed:
            previous_text = text
            screen.screen_buff.draw_string(10, 10, text, color=(57, 255, 20), scale=2.1, mono_space=False)
            if state is CameraState.PLAYBACK:
                logger.info("Refresh needed")
            screen.write_to_screen(screen.screen_buff)
            screen_refresh_needed = False

        ########################################################################
        # OTHER FUNCTIONALITY

        if not running_from_ide and usb.isconnected():
            screen.screen_buff.draw_rectangle(0, screen.height//3, screen.width, screen.height//3, color=(10,10,10), fill=True)
            screen.screen_buff.draw_string(round(screen.width/5), round(screen.height/2.3), "USB DEBUGGING", color=(255,0,0), scale=2.0)
            screen.write_to_screen(screen.screen_buff)
            utime.sleep_ms(500)
            input_handler.disable()
            exit(0)
        if input_handler.pin.value() == 0 and input_handler.time_since_interrupt() > 100:
            input_handler.interrupt_callback(line="LOOP")

        gc.collect()


if __name__ == "__main__":
    main()
