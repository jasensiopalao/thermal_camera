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

camera_version = "1.3"

import gc
import utime
import machine
from sys import exit

from uctypes import addressof, bytearray_at

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
        print(boot_time, "Alloc", gc.mem_alloc(), "Free", gc.mem_free() ,": ", *args)

logger = Logger()
logger.info("Boot")
import sensor, image, time, utime, uos
from pyb import LED, disable_irq

import framebuf
import gc
from pyb import Pin, ExtInt
import time
from micropython import const
import micropython
import pyb

usb = pyb.USB_VCP()

from time import sleep
from helpers import AuxCamera, InterruptHandler, Touch, TFT, Menu, DynamicSPI, qvga2qvga, qqvga2qvga, Settings

from camera_slave_control import CameraSlaveControl

###################################################################################################
# FRAMEWORK   CODE            #####################################################################
###################################################################################################

class CameraState():
    PREVIEW = "PREVIEW"
    POSTVIEW = "POSTVIEW"
    PLAYBACK = "PLAYBACK"

class CameraPreview():
    THERMAL = "THERMAL"
    THERMAL_ANALYSIS = "THERMAL_ANALYSIS"
    VISIBLE = "VISIBLE"
    MIX = "MIX"

import struct

class Camera():

    thermal = True
    preview = CameraPreview.THERMAL

    img_format = ".bmp"
    last_img_name = ""
    last_img_number = 0
    fps = 0
    battery_millivolts = 0
    button_shutter = 0
    button_top = 0
    button_middle = 0
    button_bottom = 0
    x = 0
    y = 0
    playback_index = 0
    playback_img_name = ""

    thermal_tlinear_resolution = 0.1
    temperature_mean = 0.0
    temperature_max = 0.0
    temperature_min = 0.0

    to_save_img = False
    to_save_fb_as_startup = False

    always_pixel_pointer = False

    def __init__(self, width=320, height=240, alloc_screen_buff=False):
        self.media_path = "DCIM"
        self.startup_img_name = "startup.bmp"
        try:
            uos.mkdir(self.media_path)
            uos.sync()
        except OSError as e:
            if e.args[0] == errno.EEXIST:
                pass
            else:
                raise
        self.last_img_name, self.last_img_number = self.get_last_saved_img()
        self.clock = time.clock()
        self.fps_reset()
        if alloc_screen_buff:
            self.screen_buff = sensor.alloc_extra_fb(width, height, sensor.RGB565)

        self.width = self.screen_buff.width()
        self.height = self.screen_buff.height()

    def fps_tick(self):
        self.fps = self.clock.fps()
        self.clock.tick()

    def fps_reset(self):
        self.clock.reset()
        self.clock.tick()

    def set_normal_resolution(self):
        sensor.set_pixformat(sensor.RGB565)
        sensor.set_framesize(sensor.QVGA)
        sensor.skip_frames(time=2000)
        self.fps_reset()

    def set_low_resolution(self):
        sensor.set_pixformat(sensor.RGB565)
        sensor.set_framesize(sensor.QQVGA)
        sensor.skip_frames(time=2000)
        self.fps_reset()

    def next_preview(self):
        previous = self.preview
        if self.preview is CameraPreview.THERMAL:
            self.preview = CameraPreview.THERMAL_ANALYSIS
        elif self.preview is CameraPreview.THERMAL_ANALYSIS:
            self.preview = CameraPreview.VISIBLE
        elif self.preview is CameraPreview.VISIBLE:
            self.preview = CameraPreview.MIX
        elif self.preview is CameraPreview.MIX:
            self.preview = CameraPreview.THERMAL
        logger.info("Change preview from ", previous, "to", self.preview)

    def get_last_saved_img(self):
        logger.info("Listing...")
        img_number = 0
        img_name = 0

        img_full_names = self.get_image_files()

        try:
            img_name = img_full_names[-1]
            img_name = img_name.split("/")[-1]
            img_number = int(img_name.split(self.img_format)[0])
        except Exception as e:
            logger.info(e)

        return img_name, img_number

    def get_image_files(self):
        img_full_names = []
        for name, *_ in sorted(uos.ilistdir(self.media_path)):
            names = name.split(self.img_format)
            if len(names) == 1:
                continue
            img_full_names.append("{}/{}".format(self.media_path, name))
        return img_full_names

    def update_playback_img_name(self, go_to_last=False):
        files = self.get_image_files()
        max_index = len(files) - 1
        if go_to_last:
            self.playback_index = max_index
        if files:
            # Wrap around
            if self.playback_index < 0:
                self.playback_index = max_index
            if self.playback_index > max_index:
                self.playback_index = 0
            self.playback_img_name = files[self.playback_index]
        else:
            self.playback_img_name = ""
        return self.playback_img_name

    def increase_playback_index(self):
        self.playback_index += 1
        self.update_playback_img_name()
        print(self.playback_img_name)

    def decrease_playback_index(self):
        self.playback_index -= 1
        self.update_playback_img_name()
        print(self.playback_img_name)

    def delete_playback_img_name(self):
        uos.remove(self.playback_img_name)
        uos.sync()
        self.update_playback_img_name()
        print(self.playback_img_name)

    def save_img(self):
        if self.screen_buff:
            self.last_img_number += 1
            self.last_img_name = "{}/{:04d}{}".format(self.media_path, self.last_img_number, self.img_format)
            logger.info("Saving...", self.last_img_name)
            self.screen_buff.save(self.last_img_name)
            uos.sync()
            logger.info("Saved:", self.last_img_name)
        else:
            logger.info("No image to save")
        self.to_save_img = False

    def save_fb_as_startup(self):
        if sensor.get_fb():
            sensor.get_fb().save(self.startup_img_name)
            uos.sync()
        self.to_save_fb_as_startup = False

    def thermal_fcc(self):
        logger.info("SYS Run FFC Normalization")
        sensor.ioctl(sensor.IOCTL_LEPTON_RUN_COMMAND, 0x0242)
        logger.info("RAD FFC Normalization")
        sensor.ioctl(sensor.IOCTL_LEPTON_RUN_COMMAND, 0x4E2E)

    def prepare_thermal_statistics(self):
        if not self.thermal:
            return

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x0100, 2)
        LEP_AGC_ENABLE_TAG = struct.unpack("<I", data)[0]
        #LEP_AGC_DISABLE=0,
        #LEP_AGC_ENABLE
        logger.info("AGC Enable and Disable", LEP_AGC_ENABLE_TAG)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x0148, 2)
        LEP_AGC_ENABLE_TAG = struct.unpack("<I", data)[0]
        #LEP_AGC_DISABLE=0,
        #LEP_AGC_ENABLE
        logger.info("AGC Calculation Enable State", LEP_AGC_ENABLE_TAG)
        ###############################################################
        # RADIOMETRY

        sensor.ioctl(sensor.IOCTL_LEPTON_SET_ATTRIBUTE, 0x4E11, struct.pack("<I", 1))

        self.thermal_fcc()
        sensor.snapshot()
        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4E24, 2)
        FLR_RAD_TS_MODE_E_TAG = struct.unpack("<I", data)[0]
        #FLR_RAD_TS_USER_MODE = 0
        #FLR_RAD_TS_CAL_MODE = 1
        #FLR_RAD_TS_FIXED_MODE = 2
        #FLR_RAD_TS_END_TS_MODE = 3
        logger.info("RAD TShutter Mode", FLR_RAD_TS_MODE_E_TAG)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4E10, 2)
        LEP_RAD_ENABLE_E_TAG = struct.unpack("<I", data)[0]
        #LEP_RAD_DISABLE = 0,
        #LEP_RAD_ENABLE,
        logger.info("RAD Radiometry Control Enable", LEP_RAD_ENABLE_E_TAG)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4E28, 1)
        LEP_RAD_KELVIN_T = struct.unpack("<H", data)[0]
        logger.info("RAD TShutter Temperature", LEP_RAD_KELVIN_T)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4E30, 2)
        LEP_RAD_STATUS_E = struct.unpack("<I", data)[0]
        #LEP_RAD_STATUS_ERROR = -1,
        #LEP_RAD_STATUS_READY = 0,
        #LEP_RAD_STATUS_BUSY,
        #LEP_RAD_FRAME_AVERAGE_COLLECTING_FRAMES
        logger.info("RAD Run Status", LEP_RAD_STATUS_E)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4EC0, 2)
        LEP_RAD_ENABLE_E_TAG = struct.unpack("<I", data)[0]
        #LEP_RAD_DISABLE = 0,
        #LEP_RAD_ENABLE,
        logger.info("RAD T-Linear Enable State", LEP_RAD_ENABLE_E_TAG)

        startRow = 0
        startCol = 0
        endRow = sensor.height() - 1
        endCol = sensor.width() - 1
        data = struct.pack("<HHHH", startRow, startCol, endRow, endCol)
        sensor.ioctl(sensor.IOCTL_LEPTON_SET_ATTRIBUTE, 0x4ECD, data)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4ECC, 4)
        startRow_rx, startCol_rx, endRow_rx, endCol_rx = struct.unpack("<HHHH", data)
        logger.info("Spotmeter {} {} {} {}".format(startRow_rx, startCol_rx, endRow_rx, endCol_rx))
        if startRow != startRow_rx or startCol != startCol_rx or endRow != endRow_rx or endCol != endCol_rx:
            raise ValueError("Spotmeter wrong window")

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4EC4, 2)
        self.thermal_tlinear_resolution = 0.01 if struct.unpack("<I", data)[0] else 0.1
        print("thermal_tlinear_resolution", self.thermal_tlinear_resolution)

    def tlinear2celcius(self, tlinear):
        """ tlinear_to_celcius """
        return (tlinear * self.thermal_tlinear_resolution) - 273.15

    def get_thermal_statistics(self):
        if not self.thermal:
            return ""

        string = ""
        fpa_temp = sensor.ioctl(sensor.IOCTL_LEPTON_GET_FPA_TEMPERATURE)
        aux_temp = sensor.ioctl(sensor.IOCTL_LEPTON_GET_AUX_TEMPERATURE)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4ED0, 4)
        radSpotmeterValue, radSpotmeterMaxValue, radSpotmeterMinValue, radSpotmeterPopulation = struct.unpack("<HHHH", data)

        self.temperature_mean = self.tlinear2celcius(radSpotmeterValue)
        self.temperature_max = self.tlinear2celcius(radSpotmeterMaxValue)
        self.temperature_min = self.tlinear2celcius(radSpotmeterMinValue)
        string += "FPA {:.2f} AUX {:.2f}".format(fpa_temp, aux_temp)
        string += "\n {:.2f} {:.2f} {:.2f}".format(self.temperature_mean, self.temperature_max, self.temperature_min)

        return string

    def preview_info(self):
        string = ""
        string += "{} [{:.2f}]\n".format(self.preview, self.fps)
        #string += "x-y {} {} \nPress {} {} {} {} \n".format(
            #self.x, self.y,
            #self.button_shutter, self.button_top, self.button_middle, self.button_bottom,
        #)
        string += "{} mV\n".format(self.battery_millivolts)
        string += self.get_thermal_statistics()
        self.generated_text = string
        return string



