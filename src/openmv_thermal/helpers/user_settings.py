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

from .control import CameraPreview

def save_control_settings(settings, control):
    if "control" not in settings.dict:
        settings.dict["control"] = {}
    control_settings = settings.dict["control"]

    control_settings["always_pixel_pointer"] = control.always_pixel_pointer
    control_settings["preview"] = control.preview

    settings.write()
    print("control settings saved")

def load_control_settings(settings, control):
    if "control" not in settings.dict:
        return
    control_settings = settings.dict["control"]

    control.always_pixel_pointer = control_settings["always_pixel_pointer"]
    control.preview = control_settings.get("preview", CameraPreview.THERMAL)

    print("control settings loaded")


def save_thermal_settings(settings, thermal):
    if "control" not in settings.dict:
        settings.dict["thermal"] = {}
    control_settings = settings.dict["thermal"]

    control_settings["static_range"] = thermal.static_range
    control_settings["static_minimum"] = thermal.static_minimum
    control_settings["static_maximum"] = thermal.static_maximum

    settings.write()
    print("thermal settings saved")


def load_thermal_settings(settings, thermal):
    if "control" not in settings.dict:
        return
    control_settings = settings.dict["thermal"]

    thermal.static_range = control_settings.get("static_range", False)
    thermal.static_minimum = control_settings.get("static_minimum", 10.0)
    thermal.static_maximum = control_settings.get("static_maximum", 35.0)

    print("thermal settings loaded")


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
    if "touch" not in settings.dict:
        return
    touch_settings = settings.dict["touch"]

    touch.x_offset = touch_settings["x_offset"]
    touch.y_offset = touch_settings["y_offset"]
    touch.x_factor = touch_settings["x_factor"]
    touch.y_factor = touch_settings["y_factor"]
    print("Touch screen settings loaded")
