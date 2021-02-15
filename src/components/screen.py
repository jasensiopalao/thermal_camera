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

from utils.rtc_time import time_datetime2string, tuple_time2rtc, time_rtc2dictionary, time_dictionary2rtc, time_modify_rtc


def sync_time(logger, screen, time_settings, auxiliary_controller):

    absolute_seconds = auxiliary_controller.time()
    time_dictionary2rtc(time_settings.dict)
    reference_seconds = time_settings.dict.get("reference_seconds", 581.4265)
    calibration_factor = time_settings.dict.get("calibration_factor", 1.0)
    if absolute_seconds < reference_seconds:
        logger.info("Battery was unplugged")
        time_settings.dict["reference_seconds"] = absolute_seconds
        reference_seconds = 0
        time_settings.write()
        uos.sync()
        screen.screen_buff.draw_rectangle(0, 0, screen.width, screen.height, color=(30,30,30), fill=True)
        screen.screen_buff.draw_string(10,0, "TIME WAS LOST", color=(255,0,0), scale=2.0, mono_space=False)
        screen.write_to_screen(camera.screen_buff)
        utime.sleep_ms(2000)

    forward_seconds = max(0, absolute_seconds - reference_seconds) * calibration_factor
    time_modify_rtc(modify_amount=forward_seconds, modify_unit="second")
    logger.info("Local time set to:", time_datetime2string())
