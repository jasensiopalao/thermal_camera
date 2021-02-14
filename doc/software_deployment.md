[Back to Main](../README.md)

### Table of Contents  

- [Installing the OPENMV software](#installing_openmv_software)  
- [Installing the PIC software](#installing_pic_software)
- [Debugging with OPENMV](#debugging_openmv_software)
- [Debugging with PIC](#debugging_pic_software)

<a name="installing_openmv_software"/>

# Installing the OPENMV software

Python code was tested with OPENMV firmware 3.8.0.

1. Copy components folder to both OENMVs  (master with Lepton module and slave with visual camera)
1. Copy the utils folder to both OENMVs  (master with Lepton module and slave with visual camera)
1. Copy all files in openmv_thermal to the root folder of your OPENMV with the LEPTON module. For H7 you must use an SD card.
1. Copy all files in openmv_visual to the root folder of your OPENMV with the Visual Camera module

<a name="installing_pic_software"/>

# Installing the PIC software

As for the PIC, C was used compiled with BoostC 8.01.

Load the "hex" file resulting from the compilation in the programmer tool:
* A precompiled version can be found in `src/auxiliary_controller/Debug/auxiliary_controller.hex`
* I used PICKit 2 to program the PIC

<a name="debugging_openmv_software"/>

# Debugging with OPENMV

Use the OPENMV IDE. The module files need to be present in the OPENMV file system. The main can be run directly from the PC.

<a name="debugging_pic_software"/>

# Debugging PIC

The software implements a UART on the same connector used for programming. This allows the PICKit UART to function without any cable swap between re-flashing.
