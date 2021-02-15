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

from utils.rtc_time import time_datetime2string
import uos
import time
import sensor

class CameraState():
    PREVIEW = "PREVIEW"
    POSTVIEW = "POSTVIEW"
    PLAYBACK = "PLAYBACK"

class CameraPreview():
    THERMAL = "THERMAL"
    THERMAL_ANALYSIS = "THERMAL_ANALYSIS"
    THERMAL_GREY = "THERMAL_GREY"
    VISIBLE = "VISIBLE"
    MIX = "MIX"

class Control():

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


    to_save_img = False
    to_save_fb_as_startup = False

    always_pixel_pointer = False

    def __init__(self, logger):
        self.logger = logger
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
            self.preview = CameraPreview.THERMAL_GREY
        elif self.preview is CameraPreview.THERMAL_GREY:
            self.preview = CameraPreview.VISIBLE
        elif self.preview is CameraPreview.VISIBLE:
            self.preview = CameraPreview.MIX
        elif self.preview is CameraPreview.MIX:
            self.preview = CameraPreview.THERMAL
        self.logger.info("Change preview from ", previous, "to", self.preview)

    def get_last_saved_img(self):
        self.logger.info("Listing...")
        img_number = 0
        img_name = 0

        img_full_names = self.get_image_files()

        try:
            img_name = img_full_names[-1]
            img_name = img_name.split("/")[-1]
            img_name = img_name.split(self.img_format)[0]
            img_number_str = img_name.split("_")[0]
            img_number = int(img_number_str)
        except Exception as e:
            self.logger.info(e)

        print("Last", img_name, img_number)
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

    def save_img(self, screen_buff, temperature_min, temperature_max):
        if screen_buff:
            self.last_img_number += 1
            self.last_img_name = "{}/{:04d}_{:d}_{:d}{}".format(
                self.media_path, self.last_img_number, round(100 * temperature_min), round(100 * temperature_max), self.img_format
            )
            self.logger.info("Saving...", self.last_img_name)
            screen_buff.save(self.last_img_name)
            uos.sync()
            self.logger.info("Saved:", self.last_img_name)
        else:
            self.logger.info("No image to save")
        self.to_save_img = False

    def save_fb_as_startup(self, screen_buff):
        if screen_buff:
            screen_buff.save(self.startup_img_name)
            uos.sync()
        self.to_save_fb_as_startup = False

    def preview_info(self):
        string = ""
        string += "{} [{:.2f}]\n".format(self.preview, self.fps)
        #string += "x-y {} {} \nPress {} {} {} {} \n".format(
            #self.x, self.y,
            #self.button_shutter, self.button_top, self.button_middle, self.button_bottom,
        #)
        string += "{} mV {}\n".format(self.battery_millivolts, time_datetime2string())

        return string
