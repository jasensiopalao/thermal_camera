/*
MIT License

Copyright (c) 2021 Jonatan Asensio Palao

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

-----------------------------------------------------------------------------
BOOSTC COMPILATION

[Settings]
Target=PIC16F886
Active Compiler=BoostC

*/

const char* software_version_ = "1.1";

/////////////////////////////////////////////////////////////////
// HARDWARE INTERFACE

// RE3/MCLR/VPP
// RA0/AN0/ULPWU/C12IN0-
#define PIN_LED_RED           porta.0
// RA1/AN1/C12IN1-
#define PIN_LED_GREEN         porta.1
// RA2/AN2/VREF-/CVREF/C2IN+
#define PIN_INT_MASTER        porta.2
#define PIN_INT_MASTER_DIR    trisa.2
// RA3/AN3/VREF+/C1IN+
// RA4/T0CKI/C1OUT
// RA5/AN4/SS/C2OUT
#define PIN_SPI_SS            porta.5
#define PIN_SPI_SS_DIR        trisa.5
// VSS
// RA7/OSC1/CLKIN
#define PIN_SPI_SS_PULL_UP     porta.7
#define PIN_SPI_SS_PULL_UP_DIR trisa.7
// RA6/OSC2/CLKOUT
// RC0/T1OSO/T1CKI
// RC1/T1OSI/CCP2
// RC2/P1A/CCP1
// RC3/SCK/SCL

// RB7/ICSPDAT
#define PORT_B7_PULL_UP 0
#define UART_TX portb.7 // UART TX pin
#define UART_TX_DIR trisb.7 // UART TX pin direction register
// RB6/ICSPCLK
#define PORT_B6_PULL_UP 0
#define UART_RX portb.6 // UART RX pin
#define UART_RX_DIR trisb.6 // UART RX pin direction register
// RB5/AN13/T1G
#define PORT_B5_PULL_UP 0
#define ADC_CHANNEL_BATTERY_VOLTAGE 13
#define ADC_ACTIVE adcon0.GO
#define ADC_NOT_DONE adcon0.GO
// RB4/AN11/P1D
#define ADC_CHANNEL_BATTERY_VSS 11
#define PORT_B4_PULL_UP 0
// RB3/AN9/PGM/C12IN2-
#define PORT_B3_PULL_UP 1
#define PIN_BUTTON_SHUTTER    portb.3
// RB2/AN8/P1B
#define PORT_B2_PULL_UP 1
#define PIN_BUTTON_BOTTOM     portb.2
// RB1/AN10/P1C/C12IN3-
#define PORT_B1_PULL_UP 1
#define PIN_BUTTON_MIDDLE     portb.1
// RB0/AN12/INT
#define PORT_B0_PULL_UP 1
#define PIN_BUTTON_TOP        portb.0
// VDD
// VSS
// RC7/RX/DT
// RC6/TX/CK
// RC5/SDO
// RC4/SDI/SDA

/////////////////////////////////////////////////////////////////
// SYSTEM INCLUDES

#include <system.h>
#include <stdio.h>

/////////////////////////////////////////////////////////////////
// COMPILER CONFIGURATION 

#pragma OPTIMIZE "1"
// 0 no or very minimal optimization
// 1 regular optimization (recommended)
// a aggressive optimization
// p promotes results of some 16 bit operations to 32 bits
#pragma CLOCK_FREQ 8000000  // config clock to 8mhz. In low frequency mode 125kHz will be used and delay routines will be avoided

/////////////////////////////////////////////////////////////////
// PIC CONFIGURATION 

// Set configuration fuse: Remove any kind of reset to minimize the change that the count that defines the time gets lost
#pragma DATA _CONFIG1, _DEBUG_OFF & _INTOSCIO & _WDT_OFF & _CP_OFF & _PWRTE_OFF & _MCLRE_OFF & _FCMEN_OFF & _LVP_OFF & _BOR_OFF
#pragma DATA _CONFIG2, _WRT_OFF

/////////////////////////////////////////////////////////////////
// Utils includes

// Only for debugging
// #define UART_DISABLE_INT

// Baudrate 2400 bps
#define OneBitDelay 41  // 410 us => 41 with delay_10us
#define delay_uart delay_10us
#define DataBitCount 8 // no parity, no flow control
#define UART_BUFFER_SIZE 50
#include "uart.h"