def save_camera_settings(settings, camera):
    if "camera" not in settings.dict:
        settings.dict["camera"] = {}
    camera_settings = settings.dict["camera"]

    camera_settings["always_pixel_pointer"] = camera.always_pixel_pointer
    settings.write()
    print("Camera settings saved")

def load_camera_settings(settings, camera):
    settings.read()
    if "camera" not in settings.dict:
        return
    camera_settings = settings.dict["camera"]

    camera.always_pixel_pointer = camera_settings["always_pixel_pointer"]
    print("Camera settings loaded")



def save_camera_slave_calibration_settings(settings, camera_slave):
    if "camera_slave" not in settings.dict:
        settings.dict["camera_slave"] = {}
    camera_slave_settings = settings.dict["camera_slave"]

    camera_slave_settings["column_offset"] = camera_slave.control.column_offset
    camera_slave_settings["row_offset"] = camera_slave.control.row_offset
    camera_slave_settings["column_zoom_numerator"] = camera_slave.control.column_zoom_numerator
    camera_slave_settings["column_zoom_denominator"] = camera_slave.control.column_zoom_denominator
    camera_slave_settings["row_zoom_numerator"] = camera_slave.control.row_zoom_numerator
    camera_slave_settings["row_zoom_denominator"] = camera_slave.control.row_zoom_denominator
    settings.write()
    print("Camera slave settings saved")

