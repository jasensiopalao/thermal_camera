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

import sensor
import utime
from pyb import LED
import struct

class Thermal():

    thermal_tlinear_resolution = 0.1
    temperature_mean = 0.0
    temperature_max = 0.0
    temperature_min = 0.0

    static_range = False
    static_minimum = 10.0
    static_maximum = 35.0

    gain_mode = 1

    sceneEmissivity = 0
    TBkgK = 0
    tauWindow = 0
    TWindowK = 0
    tauAtm = 0
    TAtmK = 0
    reflWindow = 0
    TReflK = 0

    def __init__(self, logger):
        self.logger = logger

    def initialize(self):

        led_red = LED(1)
        led_green = LED(2)
        led_blue = LED(3)
        led_green.on()
        led_blue.on()
        while True:
            try:
                sensor.reset()
                sensor.set_pixformat(sensor.GRAYSCALE)
                sensor.set_framesize(sensor.QQVGA)
                sensor.skip_frames(time=1)  # 5000
                break
            except Exception as e:
                self.logger.info("{}".format(e))
                led_red.on()
                led_green.off()
                led_blue.off()
                utime.sleep_ms(1000)
                led_red.off()
                utime.sleep_ms(1000)

        led_red.off()
        led_green.off()
        led_blue.off()
        self.thermal_configure()

    def thermal_fcc(self):
        self.logger.info("SYS Run FFC Normalization")
        sensor.ioctl(sensor.IOCTL_LEPTON_RUN_COMMAND, 0x0242)
        self.logger.info("RAD FFC Normalization")
        sensor.ioctl(sensor.IOCTL_LEPTON_RUN_COMMAND, 0x4E2E)

    def send_thermal_static_range(self):
        sensor.ioctl(sensor.IOCTL_LEPTON_SET_MEASUREMENT_RANGE, self.static_minimum, self.static_maximum)

    def thermal_configure(self, static_range=None):
        self.logger.info("##############################################################")
        self.logger.info("SETTINGS")
        if static_range is not None:
            self.static_range = static_range
        if self.static_range:
            sensor.ioctl(sensor.IOCTL_LEPTON_SET_MEASUREMENT_MODE, True)
            sensor.ioctl(sensor.IOCTL_LEPTON_SET_MEASUREMENT_RANGE, self.static_minimum, self.static_maximum)

        else:
            sensor.ioctl(sensor.IOCTL_LEPTON_SET_MEASUREMENT_MODE, False)
            self.logger.info("Setting: AGC Enable and Disable (Enable)")
            sensor.ioctl(sensor.IOCTL_LEPTON_SET_ATTRIBUTE, 0x0101, struct.pack("<I", 1))

            self.logger.info("Setting: RAD Radiometry Control Enable")
            sensor.ioctl(sensor.IOCTL_LEPTON_SET_ATTRIBUTE, 0x4E11, struct.pack("<I", 1))

        self.logger.info("-------------------------------------------------------------")
        self.logger.info("AGC:")
        # TODO switch modes
        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x0100, 2)
        LEP_AGC_ENABLE_TAG = struct.unpack("<I", data)[0]
        #LEP_AGC_DISABLE=0,
        #LEP_AGC_ENABLE
        self.logger.info("AGC Enable and Disable", LEP_AGC_ENABLE_TAG)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x0148, 2)
        LEP_AGC_ENABLE_TAG = struct.unpack("<I", data)[0]
        #LEP_AGC_DISABLE=0,
        #LEP_AGC_ENABLE
        self.logger.info("AGC Calculation Enable State", LEP_AGC_ENABLE_TAG)

        self.receive_gain_mode()
        self.send_gain_mode()

        #typedef struct LEP_SYS_GAIN_MODE_OBJ_T_TAG
        #{
        #FLR_SYS_GAIN_MODE_ROI_T sysGainModeROI; /* Specified ROI to use for Gain Mode switching */
        #FLR_SYS_GAIN_MODE_THRESHOLDS_T sysGainModeThresholds; /* Set of threshold triggers */
        #FLR_UINT16 sysGainRoiPopulation; /* Population size in pixels within the ROI */
        #FLR_UINT16 sysGainModeTempEnabled; /* True if T-Linear is implemented */
        #FLR_UINT16 sysGainModeFluxThresholdLowToHigh; /* calculated from desired temp */
        #FLR_UINT16 sysGainModeFluxThresholdHighToLow; /* calculated from desired temp */
        #}LEP_SYS_GAIN_MODE_OBJ_T, *LEP_SYS_GAIN_MODE_OBJ_T_PTR;

        #typedef struct LEP_SYS_GAIN_MODE_ROI_T_TAG
        #{
        #LEP_UINT16 startCol;
        #LEP_UINT16 startRow;
        #LEP_UINT16 endCol;
        #LEP_UINT16 endRow;
        #}LEP_SYS_GAIN_MODE_ROI_T, *LEP_SYS_GAIN_MODE_ROI_T_PTR;
        #/* Gain Mode Support
        #*/
        #typedef struct LEP_SYS_GAIN_MODE_THRESHOLDS_T_TAG
        #{
        #LEP_SYS_THRESHOLD_T sys_P_high_to_low; /* Range: [0 - 100], percent */
        #LEP_SYS_THRESHOLD_T sys_P_low_to_high; /* Range: [0 - 100], percent */
        #LEP_SYS_THRESHOLD_T sys_C_high_to_low; /* Range: [0 - 600], degrees C */
        #LEP_SYS_THRESHOLD_T sys_C_low_to_high; /* Range: [0 - 600], degrees C */
        #LEP_SYS_THRESHOLD_T sys_T_high_to_low; /* Range: [0 - 900], Kelvin */
        #LEP_SYS_THRESHOLD_T sys_T_low_to_high; /* Range: [0 - 900], Kelvin */
        #}LEP_SYS_GAIN_MODE_THRESHOLDS_T, *LEP_SYS_GAIN_MODE_THRESHOLDS_T_PTR;

        #0x0250

        ###############################################################
        # RADIOMETRY
        self.logger.info("-------------------------------------------------------------")
        self.logger.info("RADIOMETRY:")

        self.thermal_fcc()
        sensor.snapshot()
        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4E24, 2)
        FLR_RAD_TS_MODE_E_TAG = struct.unpack("<I", data)[0]
        #FLR_RAD_TS_USER_MODE = 0
        #FLR_RAD_TS_CAL_MODE = 1
        #FLR_RAD_TS_FIXED_MODE = 2
        #FLR_RAD_TS_END_TS_MODE = 3
        self.logger.info("RAD TShutter Mode", FLR_RAD_TS_MODE_E_TAG)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4E10, 2)
        LEP_RAD_ENABLE_E_TAG = struct.unpack("<I", data)[0]
        #LEP_RAD_DISABLE = 0,
        #LEP_RAD_ENABLE,
        self.logger.info("RAD Radiometry Control Enable", LEP_RAD_ENABLE_E_TAG)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4E28, 1)
        LEP_RAD_KELVIN_T = struct.unpack("<H", data)[0]
        self.logger.info("RAD TShutter Temperature", LEP_RAD_KELVIN_T)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4E30, 2)
        LEP_RAD_STATUS_E = struct.unpack("<I", data)[0]
        #LEP_RAD_STATUS_ERROR = -1,
        #LEP_RAD_STATUS_READY = 0,
        #LEP_RAD_STATUS_BUSY,
        #LEP_RAD_FRAME_AVERAGE_COLLECTING_FRAMES
        self.logger.info("RAD Run Status", LEP_RAD_STATUS_E)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4EC0, 2)
        LEP_RAD_ENABLE_E_TAG = struct.unpack("<I", data)[0]
        #LEP_RAD_DISABLE = 0,
        #LEP_RAD_ENABLE,
        self.logger.info("RAD T-Linear Enable State", LEP_RAD_ENABLE_E_TAG)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4EC8, 2)
        LEP_RAD_ENABLE_E_TAG = struct.unpack("<I", data)[0]
        #LEP_RAD_DISABLE = 0,
        #LEP_RAD_ENABLE,
        self.logger.info("RAD T-Linear Auto Resolution", LEP_RAD_ENABLE_E_TAG)

        startRow = 0
        startCol = 0
        endRow = sensor.height() - 1
        endCol = sensor.width() - 1
        data = struct.pack("<HHHH", startRow, startCol, endRow, endCol)
        sensor.ioctl(sensor.IOCTL_LEPTON_SET_ATTRIBUTE, 0x4ECD, data)

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4ECC, 4)
        startRow_rx, startCol_rx, endRow_rx, endCol_rx = struct.unpack("<HHHH", data)
        self.logger.info("Spotmeter {} {} {} {}".format(startRow_rx, startCol_rx, endRow_rx, endCol_rx))
        if startRow != startRow_rx or startCol != startCol_rx or endRow != endRow_rx or endCol != endCol_rx:
            raise ValueError("Spotmeter wrong window")

        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4EC4, 2)
        self.thermal_tlinear_resolution = 0.01 if struct.unpack("<I", data)[0] else 0.1
        self.logger.info("thermal_tlinear_resolution", self.thermal_tlinear_resolution)

        self.receive_flux_parameters()
        self.send_flux_parameters()
        self.logger.info("##############################################################")

    def receive_flux_parameters(self):
        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4EBC, 8)
        self.sceneEmissivity, self.TBkgK, self.tauWindow, self.TWindowK, self.tauAtm, self.TAtmK, self.reflWindow, self.TReflK = struct.unpack("<HHHHHHHH", data)
        self.logger.info(
            "RAD Flux Linear Parameters:",
            "\nsceneEmissivity", self.sceneEmissivity,
            "\nTBkgK", self.TBkgK,
            "\ntauWindow", self.tauWindow,
            "\nTWindowK", self.TWindowK,
            "\ntauAtm", self.tauAtm,
            "\nTAtmK", self.TAtmK,
            "\nreflWindow", self.reflWindow,
            "\nTReflK", self.TReflK,
        )

    def send_flux_parameters(self):
        data = struct.pack("<HHHHHHHH", self.sceneEmissivity, self.TBkgK, self.tauWindow, self.TWindowK, self.tauAtm, self.TAtmK, self.reflWindow, self.TReflK)
        sensor.ioctl(sensor.IOCTL_LEPTON_SET_ATTRIBUTE, 0x4EBD, data)
        self.receive_flux_parameters()

    @property
    def emissivity(self):
        return (self.sceneEmissivity*100.0)/8192

    @emissivity.setter
    def emissivity(self, value):
        value = min(100, max(1, value))
        self.sceneEmissivity = min(8192, max(0, round(value/100.0 * 8192)))
        self.send_flux_parameters()

    def string_gain_mode(self):
        if self.gain_mode == 0:
            return "HIGH"
        elif self.gain_mode == 1:
            return "LOW"
        elif self.gain_mode == 2:
            return "AUTO"

    def next_gain_mode(self):
        self.gain_mode += 1
        if self.gain_mode > 2:
            self.gain_mode = 0

    def send_gain_mode(self):
        data = struct.pack("<I", self.gain_mode)
        sensor.ioctl(sensor.IOCTL_LEPTON_SET_ATTRIBUTE, 0x0249, data)
        self.logger.info("Setting: SYS Gain Mode to ", self.gain_mode)
        self.receive_gain_mode()

    def receive_gain_mode(self):
        # TODO switch modes
        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x0248, 2)
        self.gain_mode = struct.unpack("<I", data)[0]
        #LEP_SYS_GAIN_MODE_HIGH = 0,
        #LEP_SYS_GAIN_MODE_LOW,
        #LEP_SYS_GAIN_MODE_AUTO,
        self.logger.info("SYS Gain Mode", self.gain_mode)

    def tlinear2celcius(self, tlinear):
        """ tlinear_to_celcius """
        return (tlinear * self.thermal_tlinear_resolution) - 273.15

    def get_spotmeter_values(self):
        data = sensor.ioctl(sensor.IOCTL_LEPTON_GET_ATTRIBUTE, 0x4ED0, 4)
        radSpotmeterValue, radSpotmeterMaxValue, radSpotmeterMinValue, radSpotmeterPopulation = struct.unpack("<HHHH", data)

        self.temperature_mean = self.tlinear2celcius(radSpotmeterValue)
        self.temperature_max = self.tlinear2celcius(radSpotmeterMaxValue)
        self.temperature_min = self.tlinear2celcius(radSpotmeterMinValue)

    def get_thermal_statistics(self):

        string = ""
        fpa_temp = sensor.ioctl(sensor.IOCTL_LEPTON_GET_FPA_TEMPERATURE)
        aux_temp = sensor.ioctl(sensor.IOCTL_LEPTON_GET_AUX_TEMPERATURE)

        string += "FPA {:.2f} AUX {:.2f}".format(fpa_temp, aux_temp)
        string += "\n {:.2f} {:.2f} {:.2f}".format(self.temperature_mean, self.temperature_max, self.temperature_min)

        return string