/////////////////////////////////////////////////////////////////
// SPI DATA INTERFACE
#define MAIN_LOOP_SLEEP_MS       25
#define ITERATIONS_FOR_1_SECOND  1000/MAIN_LOOP_SLEEP_MS
#define ITERATIONS_FOR_10_SECONDS  10000/MAIN_LOOP_SLEEP_MS

#define SPI_BUFFER_SIZE          20

#define TX_BUTTON_SHUTTER        0
#define TX_BUTTON_TOP            1
#define TX_BUTTON_MIDDLE         2
#define TX_BUTTON_BOTTOM         3
#define TX_VOLTAGE_H             4
#define TX_VOLTAGE_L             5
#define TX_PIN_INT               6
#define TX_TICKS_0               7
#define TX_TICKS_1               8
#define TX_TICKS_2               9
#define TX_TICKS_3               10
#define TX_SPI_ERROR             SPI_BUFFER_SIZE - 1

////////////////////////////////////////////////////////////
// Interrupt handlers

void handle_spi_interrupt(void);
void handle_timer1_interrupt(void);
void handle_adc_interrupt(void);

////////////////////////////////////////////////////////////
// Global variables

// SPI -----------------------------------------------------

#define SPI_SCK_DIR trisc.3
#define SPI_SDI_DIR trisc.4
#define SPI_SDO_DIR trisc.5
#define SPI_SDO portc.5
#include "spi.h"

// ADC -----------------------------------------------------
#define BATTERY_VOLTAGE_SAMPLES         40

// Calibrated value of VP6 when Battery voltage is known. The value is in-line with the information
// provided by the datasheet: DC and AC Characteristics Graphs and Tables -> Typical VP6
#define VOLTAGE_FVR_VP6_MILLIVOLTS 585
#define VOLTAGE_VCC_DIODE_PIC_LOW_POWER 107
#define VOLTAGE_VCC_DIODE_PIC_HIGH_POWER 191
#define MAXIMUM_POSSIBLE_MILLIVOLTS 4500
#define LED_MINIMUM_BATTERY_MILLIVOLTS 3300
#define BOARD_VOUT_POWER_OFF_MILLIVOLTS 1500
#define ADC_STABLE_MEASUREMENT_COUNT 2
#define ADC_CHANNEL_BOARD_VOUT 13
#define ADC_CHANNEL_PIC_VREF 0xF
#define MAX_ACCEPTED_MILLIVOLTS 4500

#include "adc.h"

// TIMER ----------------------------------------------------

volatile unsigned char timer1_led_count = 0;

// Every count in
//8MHz with 8 T1 prescaler: 8 * 1/((8/4)*10^6)*2^16 = 0.262144 seconds per increment
//125kHz with 1 T1 prescaler: 1 * 1/(125000/4)*2^16 = 2.097152 but timer was incremented 8 times, so 0.262144 per increment
// #define TIMER_1_COUNT_10_SECONDS 38
//32768Hz with 1 T1 prescaler: 1/(32768)*2^16 = 2 seconds per increment
#define TIMER_1_COUNT_10_SECONDS 5
#define TIMER_1_COUNT_2_SECONDS 1

#include "utils.h"

volatile char leds_enabled = 1;
inline led_green(bit value) {
   if (!value) {
      PIN_LED_GREEN = 0;
   } else if (leds_enabled) {
      PIN_LED_GREEN = 1;
   }
}

inline led_red(bit value) {
   if (!value) {
      PIN_LED_RED = 0;
   } else if (leds_enabled) {
      PIN_LED_RED = 1;
   }
}

// IO   ----------------------------------------------------
void configure_io(void) {
   // Default config to input digital pints
   anselh = 0x00;  // Disable ADC in pins. Would also prevent errors in read-modify-write
   ansel = 0x00;
   trisa = 0xFF;
   trisb = 0xFF;
   trisc = 0xFF;
   
   // -----------------------------------------------------------------
   // DIGITAL INPUTS
   // wpub = 0xFF;    // Portb pull ups
   wpub.0 = PORT_B0_PULL_UP;
   wpub.1 = PORT_B1_PULL_UP;
   wpub.2 = PORT_B2_PULL_UP;
   wpub.3 = PORT_B3_PULL_UP;
   wpub.4 = PORT_B4_PULL_UP;
   wpub.5 = PORT_B5_PULL_UP;
   wpub.6 = PORT_B6_PULL_UP;
   wpub.7 = PORT_B7_PULL_UP;
   option_reg.NOT_RBPU = 0;
   
   // -----------------------------------------------------------------
   // DIGITAL OUTPUTS
   pcon.ULPWUE = 0;
   trisa.0 = 0;
   PIN_LED_RED = 0;
   trisa.1 = 0;
   PIN_LED_GREEN = 0;
   PIN_INT_MASTER_DIR = 0;
   PIN_INT_MASTER = 0;
   
   /*
   ccp1con.CCP1M0 = 0;
   ccp1con.CCP1M1 = 0;
   ccp1con.CCP1M2 = 0;
   ccp1con.CCP1M3 = 0;
   */
}

