# Thermal Camera & Visual Image Fusion by [Jonatan Asensio Palao](https://es.linkedin.com/in/jonatan-asensio-palao-369a4143)

### Table of Contents  

[Introduction](#introduction)  
[Electronic design](#electronic_design)  
[Results](#results)  

<p align="center">
<img width="320" height="240" src="photos/Result_1_only_thermal.jpeg">
</p>

<a name="introduction"/>

## Introduction

This project details the software and hardware to build a portable thermal camera with visual image fusion.

- Openmv H7 Thermal image as master SPI node
- Openmv H7 Plus Visual image as slave SPI node
- PIC 16F886 as auxiliar processor (RTC, buttons, battery measurement)
- 2.8" Touch screen with ILI9341 and XPT2046 with 



![Front](photos/cam_front.jpeg)
![Back](photos/cam_back.jpeg)

<a name="electronic_design"/>

## Electronic design

![](schematics/thermal_camera_version_1_0.gif)

See: [Design decisions involved in version 1](doc/architecture_design_record_001.md)

[More info for version 1]: doc/architecture_design_record_001.md	"Design decisions involved in version 1"

<a name="results"/>

## Hardware mounting

![Inside](photos/cam_inside_assembled.jpeg)
![Inside look at the auxiliar processor PIC 16F886](photos/cam_inside_disassembled.jpeg)

Mounting of Lepton 3.5 See: [Design decisions involved in version 1](doc/lepton_mounting.md)

## Results


![Thermal Vision outdoor](photos/Result_2_only_thermal.jpeg)
![Fusion Vision outdoor](photos/Result_3_fusion_thermal_visual.jpeg)
![Fusion Vision indoor](photos/Result_4_fusion_thermal_visual.jpeg)