def load_camera_slave_calibration_settings(settings, camera_slave):
    settings.read()
    if "camera_slave" not in settings.dict:
        return
    camera_slave_settings = settings.dict["camera_slave"]

    camera_slave.control.column_offset = camera_slave_settings["column_offset"]
    camera_slave.control.row_offset = camera_slave_settings["row_offset"]
    camera_slave.control.column_zoom_numerator = camera_slave_settings["column_zoom_numerator"]
    camera_slave.control.column_zoom_denominator = camera_slave_settings["column_zoom_denominator"]
    camera_slave.control.row_zoom_numerator = camera_slave_settings["row_zoom_numerator"]
    camera_slave.control.row_zoom_denominator = camera_slave_settings["row_zoom_denominator"]
    print("Camera slave screen settings loaded")

def save_touch_calibration_settings(settings, touch):
    if "touch" not in settings.dict:
        settings.dict["touch"] = {}
    touch_settings = settings.dict["touch"]

    touch_settings["x_offset"] = touch.x_offset
    touch_settings["y_offset"] = touch.y_offset
    touch_settings["x_factor"] = touch.x_factor
    touch_settings["y_factor"] = touch.y_factor
    settings.write()
    print("Touch screen settings saved")

def load_touch_calibration_settings(settings, touch):
    settings.read()
    if "touch" not in settings.dict:
        return
    touch_settings = settings.dict["touch"]

    touch.x_offset = touch_settings["x_offset"]
    touch.y_offset = touch_settings["y_offset"]
    touch.x_factor = touch_settings["x_factor"]
    touch.y_factor = touch_settings["y_factor"]
    print("Touch screen settings loaded")