void process_spi_data(unsigned char package_id) {

   PIN_LED_GREEN = 0;
   unsigned char index_tx = 0;
   unsigned char index_rx = 0;
   // Already prepare the first byte of data
   write_spi( spi_tx_array[index_tx] );
   index_tx++;
   // on the first entry BF will probably still be 0 as sspbuf was just read
   do {
      if (sspstat.BF)
      {
         spi_rx_array[index_rx] = sspbuf;
         check_spi_overflow();
         if (index_rx < SPI_BUFFER_SIZE )
         {
            index_rx++;
         }
         else 
         {
            spi_set_error(SPI_ERROR_OUT_OF_INDEX);
            break;
         }
         write_spi( spi_tx_array[index_tx] );
         if (index_tx < SPI_BUFFER_SIZE)
         {
            if (package_id == 1 && index_tx == (SPI_BUFFER_SIZE - 1) ) {
               // If the rx_package_id is 1 and it finished it means that the main board received the 1 well and decided too continue
               spi_set_error(SPI_ERROR_NONE);
            }
            sspbuf = spi_tx_array[index_tx];
            index_tx++;
         }
         else
         {
            PIN_LED_GREEN = 1;
            spi_transfer_complete();
         }
      }
      handle_timer1_interrupt();
   } while (PIN_SPI_SS == 0 || sspstat.BF );
}

void handle_timer1_interrupt(void) {
   
   if(pir1.TMR1IF) {
      if (spi_tx_array[TX_TICKS_0] < 0xFF) {
         spi_tx_array[TX_TICKS_0]++;
      } else {
         spi_tx_array[TX_TICKS_0] = 0;
         if (spi_tx_array[TX_TICKS_1] < 0xFF) {
            spi_tx_array[TX_TICKS_1]++;
         } else {
            spi_tx_array[TX_TICKS_1] = 0;
            if (spi_tx_array[TX_TICKS_2] < 0xFF) {
               spi_tx_array[TX_TICKS_2]++;
            } else {
               spi_tx_array[TX_TICKS_2] = 0;
               if (spi_tx_array[TX_TICKS_3] < 0xFF) {
                  spi_tx_array[TX_TICKS_3]++;
               } else {
                  spi_tx_array[TX_TICKS_3] = 0;
               }
            }
         }
      }
      timer1_led_count++;
      pir1.TMR1IF = 0;
   }
}

void handle_spi_interrupt(void)
{
	if(pir1.SSPIF) {
      rx_package_id = sspbuf;  // Get next package count
      check_spi_overflow();
      if (rx_package_id != 0)
      {
         if (tx_package_id != rx_package_id)
         {
            spi_set_error(SPI_ERROR_PACKAGE_COUNT);
            tx_package_id = rx_package_id;
         }
      }
      else
      {
         tx_package_id = 0;
      }
      
      tx_package_id++;
      process_spi_data(rx_package_id);
      write_spi( tx_package_id );
      
      pir1.SSPIF = 0;
	}
}

void handle_adc_interrupt(void) {
   if(pir1.ADIF) {
      pir1.ADIF = 0;
      adc_measurement_count++;
      if (!is_adc_measurement_finished()) {
      // Re-measure
         ADC_ACTIVE = 1;
      }
   }
}

void interrupt(void)
{
   handle_timer1_interrupt();
   handle_spi_interrupt();
   handle_adc_interrupt();
}

inline bit check_button(char index, bit pin, bit previous_pin_valid, bit previous_pin_antibounce) {
   if (pin == previous_pin_antibounce) {
      if (pin != previous_pin_valid) {
         if (pin == 0) {  // Button pressed
            spi_tx_array[index]++;
         }
      }
      return pin;
   } else {
      return previous_pin_valid;
   }
}

