# Table of Contents  

[Introduction](#introduction)  
[Hardware](#hardware)  
[Results](#results)  

<a name="introduction"/>

# Introduction

Thermal camera using 2 Openmv with fusion of Thermal and Visual images

Code for:
- Openmv H7 Thermal image as master SPI node
- Openmv H7 Plus Visual image as slave SPI node
- PIC 16F886 as auxiliar processor
- Touch screen with ILI9341 and XPT2046

<a name="hardware"/>

# Hardware

The following devices share SCLK, MISO and MOSI:

- Openmv H7 with Lepton 3.5. SPI Master.
- Openmv H7 Plus with OV7725 (The sensor that comes with H7). Reasoning:
  - OV7725 has bigger pixle size than OV5640, so OV7725 is more sensitive in dark conditions
  - OV5640 openmv driver wasn't as fast as the one for OV7725 at the time of building the project
- AuxilarProcessor. PIC 16F886 compiled with [BoostC (free compiler)](http://www.sourceboost.com/Products/BoostC/Overview.html)
  - Buttons debouncing
  - Battery voltage averaging
  - Indication LED for Input read From Master Openmv.
- ILI9341 TFT screen
- XPT2046 Touch screen

Additional Pinout
- Shared pin from AuxilarProcessor and XPT2046 to indicate to the Master that input data is ready
- command/data pin for ILI9341
- Slave Openmv busy pin, to indicate to the Master that the visual image isn't ready


Charger module TP4056. Supplier specs:
- Input interface: Type-c USB.
- Battery overcharge lifting voltage: 4.00 V
- Battery: over-current protection current 3 A
- Maximum charging current output: 1000 ma
- Light state: no load the light not bright, red light for recharging, is full of green light.

[Link used to buy it](https://www.amazon.es/gp/product/B07PKMM8Z3/ref=ppx_yo_dt_b_asin_title_o02_s00?ie=UTF8&psc=1)


![Front](/photos/cam_front.jpeg)
![Back](/photos/cam_back.jpeg)
![Inside](/photos/cam_inside.jpeg)
![Inside look at the auxiliar processor PIC 16F886](/photos/cam_inside_pic16f886.jpeg)


<a name="results"/>

# Results

![Thermal Vision indoor](/photos/Result_1_only_thermal.jpeg)
![Thermal Vision outdoor](/photos/Result_2_only_thermal.jpeg)
![Fusion Vision outdoor](/photos/Result_3_fusion_thermal_visual.jpeg)
![Fusion Vision indoor](/photos/Result_4_fusion_thermal_visual.jpeg)

# TODOs

schematics
references