def load_menu(menu, settings, touch, camera, camera_slave, screen, **kwargs):

    def unused():
        return "empty"


    scroll_up = Menu.Entity(text=None, action=menu.cursor_decrement)
    scroll_down = Menu.Entity(text=None, action=menu.cursor_increment)
    scroll_selection = Menu.Entity(text=None, action=menu.cursor_action)

    back_action = Menu.Entity(text="Back", action=menu.back)
    back_no_text = Menu.Entity(text=None, action=menu.back)
    reset_no_text = Menu.Entity(text=None, action=menu.reset)

    # Main display
    # shutter foto
    # display mode real vision cam1/cam2/mix
    # display_menu/menu
    # run/playback

    # General menus
    # back/ double cancels
    # up
    # enter
    # down
    def column_factor():
        if camera_slave.control.column_zoom_denominator == 0:
            return 999
        return camera_slave.control.column_zoom_numerator/camera_slave.control.column_zoom_denominator

    def row_factor():
        if camera_slave.control.row_zoom_denominator == 0:
            return 999
        return camera_slave.control.row_zoom_numerator/camera_slave.control.row_zoom_denominator

    column_offset_print = (lambda: "col offset {}".format(camera_slave.control.column_offset))
    row_offset_print = (lambda: "row offset {}".format(camera_slave.control.row_offset))

    column_factor_print = (lambda: "col factor {:.2f} {}/{}".format(column_factor(), camera_slave.control.column_zoom_numerator, camera_slave.control.column_zoom_denominator))
    row_factor_print = (lambda: "row factor {:.2f} {}/{}".format(row_factor(), camera_slave.control.row_zoom_numerator, camera_slave.control.row_zoom_denominator))

    view_factor_print = (lambda: "factor {:.2f} {:.2f}".format(row_factor(), column_factor()))

    def full_field_of_view_camera_slave():
        camera_slave.control.column_offset = 0
        camera_slave.control.row_offset = 0
        camera_slave.control.column_zoom_numerator = 20
        camera_slave.control.column_zoom_denominator = 20
        camera_slave.control.row_zoom_numerator = 20
        camera_slave.control.row_zoom_denominator = 20


    menu_camera_slave_calibration = {
        "title": "Visual camera FIELD OF VIEW",
        "page": "CAMERA_SLAVE_CALIBRATION",
        "shutter": back_no_text,
        "top": scroll_up,
        "bottom": scroll_down,
        "middle": scroll_selection,
        "items": [
            Menu.Entity(text=column_offset_print, action={
                "title": column_offset_print,
                "shutter":  back_no_text,
                "top": Menu.Entity(text="Up", action=camera_slave.increase_column_offset),
                "middle": back_action,
                "bottom": Menu.Entity(text="Down", action=camera_slave.decrease_column_offset),
            }),
            Menu.Entity(text=row_offset_print, action={
                "title": row_offset_print,
                "shutter":  back_no_text,
                "top": Menu.Entity(text="Up", action=camera_slave.increase_row_offset),
                "middle": back_action,
                "bottom": Menu.Entity(text="Down", action=camera_slave.decrease_row_offset),
            }),
            Menu.Entity(text=view_factor_print, action={
                "title": view_factor_print,
                "shutter":  back_no_text,
                "top": Menu.Entity(text="Up", action=[camera_slave.increase_column_factor, camera_slave.increase_row_factor]),
                "middle": back_action,
                "bottom": Menu.Entity(text="Down", action=[camera_slave.decrease_column_factor, camera_slave.decrease_row_factor]),
            }),
            Menu.Entity(text=column_factor_print, action={
                "title": column_factor_print,
                "shutter":  back_no_text,
                "top": Menu.Entity(text="Up", action=camera_slave.increase_column_factor),
                "middle": back_action,
                "bottom": Menu.Entity(text="Down", action=camera_slave.decrease_column_factor),
            }),
            Menu.Entity(text=row_factor_print, action={
                "title": row_offset_print,
                "shutter":  back_no_text,
                "top": Menu.Entity(text="Up", action=camera_slave.increase_row_factor),
                "middle": back_action,
                "bottom": Menu.Entity(text="Down", action=camera_slave.decrease_row_factor),
            }),
            Menu.Entity(text="OK", action=[
                (save_camera_slave_calibration_settings, {"settings": settings, "camera_slave": camera_slave}),
                menu.back,
            ]),
            Menu.Entity(text="FULL Field of View", action=full_field_of_view_camera_slave),
        ]
    }

    def touch_calibration_title():
        xpoints = len(touch.x_calibration_points)
        if not xpoints:
            return "Drag the finger on screen"
        else:
            return "{} points saved".format(xpoints)

    menu_touch_calibration = {
        "title": touch_calibration_title,
        "page": "TOUCH_CALIBRATION",
        "shutter":  back_no_text,
        "top": Menu.Entity(text="OK", action=[
            touch.calibrate,
            (save_touch_calibration_settings, {"settings": settings, "touch": touch}),
            menu.back
        ]),
        "middle": back_action,
        "items": [
            Menu.Entity(text=(lambda: "x_offset {}".format(touch.x_offset)), action=None),
            Menu.Entity(text=(lambda: "y_offset {}".format(touch.y_offset)), action=None),
            Menu.Entity(text=(lambda: "x_factor {}".format(touch.x_factor)), action=None),
            Menu.Entity(text=(lambda: "y_factor {}".format(touch.y_factor)), action=None),
        ]
    }

    def save_fb_as_startup():
        camera.to_save_fb_as_startup = True

    menu_playback = {
        "state": CameraState.PLAYBACK,
        "page": "PHOTO_VIEW",
        "title": (lambda: "{} [{}]".format(camera.playback_img_name, camera.playback_index)),
        "shutter": reset_no_text,
        "top" : Menu.Entity(text=None, action=camera.decrease_playback_index),
        "middle": Menu.Entity(text=None, action={
            "title": "OPTIONS",
            "shutter": back_no_text,
            "top": scroll_up,
            "bottom": scroll_down,
            "middle": scroll_selection,
            "items": [
                back_action,
                Menu.Entity(text="Delete", action=[camera.delete_playback_img_name, menu.back]),
                Menu.Entity(text="As Startup", action=[save_fb_as_startup, menu.back]),
            ],
        }),
        "bottom" : Menu.Entity(text=None, action=camera.increase_playback_index),
    }
    def toggle_pixle_pointer():
        camera.always_pixel_pointer = not camera.always_pixel_pointer
        save_camera_settings(settings=settings, camera=camera)

    menu_main = {
        "title": "MAIN MENU",
        "shutter": reset_no_text,
        "top": scroll_up,
        "bottom": scroll_down,
        "middle": scroll_selection,
        "items": [
            Menu.Entity(text=(lambda: "Flat Field Corr. {}".format(camera.get_thermal_statistics())), action=camera.thermal_fcc),
            Menu.Entity(text=(lambda: "Always pointer: {}".format(camera.always_pixel_pointer)), action=toggle_pixle_pointer),
            Menu.Entity(text="Calibrate Field Of View", action=menu_camera_slave_calibration),
            Menu.Entity(text="Calibrate Touch", action=menu_touch_calibration),
            Menu.Entity(text=(lambda: "1 FPS {}".format(camera.fps)), action=camera.fps_reset),
        ],
    }

    def save_img():
        camera.to_save_img = True

    menu.structure = {
        "state": CameraState.PREVIEW,
        "page": "ROOT",
        "title": "", # (lambda: "{}".format(camera.last_img_number)),
        "shutter": Menu.Entity(text=None, action=save_img),
        "top" : Menu.Entity(text=None, action=camera.next_preview),
        "middle": Menu.Entity(text=None, action={
            "state": CameraState.PREVIEW,
            "page": "INFO",
            "title": camera.preview_info,
            "shutter": Menu.Entity(text=None, action=save_img),
            "top" : Menu.Entity(text="Views", action=camera.next_preview),
            "middle": Menu.Entity(text="Menu", action=menu_main),
            "bottom" :  Menu.Entity(text="Hide / Playback", action=menu.back),
            "postview": Menu.Entity(text=None, action={"state": CameraState.POSTVIEW, "title": "SNAPSHOT"}),
        }),
        "bottom" : Menu.Entity(text=None, action=menu_playback),
        "postview": Menu.Entity(text=None, action={"state": CameraState.POSTVIEW, "title": "SNAPSHOT"}),
    }

    menu.entity_order = ["top", "middle", "bottom"]

    # TODO check print thermal, and set regoin of interest spotmeter. Make default display info
    menu.process_action("middle")
    logger.info("Menu initialized")

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