void main()
{
   intcon = 0;
   pie1 = 0;
   
   // 111 = 8 MHz
   // 110 = 4 MHz (default)
   // 101 = 2 MHz
   // 100 = 1 MHz
   // 011 = 500 kHz
   // 010 = 250 kHz
   // 001 = 125 kHz
   // 000 = 31 kHz (LFINTOSC)
   set_clock_8MHZ();
   osccon.SCS = 1;  // System Clock Select bit, 1 = Internal oscillator is used for system clock
   // osccon.OSTS as 0, Device is running from the internal oscillator (HFINTOSC or LFINTOSC)
   while(!((osccon.OSTS == 0) && (osccon.HTS == 1) && (osccon.LTS == 0)));
   //osccon.LTS = 0;
   for (unsigned char i=0; i<SPI_BUFFER_SIZE; i++) {
      spi_tx_array[i] = 0;
      spi_rx_array[i] = 0;
   }
   for (unsigned char i=0; i<BATTERY_VOLTAGE_SAMPLES; i++) {
      battery_voltage_samples_h[i] = 0;
      battery_voltage_samples_l[i] = 0;
   }
   configure_io();
   init_adc();
   init_spi();
   
   // Timer1 from LP
   t1con.T1OSCEN = 1;  // LP Oscillator Enable Control bit. 1 = LP oscillator is enabled for Timer1 clock
   t1con.TMR1CS = 1;  // Timer1 Clock Source Select bit. 1 = External clock from T1CKI pin (on the rising edge)
   t1con.NOT_T1SYNC = 1;  // Timer1 External Clock Input Synchronization Control bit. 1 = Do not synchronize external clock input
   t1con.TMR1ON = 1;
   t1con.TMR1GE = 0;   // Timer1 Gate Enable bit
   t1con.T1CKPS0 = 0;  // Timer1 Input Clock Prescale Select bits to 1/1
   t1con.T1CKPS1 = 0;  // Timer1 Input Clock Prescale Select bits to 1/1
   
   pie1.TMR1IE = 1;  // Enable interrupt
   
   intcon.PEIE = 1;  // Enable peripherals interrupt
   intcon.GIE = 1;  // Enable global interrupt
   
   PIN_INT_MASTER = 1;
   for (int i=0; i<10; i++) {
      PIN_LED_GREEN = 1;
      PIN_LED_RED = 1;
      delay_ms( 150 );
      PIN_LED_GREEN = 0;
      PIN_LED_RED = 0;
      delay_ms( 150 );
   }
   
   bit button_shutter_antibounce = 0;
   bit button_top_antibounce = 0;
   bit button_middle_antibounce = 0;
   bit button_bottom_antibounce = 0;
   
   bit button_shutter_valid = 0;
   bit button_top_valid = 0;
   bit button_middle_valid = 0;
   bit button_bottom_valid = 0;
   
   unsigned char iterations_no_spi = 0;
   unsigned char rx_package_id_previous = 0;
   
   spi_tx_array[TX_TICKS_0] = 0;
   spi_tx_array[TX_TICKS_1] = 0;
   spi_tx_array[TX_TICKS_2] = 0;
   spi_tx_array[TX_TICKS_3] = 0;
   timer1_led_count = 0;
   
   unsigned char display_countdown = 0;
   bit display_timer1_timeout = 0;
   bit display_on_time = 0;
   bit low_consumption_mode_previous = 0;  // Defalt 0 so if it is
   unsigned short board_vout_low_count = 0;
   unsigned char timer1_ticks_adc_complete = 0;
   unsigned char adc_measurement_processed = 1;  // Allow measurements to start
   unsigned char timer1_led_count_previous = 0;
   for(;;)      //endless loop
   {
      ///////////////////////////////////////////////////////////////////
      // ADC RESULTS PROCESSING
      if(is_adc_measurement_finished() && !adc_measurement_processed) {
         if (adc_channel == ADC_CHANNEL_PIC_VREF) {
            process_battery_voltage();
         }
         if (adc_channel == ADC_CHANNEL_BOARD_VOUT) {
            process_board_vout();
            timer1_ticks_adc_complete = spi_tx_array[TX_TICKS_0];
         }
         adc_measurement_processed = 1;
         
         if (adc_channel == ADC_CHANNEL_PIC_VREF) {
            adc_channel_board_vout();
         } else {
            adc_channel_pic_vref();
         }
      }
      
      ///////////////////////////////////////////////////////////////////
      // LOW POWER MANAGEMENT
      // If the battery very low under no load, the leds should not be used
      if (battery_last < LED_MINIMUM_BATTERY_MILLIVOLTS && board_vout_last < BOARD_VOUT_POWER_OFF_MILLIVOLTS) {
         leds_enabled = 0;
         led_red(0);
         led_green(0);
      } else {
         leds_enabled = 1;
      }
      
      bit board_vout_low = (board_vout_last < BOARD_VOUT_POWER_OFF_MILLIVOLTS) ? 1 : 0;
      if (board_vout_low) {
         if (board_vout_low_count < 0xFFFF) {
            board_vout_low_count++;
         }
      } else {
         board_vout_low_count = 0;
      }
      
      bit low_consumption_mode = (board_vout_low_count > ITERATIONS_FOR_10_SECONDS) ? 1 : 0;
      bit low_consumption_mode_changed = low_consumption_mode_previous != low_consumption_mode ? 1 : 0 ;
      low_consumption_mode_previous = low_consumption_mode;
      
      if (UART_RX) {
         InitSoftUART();
         UART_Send_String(low_consumption_mode ? "OFF" : "ON");
      } else {
         DeinitSoftUART();
      }
      
      if ( low_consumption_mode_changed ) {
         led_red(0);
         led_green(0);
         if (low_consumption_mode) {
            led_red(1);
            delay_ms(250);
            led_red(0);
            delay_ms(250);
            led_red(1);
            delay_ms(250);
            
            UART_Send_String("Entering low power mode");
            UART_New_Line();
            deinit_spi();
            SPI_SDO_DIR = 1;  // Input
            PIN_INT_MASTER_DIR = 1;  // Input
            PIN_LED_GREEN = 0;
            led_red(0);
         } else {            
            for(int i=0; i<10; i++) {
               led_red(0);
               delay_ms(50);
               led_red(1);
               delay_ms(50);
            }
            iterations_no_spi = 0;
            UART_New_Line();
            UART_New_Line();
            UART_Send_String("##############################");
            UART_New_Line();
            UART_Send_String("Active mode");
            UART_Send_String(software_version_);
            UART_New_Line();
            init_spi();
            PIN_INT_MASTER_DIR = 0;  // Output
            PIN_INT_MASTER = 1;
            led_red(0);
            
         }
      }
      
      ///////////////////////////////////////////////////////////////////
      // ADC NEXT TRIGGER
      
      if (adc_measurement_processed && ((timer1_ticks_adc_complete != spi_tx_array[TX_TICKS_0]))) {
         adc_start_measurement();
         adc_measurement_processed = 0;
      }
      
      ///////////////////////////////////////////////////////////////////
      // TIME TICK
      
      if(timer1_led_count_previous != timer1_led_count) {
         if (display_countdown > 0) {
            display_countdown--;
         }
      
         if (display_timer1_timeout) {
            // When this debug mode is on, always make led blink and also
            // wait some time in LED off
            led_red(1);
            delay_ms(10);
            led_red(0);
            delay_ms(20);
         }
      }
         
      if (low_consumption_mode && !display_timer1_timeout && timer1_led_count >= TIMER_1_COUNT_10_SECONDS) {
         // Only signal when camera is off but not waiting in led off to save battery
         timer1_led_count = 0;
         PIN_LED_RED = 1;
         delay_ms(10);
         PIN_LED_RED = 0;
      }
      
      timer1_led_count_previous = timer1_led_count;
      ///////////////////////////////////////////////////////////////////
      // TASKS
      
      
      if (low_consumption_mode ) {
         led_red((UART_RX || !PIN_BUTTON_SHUTTER) ? 1 : 0);
         if (!PIN_BUTTON_TOP) {
            display_countdown = 120;
            display_timer1_timeout = 1;
         }
         if (!PIN_BUTTON_MIDDLE) {
            display_countdown = 120;
            display_on_time = 1;
         }
         if (!PIN_BUTTON_BOTTOM || display_countdown == 0) {
            display_countdown = 0;
            display_on_time = 0;
            display_timer1_timeout = 0;
         }
      } else {
         // When uart unused SPI errors will be cleared on each cycle
         led_red(UART_RX ? 1 : 0);
         
         bit button_shutter = PIN_BUTTON_SHUTTER;
         bit button_top = PIN_BUTTON_TOP;
         bit button_middle = PIN_BUTTON_MIDDLE;
         bit button_bottom = PIN_BUTTON_BOTTOM;
         
         button_shutter_valid = check_button(TX_BUTTON_SHUTTER, button_shutter, button_shutter_valid, button_shutter_antibounce );
         button_top_valid =     check_button(TX_BUTTON_TOP,     button_top,     button_top_valid,     button_top_antibounce );
         button_middle_valid =  check_button(TX_BUTTON_MIDDLE,  button_middle,  button_middle_valid,  button_middle_antibounce );
         button_bottom_valid =  check_button(TX_BUTTON_BOTTOM,  button_bottom,  button_bottom_valid,  button_bottom_antibounce );
         
         unsigned char total_presses = 0;
         total_presses += spi_tx_array[TX_BUTTON_SHUTTER];
         total_presses += spi_tx_array[TX_BUTTON_TOP];
         total_presses += spi_tx_array[TX_BUTTON_MIDDLE];
         total_presses += spi_tx_array[TX_BUTTON_BOTTOM];
         
         PIN_INT_MASTER = total_presses ? 0 : 1;
         spi_tx_array[TX_PIN_INT] = total_presses;
         
         button_shutter_antibounce = button_shutter;
         button_top_antibounce = button_top;
         button_middle_antibounce = button_middle;
         button_bottom_antibounce = button_bottom;
         
         ///////////////////////////////////////////////////////////////////
         // SPI ACTIVITY INDICATIONS
         bit spi_no_transferred = (rx_package_id == rx_package_id_previous) ? 1 : 0;
         rx_package_id_previous = rx_package_id;
         
         if (spi_no_transferred) {
            if (iterations_no_spi < 0xFF) {
               iterations_no_spi++;
            }
         } else {
            iterations_no_spi = 0;
         }
         
         if (iterations_no_spi > ITERATIONS_FOR_1_SECOND) {
            PIN_LED_GREEN = 0;
         }
         
      }
      ///////////////////////////////////////////////////////////////////
      // PRINTS
      
      if (UART_RX) {
         sprintf(uart_tx_array, "batt %u", battery_last);
         UART_Send_String(uart_tx_array);
         sprintf(uart_tx_array, "(agv %u)", battery_average);
         UART_Send_String(uart_tx_array);
         sprintf(uart_tx_array, "3V3 %u", board_vout_last);
         UART_Send_String(uart_tx_array);
         UART_Send_String("STMB");
         sprintf(uart_tx_array, "%u", spi_tx_array[TX_BUTTON_SHUTTER]);
         UART_Send_String(uart_tx_array);
         sprintf(uart_tx_array, "%u", spi_tx_array[TX_BUTTON_TOP]);
         UART_Send_String(uart_tx_array);
         sprintf(uart_tx_array, "%u", spi_tx_array[TX_BUTTON_MIDDLE]);
         UART_Send_String(uart_tx_array);
         sprintf(uart_tx_array, "%u", spi_tx_array[TX_BUTTON_BOTTOM]);
         UART_Send_String(uart_tx_array);
         UART_Send_String(" ");
         
         sprintf(uart_tx_array, "%u", PIN_BUTTON_SHUTTER);
         UART_Send_String(uart_tx_array);
         sprintf(uart_tx_array, "%u", PIN_BUTTON_TOP);
         UART_Send_String(uart_tx_array);
         sprintf(uart_tx_array, "%u", PIN_BUTTON_MIDDLE);
         UART_Send_String(uart_tx_array);
         sprintf(uart_tx_array, "%u", PIN_BUTTON_BOTTOM);
         UART_Send_String(uart_tx_array);
         UART_Send_String(" ");
         if (display_timer1_timeout) {
            UART_Send_String("2s");
         } else {
            UART_Send_String("10s");
         }
         
         unsigned long clock_ticks = spi_tx_array[TX_TICKS_0];
         clock_ticks |= ((unsigned long)(spi_tx_array[TX_TICKS_1]) << 8);
         clock_ticks |= ((unsigned long)(spi_tx_array[TX_TICKS_2]) << 16);
         clock_ticks |= ((unsigned long)(spi_tx_array[TX_TICKS_3]) << 24);
         sprintf32(uart_tx_array, "ticks %l", clock_ticks);
         UART_Send_String(uart_tx_array);
         
         UART_New_Line();
      }
      
      ///////////////////////////////////////////////////////////////////
      // LOOP DELAY
      
      if (low_consumption_mode) {
         if(is_adc_measurement_finished() && !adc_measurement_processed) {
            continue;
         }
         led_green(0);
         sleep();
         led_green(display_on_time);
      } else {
         if(!UART_RX) { 
            delay_ms( MAIN_LOOP_SLEEP_MS );
         }
      }
   }
}
