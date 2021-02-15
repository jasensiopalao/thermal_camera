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

import uos
from utils.menu import Menu

from utils.rtc_time import time_datetime2string, time_modify_rtc, time_rtc2dictionary
from .control import CameraState
from .sync_time import sync_time

from .user_settings import (
    save_control_settings,
    load_control_settings,
    save_thermal_settings,
    load_thermal_settings,
    save_camera_slave_calibration_settings,
    load_camera_slave_calibration_settings,
    save_touch_calibration_settings,
    load_touch_calibration_settings,
)

def load_menu(components):

    menu_preview = create_menu_preview(**components)
    menu_playback = create_menu_playback(**components)

    menu = components["menu"]
    control = components["control"]
    thermal = components["thermal"]
    settings = components["settings"]

    def save_img(control, **_):
        print("Snapshot...")
        control.to_save_img = True

    def next_preview():
        control.next_preview()
        save_control_settings(settings=settings, control=control)

    menu.structure = {
        "state": CameraState.PREVIEW,
        "page": "ROOT",
        "title": "", # (lambda: "{}".format(control.last_img_number)),
        "shutter": Menu.Entity(text=None, action=(save_img, components) ),
        "top" : Menu.Entity(text=None, action=next_preview),
        "middle": Menu.Entity(text=None, action={
            "state": CameraState.PREVIEW,
            "page": "INFO",
            "title": (lambda: control.preview_info() + thermal.get_thermal_statistics()),
            "shutter": Menu.Entity(text=None, action=(save_img, components) ),
            "top" : Menu.Entity(text="Views", action=next_preview),
            "middle": Menu.Entity(text="Menu", action=menu_preview),
            "bottom" :  Menu.Entity(text="Hide / Playback", action=menu.back),
            "postview": Menu.Entity(text=None, action={"state": CameraState.POSTVIEW, "title": "SNAPSHOT"}),
        }),
        "bottom" : Menu.Entity(text=None, action=menu_playback),
        "postview": Menu.Entity(text=None, action={"state": CameraState.POSTVIEW, "title": "SNAPSHOT"}),
    }

    menu.entity_order = ["top", "middle", "bottom"]

def create_menu_playback(time_settings, settings, menu, touch, control, camera_slave, screen, auxiliary_controller, **_):
    def save_fb_as_startup():
        control.to_save_fb_as_startup = True

    return {
        "state": CameraState.PLAYBACK,
        "page": "PHOTO_VIEW",
        "title": (lambda: "{} [{}]".format(control.playback_img_name, control.playback_index)),
        "shutter": menu.entity_reset_no_text,
        "top" : Menu.Entity(text=None, action=control.decrease_playback_index),
        "middle": Menu.Entity(text=None, action={
            "title": "OPTIONS",
            "page": "MENU",
            "shutter": menu.entity_back_no_text,
            "top": menu.entity_scroll_up,
            "bottom": menu.entity_scroll_down,
            "middle": menu.entity_scroll_selection,
            "items": [
                Menu.Entity(text="Analysis", action={
                    "page": "ANALYSIS",
                    "title": (lambda: "{} [{}]".format(control.playback_img_name, control.playback_index)),
                    "shutter": menu.entity_back_no_text,
                    "top": menu.entity_back_no_text,
                    "middle": menu.entity_back_no_text,
                    "bottom": menu.entity_back_no_text,
                }),
                menu.entity_back_action,
                Menu.Entity(text="Delete", action=[control.delete_playback_img_name, menu.back]),
                Menu.Entity(text="As Startup", action=[save_fb_as_startup, menu.back]),
            ],
        }),
        "bottom" : Menu.Entity(text=None, action=control.increase_playback_index),
    }