class ImageBuffer():
    """ There seems to be some bug which causes alloc_extra_fb to overwrite the previous object memory
    pointer
    This causes all frame buffers to write only in the piece of memory of the last one """
    pass

def testing_bug(screen, **kwargs):

    # TODO remove
    logger.info("Test")
    new_alloc = None
    while True:
        old_alloc = new_alloc
        new_alloc = sensor.alloc_extra_fb(320, 240, sensor.RGB565)
        print(addressof(new_alloc), addressof(new_alloc.bytearray()))
        new_alloc.draw_rectangle(0,0, 100, 100, color=(0,0,255), fill=True)
        if old_alloc:
            print("Change old")
            print(addressof(old_alloc), addressof(old_alloc.bytearray()))
            old_alloc.draw_rectangle(0,0, 100, 100, color=(0,255,0), fill=True)
            print("done")
            print("old in red")
            screen.write_to_screen(old_alloc)
        utime.sleep_ms(1000)
        print("new in blue")
        screen.write_to_screen(new_alloc)
        utime.sleep_ms(1000)


def testing_bug2(screen, **kwargs):

    logger.info("Test")
    new_alloc = None
    old_alloc = sensor.alloc_extra_fb(320, 240, sensor.RGB565)
    new_alloc = sensor.alloc_extra_fb(320, 240, sensor.RGB565)
    print(addressof(old_alloc), addressof(old_alloc.bytearray()))
    old_alloc.draw_rectangle(0,0, 100, 100, color=(0,255,255), fill=True)
    print(addressof(new_alloc), addressof(new_alloc.bytearray()))
    new_alloc.draw_rectangle(0,0, 100, 100, color=(0,0,255), fill=True)
    while True:
        print("old")
        screen.write_to_screen(old_alloc)
        utime.sleep_ms(1000)
        print("new in blue")
        screen.write_to_screen(new_alloc)
        utime.sleep_ms(1000)
        old_alloc.draw_rectangle(0,0, 100, 100, color=(255,0,0), fill=True)


