[Back to Main](../README.md)

### Table of Contents  

- [Folder structure](#software_tooling)  
- [# Master OPENMV (openmv_thermal) python class instances](#openmv_master)

<a name="software_tooling"/>

# Folder structure

* __auxiliary_controller:__ BoostC Project in C with the firmware for the PIC16F886. Implemented Interrupts Timer1 (RTC), SPI, ADC (Battery Voltage). The python SPI API for this MCU is in `components/auxiliary_controller.py`
* __components:__ Devices interfaces. At the moment it describes SPI interfaces, mostly used from the master side.
* __openmv_thermal:__ Files to be places at the root of the file system of the OPENMV master (with the Letpon module)
    * __helpers:__ Utility functions or clases that depend on object instances from the main.py
* __openmv_visual:__ Files to be places at the root of the file system of the OPENMV master (with the Letpon module)
* __utils:__ Utility functions or clases that are independent and can be re-used.

<a name="openmv_master"/>

# Master OPENMV (openmv_thermal) python class instances

The master OPENMV implements in python the following class instances:

* auxiliary_controller: Fetches all the data from the PIC16F886. Battery voltage, Real time clock counter, button press info.
* touch. Interface with XPT2046. It handles the calibration of the touch screen.
* control. Stores most of the camera variables and manages the images from SD
* thermal. Interface the Lepton 3.5
* menu: Contains a dictionary with all the information about the menus to be displayed when each key is pressed
* screen: Interface with ILI9341
* settings: User settings
* time_settings: It stores the datetime and the RTC count at the time of the time-set. This allows the OPENMV to know the absolute time when it boots. Additionally there is a calibration factor which can be used to get higher accuracy.
* input_handler: Pipes the interrupt through the appropiate callbacks, so the final callback has all the class instances required and 
* camera_slave: Buffers and manages the data transfer of the visual camera image via SPI
* logger: Temporary placeholder with an info method. TODO to set a proper logger