def create_menu_preview(logger, time_settings, settings, menu, touch, control, thermal, camera_slave, screen, auxiliary_controller, **_):

    def get_time_calibration_factor():
        return time_settings.dict.get("calibration_factor", 1.0)

    def time_save():
        time_rtc2dictionary(time_settings.dict)
        time_settings.dict["reference_seconds"] = auxiliary_controller.time()
        time_settings.write()
        uos.sync()
        logger.info("Time saved")
        sync_time(logger, screen, time_settings, auxiliary_controller)

    def time_settings_write():
        time_settings.write()

    def entity_to_modify_time(unit):
        return Menu.Entity(text=unit, action={
            "title": time_datetime2string,
            "shutter":  menu.entity_back_no_text,
            "top": Menu.Entity(text="Up", action=(time_modify_rtc, {"modify_amount":1, "modify_unit": unit})),
            "middle": Menu.Entity(text="Finish adjusting %s" % unit, action=menu.back),
            "bottom": Menu.Entity(text="Down", action=(time_modify_rtc, {"modify_amount":-1, "modify_unit": unit})),
        })


    def get_forward_seconds():
        auxiliary_controller.sync()
        absolute_seconds = auxiliary_controller.time()
        reference_seconds = time_settings.dict.get("reference_seconds", 581.4265)
        return (absolute_seconds - reference_seconds) * get_time_calibration_factor()


    def change_time_calibration_factor(modify_amount = 0.0001):
        time_settings.dict["calibration_factor"] = get_time_calibration_factor() + modify_amount
        sync_time(logger, screen, time_settings, auxiliary_controller)

    menu_time_change = {
        "title": time_datetime2string,
        "shutter": menu.entity_back_no_text,
        "top": menu.entity_scroll_up,
        "bottom": menu.entity_scroll_down,
        "middle": menu.entity_scroll_selection,
        "items": [
            entity_to_modify_time("year"),
            entity_to_modify_time("month"),
            entity_to_modify_time("day"),
            entity_to_modify_time("hour"),
            entity_to_modify_time("minute"),
            entity_to_modify_time("second"),
            Menu.Entity(text="Save date/time change", action=[time_save, menu.back]),
            Menu.Entity(text="Calibration", action={
                "title": (lambda: "Date {}\nSeconds: {}".format(time_datetime2string(), get_forward_seconds())) ,
                "shutter":  menu.entity_back_no_text,
                "top": Menu.Entity(text="Up", action=(change_time_calibration_factor, {"modify_amount":0.000005})),
                "middle": Menu.Entity(text=(lambda: "Finish adjusting factor {}".format(get_time_calibration_factor())), action=[menu.back, time_settings_write]),
                "bottom": Menu.Entity(text="Down", action=(change_time_calibration_factor, {"modify_amount":-0.000005})),
            }),
        ]
    }

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
        "shutter": menu.entity_back_no_text,
        "top": menu.entity_scroll_up,
        "bottom": menu.entity_scroll_down,
        "middle": menu.entity_scroll_selection,
        "items": [
            Menu.Entity(text=column_offset_print, action={
                "title": column_offset_print,
                "shutter":  menu.entity_back_no_text,
                "top": Menu.Entity(text="Up", action=camera_slave.increase_column_offset),
                "middle": menu.entity_back_action,
                "bottom": Menu.Entity(text="Down", action=camera_slave.decrease_column_offset),
            }),
            Menu.Entity(text=row_offset_print, action={
                "title": row_offset_print,
                "shutter":  menu.entity_back_no_text,
                "top": Menu.Entity(text="Up", action=camera_slave.increase_row_offset),
                "middle": menu.entity_back_action,
                "bottom": Menu.Entity(text="Down", action=camera_slave.decrease_row_offset),
            }),
            Menu.Entity(text=view_factor_print, action={
                "title": view_factor_print,
                "shutter":  menu.entity_back_no_text,
                "top": Menu.Entity(text="Up", action=[camera_slave.increase_column_factor, camera_slave.increase_row_factor]),
                "middle": menu.entity_back_action,
                "bottom": Menu.Entity(text="Down", action=[camera_slave.decrease_column_factor, camera_slave.decrease_row_factor]),
            }),
            Menu.Entity(text=column_factor_print, action={
                "title": column_factor_print,
                "shutter":  menu.entity_back_no_text,
                "top": Menu.Entity(text="Up", action=camera_slave.increase_column_factor),
                "middle": menu.entity_back_action,
                "bottom": Menu.Entity(text="Down", action=camera_slave.decrease_column_factor),
            }),
            Menu.Entity(text=row_factor_print, action={
                "title": row_offset_print,
                "shutter":  menu.entity_back_no_text,
                "top": Menu.Entity(text="Up", action=camera_slave.increase_row_factor),
                "middle": menu.entity_back_action,
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
        "shutter":  menu.entity_back_no_text,
        "top": Menu.Entity(text="OK", action=[
            touch.calibrate,
            (save_touch_calibration_settings, {"settings": settings, "touch": touch}),
            menu.back
        ]),
        "middle": menu.entity_back_action,
        "items": [
            Menu.Entity(text=(lambda: "x_offset {}".format(touch.x_offset)), action=None),
            Menu.Entity(text=(lambda: "y_offset {}".format(touch.y_offset)), action=None),
            Menu.Entity(text=(lambda: "x_factor {}".format(touch.x_factor)), action=None),
            Menu.Entity(text=(lambda: "y_factor {}".format(touch.y_factor)), action=None),
        ]
    }

    def emissivity_text():
        return "Emissivity. {:.1f}".format(thermal.emissivity)

    def emissivity_down():
        thermal.emissivity -= 1.0

    def emissivity_up():
        thermal.emissivity += 1.0

    def toggle_static_range():
        thermal.static_range = not thermal.static_range
        thermal.thermal_configure()

    def string_static_range_minimum():
        return "Static min Temp: {:.1f}".format(thermal.static_minimum)

    def static_range_minimum_down():
        thermal.static_minimum -= 1.0
        thermal.send_thermal_static_range()

    def static_range_minimum_up():
        thermal.static_minimum += 1.0
        thermal.send_thermal_static_range()

    def string_static_range_maximum():
        return "Static max Temp: {:.1f}".format(thermal.static_maximum)

    def static_range_maximum_down():
        thermal.static_maximum -= 1.0
        thermal.send_thermal_static_range()

    def static_range_maximum_up():
        thermal.static_maximum += 1.0
        thermal.send_thermal_static_range()

    menu_thermal_options = {
        "title": "THERMAL OPTIONS",
        "shutter": menu.entity_back_no_text,
        "top": menu.entity_scroll_up,
        "bottom": menu.entity_scroll_down,
        "middle": menu.entity_scroll_selection,
        "items": [
            Menu.Entity(text=(lambda: "Flat Field Corr. {}".format(thermal.get_thermal_statistics())), action=thermal.thermal_fcc),
            Menu.Entity(text=emissivity_text, action=
            {
                "title": emissivity_text,
                "shutter":  menu.entity_back_no_text,
                "top": Menu.Entity(text="Up", action=emissivity_up),
                "middle": menu.entity_back_action,
                "bottom": Menu.Entity(text="Down", action=emissivity_down),
            }),
            Menu.Entity(text=(lambda: "Gain: {}".format(thermal.string_gain_mode())), action=thermal.next_gain_mode),
            Menu.Entity(text=(lambda: "Static range: {}".format(thermal.static_range)), action=toggle_static_range),
            Menu.Entity(text=string_static_range_maximum, action=
            {
                "title": string_static_range_maximum,
                "shutter":  menu.entity_back_no_text,
                "top": Menu.Entity(text="Up", action=static_range_maximum_up),
                "middle": menu.entity_back_action,
                "bottom": Menu.Entity(text="Down", action=static_range_maximum_down),
            }),
            Menu.Entity(text=string_static_range_minimum, action=
            {
                "title": string_static_range_minimum,
                "shutter":  menu.entity_back_no_text,
                "top": Menu.Entity(text="Up", action=static_range_minimum_up),
                "middle": menu.entity_back_action,
                "bottom": Menu.Entity(text="Down", action=static_range_minimum_down),
            }),
            Menu.Entity(text="Save", action=[
                (save_thermal_settings, {"settings": settings, "thermal":thermal}),
                menu.back,
            ]),
            Menu.Entity(text="Restart", action=[thermal.initialize]),
        ],
    }

    def restore_backup():
        settings.read(from_backup=True)
        settings.write()

        load_camera_slave_calibration_settings(settings=settings, camera_slave=camera_slave)
        load_touch_calibration_settings(settings=settings, touch=touch)
        load_control_settings(settings=settings, control=control)
        load_thermal_settings(settings=settings, thermal=thermal)

    def save_backup():
        save_camera_slave_calibration_settings(settings=settings, camera_slave=camera_slave)
        save_touch_calibration_settings(settings=settings, touch=touch)
        save_control_settings(settings=settings, control=control)

        settings.write()  # First make sure the current settings were saved
        settings.write(to_backup=True)

    menu_manage_settings = {
        "title": "MANAGE SETTINGS",
        "shutter": menu.entity_back_no_text,
        "top": menu.entity_scroll_up,
        "bottom": menu.entity_scroll_down,
        "middle": menu.entity_scroll_selection,
        "items": [
            Menu.Entity(text="Restore Backup", action=[restore_backup, menu.back]),
            Menu.Entity(text="Save Backup", action=[save_backup, menu.back]),
        ],
    }

    def toggle_pixle_pointer():
        control.always_pixel_pointer = not control.always_pixel_pointer
        save_control_settings(settings=settings, control=control)

    menu_preview = {
        "title": "MAIN MENU",
        "shutter": menu.entity_reset_no_text,
        "top": menu.entity_scroll_up,
        "bottom": menu.entity_scroll_down,
        "middle": menu.entity_scroll_selection,
        "items": [
            Menu.Entity(text="Thermal options", action=menu_thermal_options),
            Menu.Entity(text=(lambda: "Always pointer: {}".format(control.always_pixel_pointer)), action=toggle_pixle_pointer),
            Menu.Entity(text="Calibrate Field Of View", action=menu_camera_slave_calibration),
            Menu.Entity(text="Calibrate Touch", action=menu_touch_calibration),
            Menu.Entity(text="Manage settings", action=menu_manage_settings),
            Menu.Entity(text="Set Time", action=menu_time_change),
            Menu.Entity(text=(lambda: "1 FPS {}".format(control.fps)), action=control.fps_reset),
        ],
    }
    return menu_preview