def testing_bug3(screen, camera, camera_slave, **kwargs):

    logger.info("Test")
    print(addressof(camera.screen_buff), addressof(camera.screen_buff.bytearray()))
    camera.screen_buff.draw_rectangle(0,0, 100, 100, color=(0,255,255), fill=True)
    print(addressof(camera_slave.rx_buff), addressof(camera_slave.rx_buff.bytearray()))
    camera_slave.rx_buff.draw_rectangle(0,0, 100, 100, color=(0,0,255), fill=True)
    while True:
        print("old")
        screen.write_to_screen(camera.screen_buff)
        utime.sleep_ms(1000)
        print("new in blue")
        screen.write_to_screen(camera_slave.rx_buff)
        utime.sleep_ms(1000)
        camera.screen_buff.draw_rectangle(0,0, 100, 100, color=(255,0,0), fill=True)

def testing_workaround(screen, **kwargs):

    # TODO remove
    logger.info("Test")
    new_alloc = None
    while True:
        old_alloc = new_alloc
        new_alloc = sensor.alloc_extra_fb(320, 240, sensor.RGB565)
        print(addressof(new_alloc), addressof(new_alloc.bytearray()))
        new_alloc.draw_rectangle(0,0, 100, 100, color=(0,0,255), fill=True)
        if old_alloc:
            print("Change old")
            print(addressof(old_alloc), addressof(old_alloc.bytearray()))
            old_alloc.draw_rectangle(0,0, 100, 100, color=(0,255,0), fill=True)
            print("done")
            print("old in red")
            screen.write_to_screen(bytearray_at(addressof(old_alloc), 320 * 240 * 2))
        utime.sleep_ms(1000)
        print("new in blue")
        screen.write_to_screen(bytearray_at(addressof(new_alloc), 320 * 240 * 2))
        utime.sleep_ms(1000)


def main():

    ##############################################################################
    # CREATE COMPONENTS
    logger.info("uname", uos.uname())

    led_red = LED(1) # red led
    led_red.off()
    camera = Camera(width=320, height=240, alloc_screen_buff=True)

    # SPI at 40000000 or start_delay=100 would lead to data corruption
    camera_slave = CameraSlave(
        spi=DynamicSPI(
            baudrate=30000000, pin_cs=Pin.board.P4, polarity=0, phase=0, start_delay=500,
        ),
        pin_data_ready=Pin.board.P5,
        width=camera.width,
        height=camera.height,
        alloc_rx_buff=True
    )

    touch = Touch(
        spi=DynamicSPI(
            baudrate=2000000, pin_cs=Pin.board.P7, polarity=0, phase=0, start_delay=10, byte_delay=10,
        )
    )

    aux_camera = AuxCamera(
        spi=DynamicSPI(
            baudrate=2500000, pin_cs=Pin.board.P6, polarity=1, phase=0, start_delay=10, byte_delay=100,
        )
    )

    screen = TFT(
        spi=DynamicSPI(
            baudrate=54000000, pin_cs=Pin.board.P3, polarity=0, phase=0
        ),
        pin_dc=Pin.board.P9
    )

    menu = Menu()
    settings = Settings("camera.json")

    input_handler = InterruptHandler(
        pin_interrupt=Pin.board.P8, trigger=ExtInt.IRQ_FALLING
    )

    components = {
        "aux_camera": aux_camera,
        "touch": touch,
        "camera": camera,
        "menu": menu,
        "screen": screen,
        "settings": settings,
        "input_handler": input_handler,
        "camera_slave": camera_slave,
    }

    #testing_bug3(**components)
    ###########################
    DynamicSPI._verbose = False
    aux_camera._verbose = False

    ##############################################################################
    # INITIALIZE COMPONENTS

    #create an instance of the screen driver
    #you mustr pass a SPI bus and type of screen (ili9341 320,240 or st7735 160,120
    #optional can pass cs pin and dc pin default is cs='P3' and dc='P9'
    logger.info("Initializing screen...")
    screen.initialize()
    screen.set_window(0,0,camera.width,camera.height)

    try:
        image.Image(camera.startup_img_name, copy_to_fb=camera.screen_buff)

        camera.screen_buff.draw_rectangle(0, 0, camera.width, 20, color=(30,30,30), fill=True)
        camera.screen_buff.draw_string(10,0, """Shutter Button is "Back" button""", color=(0,200,30), scale=2.0, mono_space=False)

        camera.screen_buff.draw_rectangle(0, round(camera.height*3/4), camera.width, round(camera.height*4/4), color=(30,30,30), fill=True)
        startup_text = "by JONATAN ASENSIO PALAO. v" + camera_version
        camera.screen_buff.draw_string(round(camera.width/11), round(camera.height*3.1/4), startup_text, color=(0,200,30), scale=2.0, mono_space=False)

        camera.screen_buff.draw_string(round(camera.width/11), round(camera.height*3.6/4), "LOADING... WAIT", color=(200,0,0), scale=2.0, mono_space=False)

        screen.write_to_screen(camera.screen_buff)
    except Exception as e:
        logger.info("Could not display startup image {}".format(e))

    logger.info("Initializing camera...")
    def setup_visual_camera():
        sensor.reset()
        sensor.set_pixformat(sensor.RGB565)
        sensor.set_framesize(sensor.QVGA)
        sensor.skip_frames(n=1)

    def setup_thermal_camera():
        import struct
        #min_temp_in_celsius = 15.0
        #max_temp_in_celsius = 40.0

        print("Resetting Lepton...")
        # These settings are applied on reset
        try:
            sensor.reset()
        except Exception as e:
            logger.info("{}".format(e))
            raise
        sensor.ioctl(sensor.IOCTL_LEPTON_SET_MEASUREMENT_MODE, False)
        #sensor.ioctl(sensor.IOCTL_LEPTON_SET_MEASUREMENT_MODE, True)
        #sensor.ioctl(sensor.IOCTL_LEPTON_SET_MEASUREMENT_RANGE, min_temp_in_celsius, max_temp_in_celsius)
        print("Lepton Res (%dx%d)" % (sensor.ioctl(sensor.IOCTL_LEPTON_GET_WIDTH),
                                      sensor.ioctl(sensor.IOCTL_LEPTON_GET_HEIGHT)))
        print("Radiometry Available: " + ("Yes" if sensor.ioctl(sensor.IOCTL_LEPTON_GET_RADIOMETRY) else "No"))

        sensor.set_pixformat(sensor.GRAYSCALE)
        sensor.set_framesize(sensor.QQVGA)
        sensor.skip_frames(time=5000)

        camera.prepare_thermal_statistics()

    if camera.thermal:
        setup_thermal_camera()
    else:
        setup_visual_camera()

    logger.info("Initializing auxiliar processor...")
    aux_camera.initialize()

    logger.info("Initializing camera slave...")
    camera_slave.sync(ignore_busy=True)

    logger.info("Enabling input interrupts...")
    input_handler.enable(
        callback=input_interrupt, **components
    )

    logger.info("Loading settings...")

    load_camera_slave_calibration_settings(settings=settings, camera_slave=camera_slave)
    load_touch_calibration_settings(settings=settings, touch=touch)
    load_camera_settings(settings=settings, camera=camera)

    logger.info("Loading menu...")
    load_menu(**components)

    logger.info("Running main loop...")
    loop(**components)


###################################################################################################
# APPLICATION CODE            #####################################################################
###################################################################################################

def input_interrupt(aux_camera, touch, camera, menu, screen, input_handler, **kwargs):
    #spi = aux_camera._spi
    spi = touch.spi
    if not spi.lock(allow_relock=True, release_callback=input_handler.interrupt_callback, line="SPI"):
        #logger.info("SPI IN USE...")
        return

    x, y = touch.get_pixel() # get_raw
    if touch.is_valid_measurement():
        if "TOUCH_CALIBRATION" in menu.page:
            touch.x_calibration_points.append(touch.x_raw)
            touch.y_calibration_points.append(touch.y_raw)

        camera.x = x
        camera.y = y

        # return

    aux_camera.sync()
    camera.battery_millivolts = aux_camera.battery_millivolts
    camera.button_shutter = aux_camera.button_shutter
    camera.button_top = aux_camera.button_top
    camera.button_middle = aux_camera.button_middle
    camera.button_bottom = aux_camera.button_bottom

    if camera.button_shutter:
        menu.process_action("shutter")
    if camera.button_top:
        menu.process_action("top")
    if camera.button_middle:
        menu.process_action("middle")
    if camera.button_bottom:
        menu.process_action("bottom")

    if aux_camera.active_flags:
        logger.info("START ------------ after spi release:", kwargs)
        aux_camera.print_data()
        logger.info(" END -------------")

def loop(camera, screen, menu, input_handler, camera_slave, **kwargs):

    led_green = LED(2) # red led
    led_green.off()

    usb = pyb.USB_VCP()
    running_from_ide = usb.isconnected()


    def camera_slave_sync_cancel_condition():
        if camera.preview is not CameraPreview.VISIBLE or menu.state is not CameraState.PREVIEW:
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

    while True:
        changed_state = state is not menu.state
        state = menu.state

        changed_preview = camera_preview is not camera.preview
        camera_preview = camera.preview

        # -----------------------------------------------------------------------------------------
        # INITIALIZATIONS
        if changed_state:
            state_ticks_ms = utime.ticks_ms()
            logger.info("Processing state change to ", menu.state)
            if menu.state is CameraState.PREVIEW:
                camera.fps_reset()
            if menu.state is CameraState.PLAYBACK or menu.state is CameraState.POSTVIEW:
                #camera.set_normal_resolution()
                camera.update_playback_img_name(go_to_last=True)
                camera_playback_img_name = ""

        if changed_preview:
            camera.fps_reset()
            logger.info("Processing preview change to ", camera.preview)
            #if camera.preview is CameraPreview.THERMAL:
                #camera.set_low_resolution()
                #logger.info("Set low res")
            #if camera.preview is CameraPreview.VISIBLE:
                #camera.set_normal_resolution()
                #logger.info("Set normal res")
            #if camera.preview is CameraPreview.MIX:
                #camera.set_normal_resolution()

        # -----------------------------------------------------------------------------------------
        # RUN TIME

        if state is CameraState.PREVIEW:
            camera.fps_tick()
            screen_refresh_needed = True
            text = "\n" + menu.generate_text()

            if camera.preview is CameraPreview.THERMAL or camera.preview is CameraPreview.THERMAL_ANALYSIS or camera.preview is CameraPreview.MIX:
                def map_g_to_temp(g):
                    return ((g * (camera.temperature_max - camera.temperature_min)) / 255.0) + camera.temperature_min

                img = sensor.snapshot()
                img_touch_x = max(0,min(sensor.width() - 1, round(camera.x * sensor.width()/camera.width) ))
                img_touch_y = max(0,min(sensor.height() - 1, round(camera.y * sensor.height()/camera.height) ))
                pixel = "{:.2f}".format(map_g_to_temp(img.get_pixel(img_touch_x, img_touch_y)))
                if not camera.thermal:
                    pass
                elif camera.preview is CameraPreview.THERMAL or camera.preview is CameraPreview.MIX:
                    img.to_rainbow(color_palette=sensor.PALETTE_IRONBOW) # color it
                elif camera.preview is CameraPreview.THERMAL_ANALYSIS:

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

                qqvga2qvga(sensor.get_fb(), camera.screen_buff)

            if camera.preview is CameraPreview.VISIBLE or camera.preview is CameraPreview.MIX:
                input_handler.disable()
                sync_success = True
                sync_success = camera_slave.sync()
                input_handler.enable()
                if not sync_success:
                    logger.info("Failed sync")
                    camera.screen_buff.fill(c=(10,10,10))
                    camera.screen_buff.draw_string(camera.width//2, camera.height//2, "ERROR", c=(255,0,0))

                if camera.preview is CameraPreview.VISIBLE:
                    qvga2qvga(camera_slave.rx_buff, camera.screen_buff, 0, 1)
                    pixel = camera.screen_buff.get_pixel(camera.x, camera.y)
                elif camera.preview is CameraPreview.MIX:
                    qvga2qvga(camera_slave.rx_buff, camera.screen_buff, 0, 2)

            if menu.page != "ROOT" or camera.always_pixel_pointer:
                camera.screen_buff.draw_rectangle(camera.x-5, camera.y-5, 10, 10, color=(255,0,255), thickness=1, fill=True)
                if menu.state is CameraState.PREVIEW:
                    text_y_offset = 50 if camera.y < camera.height//2 else -50
                    camera.screen_buff.draw_string(camera.x - 20, camera.y + text_y_offset, "{}".format(pixel))

        if state is CameraState.PLAYBACK or state is CameraState.POSTVIEW:

            if camera.playback_img_name != camera_playback_img_name:
                camera_playback_img_name = camera.playback_img_name
                logger.info("Displaying image...", camera.playback_img_name)
                while True:
                    try:
                        image.Image(camera.playback_img_name, copy_to_fb=True)
                        break
                    except OSError as e:
                        logger.info("Error while loading ", camera.playback_img_name, ". Try Again. Error", e)
                        pass
                screen_refresh_needed = True
            if not camera.playback_img_name:
                logger.info("No image to be loaded")
                menu.back()
                continue

            qvga2qvga(sensor.get_fb(), camera.screen_buff, 0, 1)

            text = menu.generate_text()
            if previous_text != text:
                logger.info("will need refresh. Before", previous_text, " After ", text)
                screen_refresh_needed = True

            if state is CameraState.POSTVIEW and utime.ticks_diff(utime.ticks_ms(), state_ticks_ms) > 2000:
                menu.back()


        if menu.state is CameraState.PLAYBACK and menu.page != "PHOTO_VIEW":
            camera.screen_buff.draw_rectangle(0,0,camera.width//2,camera.height,color=(0,0,0), fill=True)

        if screen_refresh_needed:
            previous_text = text
            camera.screen_buff.draw_string(10, 10, text, color=127, scale=2.1, mono_space=False)
            if state is CameraState.PLAYBACK:
                logger.info("Refresh needed")
            screen.write_to_screen(camera.screen_buff)
            screen_refresh_needed = False

        ########################################################################
        # INPUT TASKS which are BIG
        if camera.to_save_img:
            camera.save_img()
            menu.process_action("postview")

        if camera.to_save_fb_as_startup:
            camera.save_fb_as_startup()

        ########################################################################
        # OTHER FUNCTIONALITY

        if not running_from_ide and usb.isconnected():
            camera.screen_buff.draw_rectangle(0, camera.height//3, camera.width, camera.height//3, color=(10,10,10), fill=True)
            camera.screen_buff.draw_string(round(camera.width/5), round(camera.height/2.3), "USB DEBUGGING", color=(255,0,0), scale=2.0)
            screen.write_to_screen(camera.screen_buff)
            utime.sleep_ms(500)
            input_handler.disable()
            exit(0)
        if input_handler.pin.value() == 0 and input_handler.time_since_interrupt() > 100:
            input_handler.interrupt_callback(line="LOOP")

        gc.collect()


if __name__ == "__main__":
    main()
