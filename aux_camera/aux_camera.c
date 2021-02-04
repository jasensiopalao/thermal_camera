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

#include <system.h>
#include <stdio.h>
//#include <rs232_driver.h>
#pragma OPTIMIZE "2"
// 0 no or very minimal optimization
// 1 regular optimization (recommended)
// a aggressive optimization
// p promotes results of some 16 bit operations to 32 bits
const char* software_version_ = "1.0";

#pragma CLOCK_FREQ 8000000  // config clock to 8mhz. In low frequency mode 125kHz will be used and delay routines will be avoided
// Set configuration fuse: Remove any kind of reset to minimize the change that the count that defines the time gets lost
#pragma DATA _CONFIG1, _DEBUG_OFF & _INTOSCIO & _WDT_OFF & _CP_OFF & _PWRTE_OFF & _MCLRE_OFF & _FCMEN_OFF & _LVP_OFF & _BOR_OFF
#pragma DATA _CONFIG2, _WRT_OFF

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


volatile unsigned char spi_tx_size = SPI_BUFFER_SIZE;  // spi_rx_size is just local
volatile unsigned char spi_tx_array[SPI_BUFFER_SIZE];
volatile unsigned char spi_rx_array[SPI_BUFFER_SIZE];

#define BATTERY_VOLTAGE_SAMPLES         40
volatile unsigned char battery_voltage_sample = 0;
volatile unsigned char battery_voltage_samples = 0;
// Split array because:
//  - Arrays of shorts seem to not get the memory size allocated well according to the type, it seems to only count on char
//  - Also arrays must fit in one signle page
volatile unsigned char battery_voltage_samples_h[BATTERY_VOLTAGE_SAMPLES];
volatile unsigned char battery_voltage_samples_l[BATTERY_VOLTAGE_SAMPLES];



#define UART_BUFFER_SIZE 50

volatile char uart_tx_array[UART_BUFFER_SIZE];

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
// VSS
// RA7/OSC1/CLKIN
// RA6/OSC2/CLKOUT
// RC0/T1OSO/T1CKI
// RC1/T1OSI/CCP2
// RC2/P1A/CCP1
// RC3/SCK/SCL

// RB7/ICSPDAT
// RB6/ICSPCLK
// RB5/AN13/T1G
#define ADC_CHANNEL_BATTERY_VOLTAGE 13
#define BOARD_VOUT_POWER_OFF_MILLIVOLTS 1500
#define ADC_ACTIVE adcon0.GO
// RB4/AN11/P1D
// RB3/AN9/PGM/C12IN2-
#define PIN_BUTTON_SHUTTER    portb.3
// RB2/AN8/P1B
#define PIN_BUTTON_BOTTOM     portb.2
// RB1/AN10/P1C/C12IN3-
#define PIN_BUTTON_MIDDLE     portb.1
// RB0/AN12/INT
#define PIN_BUTTON_TOP        portb.0
// VDD
// VSS
// RC7/RX/DT
// RC6/TX/CK
// RC5/SDO
// RC4/SDI/SDA
volatile unsigned short battery_average = 0;
volatile unsigned long battery_last = 0;
volatile unsigned long board_vout_last = 0;

volatile unsigned long max_adc_x_vref = (0x000003FF) * 585;  //  FVR is 0.6 V, 585

volatile char adc_channel = 0;
#define ADC_CHANNEL_BOARD_VOUT 13
#define ADC_CHANNEL_PIC_VREF 0xF

inline void adc_channel_board_vout() {
   adc_channel = ADC_CHANNEL_BOARD_VOUT;
   // 1101 = AN13
   adcon0.CHS3 = 1;
   adcon0.CHS2 = 1;
   adcon0.CHS1 = 0;
   adcon0.CHS0 = 1;
}

inline void adc_channel_pic_vref() {
   adc_channel = ADC_CHANNEL_PIC_VREF;
   // 1111 = Fixed Ref
   adcon0.CHS3 = 1;
   adcon0.CHS2 = 1;
   adcon0.CHS1 = 1;
   adcon0.CHS0 = 1;
}

void init_adc() {

   // -----------------------------------------------------------------
   // ADC
   
   // 10 = FOSC/32
   // adcon0.ADCS1 = 1;
   // adcon0.ADCS0 = 0;
   
   // FRC (clock derived from a dedicated internal oscillator = 500 kHz max)
   adcon0.ADCS1 = 1;
   adcon0.ADCS0 = 1;
   
   // 1101 = AN13
   adc_channel_pic_vref();
   adcon0.GO = 0; // No conversion ongoing. Alias NOT_DONE, GO_DONE
   adcon0.ADON = 1;

   adcon1.ADFM = 1;  // 1 = Right justified
   adcon1.VCFG1 = 0;  // Reference 0 = VSS
   adcon1.VCFG0 = 0;  // Reference 0 = VDD
   
   anselh.5 = 1;  // RB5/AN13 as ADC
   trisb.5 = 1;
   
   adcon0.GO = 0;
   pir1.ADIF = 0;
   // pie1.ADIE = 1;  // To enable the interrupt
}


inline void process_board_vout(void) {
   // adc -- v_out
   // 0x3FF -- battery_last
   
   unsigned short adc_measurement = (adresh << 8) | adresl;
   board_vout_last = ((unsigned long)adc_measurement * (unsigned long)battery_last ) / 0x3FF;
   
   
}

inline void process_battery_voltage(void) {
   
   // adc -- 0.6
   // 0x3FF -- battery
   
   unsigned short adc_measurement = (adresh << 8) | adresl;
   battery_last = max_adc_x_vref / adc_measurement;
   
   battery_voltage_samples_h[battery_voltage_sample] = (unsigned char)(battery_last >> 8);
   battery_voltage_samples_l[battery_voltage_sample] = (unsigned char)(battery_last);
   battery_voltage_sample++;
   if (battery_voltage_sample >= BATTERY_VOLTAGE_SAMPLES) {
      battery_voltage_sample = 0;
   }
   if (battery_voltage_samples < BATTERY_VOLTAGE_SAMPLES) {
      battery_voltage_samples++;
   }
   
   // Perform average   
   unsigned long battery_sum = 0;
   for (unsigned int i=0; i<battery_voltage_samples; i++) {
      battery_sum += ((battery_voltage_samples_h[i] << 8) | battery_voltage_samples_l[i]);
   }
   battery_average = battery_sum / battery_voltage_samples;
   
   bit spi_enabled = pie1.SSPIE;
   pie1.SSPIE = 0;
   spi_tx_array[TX_VOLTAGE_H] = (unsigned char)(battery_average >> 8);
   spi_tx_array[TX_VOLTAGE_L] = (unsigned char)(battery_average);
   pie1.SSPIE = spi_enabled;
}


volatile char dividend_8MHZ_by_clock = 0;   

inline void set_clock_125KHZ(void) {
   osccon.IRCF2 = 0;
   osccon.IRCF1 = 0;
   osccon.IRCF0 = 1;
   dividend_8MHZ_by_clock = 8;  // It would be 64 but by removing the pre-scaler we do 64/8
   
   // Timer1 Input Clock Prescale Select bits to 1/8
   t1con.T1CKPS0 = 0;
   t1con.T1CKPS1 = 0;
}

inline void set_clock_500KHZ(void) {
   osccon.IRCF2 = 0;
   osccon.IRCF1 = 1;
   osccon.IRCF0 = 1;
   dividend_8MHZ_by_clock = 16;
   
   // Timer1 Input Clock Prescale Select bits to 1/8
   t1con.T1CKPS0 = 1;
   t1con.T1CKPS1 = 1;
}

inline void set_clock_8MHZ(void) {
   osccon.IRCF2 = 1;
   osccon.IRCF1 = 1;
   osccon.IRCF0 = 1;
   dividend_8MHZ_by_clock = 1;
   
   // Timer1 Input Clock Prescale Select bits to 1/8
   t1con.T1CKPS0 = 1;
   t1con.T1CKPS1 = 1;
}

void configure_io(void) {
   // Default config to input digital pints
   anselh = 0x00;  // Disable ADC in pins. Would also prevent errors in read-modify-write
   ansel = 0x00;
   trisa = 0xFF;
   trisb = 0xFF;
   trisc = 0xFF;
   
   // -----------------------------------------------------------------
   // DIGITAL INPUTS
   wpub = 0xFF;    // Portb pull ups
   wpub.6 = 0;
   option_reg.NOT_RBPU = 0;
   
   // -----------------------------------------------------------------
   // DIGITAL OUTPUTS
   pcon.ULPWUE = 0;
   trisa.0 = 0;
   trisa.1 = 0;
   PIN_INT_MASTER_DIR = 0;
}

enum SpiError {
   SPI_ERROR_UNDEFINED = 0,
   SPI_ERROR_NONE = (1<<0),
   SPI_ERROR_OVERFLOW = (1<<1),
   SPI_ERROR_OVERWRITE = (1<<2),
   SPI_ERROR_OUT_OF_INDEX = (1<<3),
   SPI_ERROR_PACKAGE_COUNT = (1<<4)
};

inline void spi_set_error(enum SpiError spi_error)
{   
   if (spi_error == SPI_ERROR_NONE) {
      spi_tx_array[TX_SPI_ERROR] = SPI_ERROR_NONE;
   } else {
      spi_tx_array[TX_SPI_ERROR] |= spi_error;
      PIN_LED_RED = 1;
   }
}

inline void check_spi_overflow()
{
   if(sspcon.SSPOV)
   {
      sspcon.SSPOV = 0;
      spi_set_error(SPI_ERROR_OVERFLOW);
   }
}
inline void write_spi(char tx_value)
{
   do
   {
      sspcon.WCOL = 0;
      sspbuf = tx_value;
   } while (sspcon.WCOL && PIN_SPI_SS == 0);
   if(sspcon.WCOL)
   {
      spi_set_error(SPI_ERROR_OVERWRITE);
   }
}

enum SpiError spi_error = SPI_ERROR_NONE;

#define SPI_SCK_DIR trisc.3
#define SPI_SDI_DIR trisc.4
#define SPI_SDO_DIR trisc.5
#define SPI_SDO portc.5
inline void deinit_spi(void) {
   pie1.SSPIE = 0;  // Disable SPI interrupt
   sspcon.SSPEN= 0; // Disable module
}

inline void init_spi(void) {
   char dummy;
   // Serial Data Out (SDO) – RC5/SDO
   // Serial Data In (SDI) – RC4/SDI/SDA
   // Serial Clock (SCK) – RC3/SCK/SCL
   // Slave Select (SS) – RA5/SS/AN4

   deinit_spi();
   
   dummy = sspbuf;
   
   write_spi(0xF0);
   
   sspstat.SMP = 0;  // SMP must be cleared when SPI is used in Slave mode
   sspstat.CKE = 1; // SPI Clock Edge Select bit. CKP = 1, 1 = Data transmitted on falling edge of SCK
   sspstat.BF = 0;  // Buffer Full Status bit.  Receive complete, SSPBUF is full
   
   sspcon.WCOL = 0;  // The SSPBUF register is written while it is still transmitting the previous word (must be cleared in software)
   sspcon.SSPOV = 0;  // Receive Overflow Indicator bit
   sspcon.SSPEN= 1;  // Synchronous Serial Port Enable bit
   sspcon.CKP = 1;  // Clock Polarity Select bit
   // SSPM<3:0> Synchronous Serial Port Mode Select bits: 0100 = SPI Slave mode, clock = SCK pin, SS pin control enabled
   sspcon.SSPM3 = 0;
   sspcon.SSPM2 = 1;
   sspcon.SSPM1 = 0;
   sspcon.SSPM0 = 0;
   
   trisa.5 = 1;  // RA5/AN4 as input
   ansel.4 = 0;  // RA5/AN4 Enable SS by disabling the analog reading
   SPI_SDO_DIR = 0;  // RC5/SDO as output
   SPI_SDI_DIR = 1;  // RC4/SDI as input
   SPI_SCK_DIR = 1;  // RC3/SCK as input
   pir1.SSPIF = 0;
   pie1.SSPIE = 1;  // Enable SPI interrupt
   
   spi_set_error(SPI_ERROR_NONE);
}

inline void spi_transfer_complete(void) {
   spi_tx_array[TX_BUTTON_SHUTTER] = 0;
   spi_tx_array[TX_BUTTON_TOP] = 0;
   spi_tx_array[TX_BUTTON_MIDDLE] = 0;
   spi_tx_array[TX_BUTTON_BOTTOM] = 0;
   PIN_INT_MASTER = 1;  // Idle
}

inline void process_spi_data(unsigned char package_id) {

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
      // Wait for the in the most restrictive case:
      // Master indicated a size to send to slave and data not received yet
      //   Useful if the master isn't using the SS line as data blocks
      // Master already sent the next data
      // Alternative if index_rx < spi_rx_size
      // Master didn't put the ss pin high (not indicated as finished and probably sending data in one block)
      //   Useful if the master isn't using the sizes to indicate data blocks
      // So for the slave to transmit all data. There are two options:
      //   - The master needs keep the SS low as long as it didn't transfer the X bytes indicates by the first byte received
      //   - The master first byte (indicating the master-tx size) needs to indicate SPI_BUFFER_SIZE (max size, so wrost case)
   } while (PIN_SPI_SS == 0 || sspstat.BF );
}

// send           receive
// package_count  package_count
// tx[index]      data for rx[index]

volatile unsigned char tx_package_id = 0;
volatile unsigned char rx_package_id = 0;

inline void spi_interrupt(void)
{
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
}

volatile unsigned char low_frequency=0;
volatile unsigned char desired_low_frequency=0;

volatile unsigned short timer1_count = 0;
void interrupt(void)
{
	if(pir1.SSPIF) {
      //test_spi();
      spi_interrupt();
      pir1.SSPIF = 0;
	}
   if(pir1.TMR1IF) {
      char cached_dividend_8MHZ_by_clock = dividend_8MHZ_by_clock;
      
      // If desired, change the frequency as soon as possible to prevent that counts are misinterpreted
      if (low_frequency != desired_low_frequency) {
         low_frequency = desired_low_frequency;
         if (low_frequency) {
            set_clock_125KHZ();
         } else {
            set_clock_8MHZ();
         }
      }
      
      for (char increments=0; increments<cached_dividend_8MHZ_by_clock; increments++) {
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
         timer1_count++;
      }
      pir1.TMR1IF = 0;
   }
   if(pir1.ADIF) {
      pir1.ADIF = 0;
      pie1.ADIE = 0;
      // Re-measure
      ADC_ACTIVE = 1;
   }
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

// https://www.microchip.com/forums/m926980.aspx

#define Baudrate 1200 //bps
// #define OneBitDelay (1000000/Baudrate)
// 1200 82
// 2400 41
#define OneBitDelay 41
#define delay_uart delay_10us
#define DataBitCount 8 // no parity, no flow control
#define UART_RX portb.6 // UART RX pin
#define UART_TX portb.7 // UART TX pin
#define UART_RX_DIR trisb.6 // UART RX pin direction register
#define UART_TX_DIR trisb.7 // UART TX pin direction register

//Function Declarations
void InitSoftUART(void);
unsigned char UART_Receive(void);
void UART_Transmit(const char);

void UART_Send_String(const char * send_uart);
void UART_New_Line();

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
   InitSoftUART();
   
   t1con.TMR1CS = 0;
   t1con.T1SYNC = 1;
   t1con.TMR1ON = 1;
   t1con.TMR1GE = 0;  // Timer1 Gate Enable bit
   
   pie1.TMR1IE = 1;  // Enable interrupt
   
   intcon.PEIE = 1;  // Enable peripherals interrupt
   intcon.GIE = 1;  // Enable global interrupt
   
   PIN_INT_MASTER = 1;
   PIN_LED_GREEN = 1;
   PIN_LED_RED = 1;
   delay_ms( 250 );
   PIN_LED_GREEN = 0;
   PIN_LED_RED = 0;
   delay_ms( 250 );
   ADC_ACTIVE = 1;
   
   bit button_shutter_antibounce = 0;
   bit button_top_antibounce = 0;
   bit button_middle_antibounce = 0;
   bit button_bottom_antibounce = 0;
   
   bit button_shutter_valid = 0;
   bit button_top_valid = 0;
   bit button_middle_valid = 0;
   bit button_bottom_valid = 0;
   
   volatile unsigned char iterations_no_spi = 0;
   volatile unsigned char rx_package_id_previous = 0;
   
   spi_tx_array[TX_TICKS_0] = 0;
   spi_tx_array[TX_TICKS_1] = 0;
   spi_tx_array[TX_TICKS_2] = 0;
   spi_tx_array[TX_TICKS_3] = 0;
   timer1_count = 0;
   
   // TEST
   
   trisc.2 = 0;
   portc.2 = 0;
   delay_ms( 250 );
   delay_ms( 250 );
   delay_ms( 250 );
   delay_ms( 250 );
   
   bit low_consumption_mode_previous = 0;  // Defalt 0 so if it is
   unsigned short board_vout_low_count = 0;
   for(;;)      //endless loop
   {
      bit board_vout_low = (board_vout_last < BOARD_VOUT_POWER_OFF_MILLIVOLTS) ? 1 : 0;
      if (board_vout_low) {
         if (board_vout_low_count < 0xFFFF) {
            board_vout_low_count++;
         }
      } else {
         board_vout_low_count = 0;
      }
      
      bit low_consumption_mode = ((board_vout_low_count > ITERATIONS_FOR_10_SECONDS) && !UART_RX) ? 1 : 0;
      bit low_consumption_mode_changed = low_consumption_mode_previous != low_consumption_mode ? 1 : 0 ;
      low_consumption_mode_previous = low_consumption_mode;
      
      if ( low_consumption_mode_changed ) {
         if (low_consumption_mode) {
            PIN_LED_RED = 1;
            delay_ms(250);
            PIN_LED_RED = 0;
            delay_ms(250);
            PIN_LED_RED = 1;
            delay_ms(250);
            
            UART_Send_String("Entering low power mode");
            UART_New_Line();
            deinit_spi();
            SPI_SDO_DIR = 1;  // Input
            PIN_INT_MASTER_DIR = 1;  // Input
            PIN_LED_GREEN = 0;
            PIN_LED_RED = 0;
            
            desired_low_frequency = 1;
            while(low_frequency != 1);
            
            PIN_LED_RED = 0;
         } else {
            desired_low_frequency = 0;
            while(low_frequency != 0);
            
            for(int i=0; i<10; i++) {
               PIN_LED_RED = 0;
               delay_ms(50);
               PIN_LED_RED = 1;
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
            PIN_LED_RED = 0;
            
         }
      }
      
      ///////////////////////////////////////////////////////////////////
      // TASKS
      if (low_consumption_mode ) {
         PIN_LED_RED = !PIN_BUTTON_SHUTTER;
         // 0.000001 262140
         // 50ms
         // 10/0,262140 = 38
         // 60/0,065535 ~ 228
         if (timer1_count > 38) {
            timer1_count = 0;
            PIN_LED_RED = 1;
            //delay_ms(10);
            delay_10us(15);  // delay_ms(10); / (8000000/125000) / 10
            PIN_LED_RED = 0;
         }
         
      } else {
         // When uart unused SPI errors will be cleared on each cycle
         PIN_LED_RED = UART_RX;
         
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
         ///////////////////////////////////////////////////////////////////
         // PRINTS
         
         if (UART_RX) {
            sprintf(uart_tx_array, "batt %d", (unsigned int)battery_last);
            UART_Send_String(uart_tx_array);
            sprintf(uart_tx_array, "(agv %d)", (unsigned int)battery_average);
            UART_Send_String(uart_tx_array);
            sprintf(uart_tx_array, "vout_3V3 %d", (unsigned int)board_vout_last);
            UART_Send_String(uart_tx_array);
            sprintf(uart_tx_array, "shutter %d", (unsigned int)spi_tx_array[TX_BUTTON_SHUTTER]);
            UART_Send_String(uart_tx_array);
            sprintf(uart_tx_array, "top %d", spi_tx_array[TX_BUTTON_TOP]);
            UART_Send_String(uart_tx_array);
            sprintf(uart_tx_array, "mid %d", spi_tx_array[TX_BUTTON_MIDDLE]);
            UART_Send_String(uart_tx_array);
            sprintf(uart_tx_array, "bot %d", spi_tx_array[TX_BUTTON_BOTTOM]);
            UART_Send_String(uart_tx_array);
            
            unsigned long clock_ticks = spi_tx_array[TX_TICKS_0];
            clock_ticks |= ((unsigned long)(spi_tx_array[TX_TICKS_1]) << 8);
            clock_ticks |= ((unsigned long)(spi_tx_array[TX_TICKS_2]) << 16);
            clock_ticks |= ((unsigned long)(spi_tx_array[TX_TICKS_3]) << 24);
            sprintf32(uart_tx_array, "ticks %l", clock_ticks);
            UART_Send_String(uart_tx_array);
            
            UART_New_Line();
         }
      }
      ///////////////////////////////////////////////////////////////////
      // ADC CONVERTIONS
      if(pir1.ADIF && !pie1.ADIE) {
         pir1.ADIF = 0;
         if (adc_channel == ADC_CHANNEL_PIC_VREF) {
            process_battery_voltage();
         }
         if (adc_channel == ADC_CHANNEL_BOARD_VOUT) {
            process_board_vout();
         }
         
         if (adc_channel == ADC_CHANNEL_PIC_VREF) {
            adc_channel_board_vout();
         } else {
            adc_channel_pic_vref();
         }
         
         pie1.ADIE = 1;
         ADC_ACTIVE = 1;
      }
      
      ///////////////////////////////////////////////////////////////////
      // LOOP DELAY AND ADC MEASUREMENT START
      if (!low_consumption_mode) {
         delay_ms( MAIN_LOOP_SLEEP_MS );
      }
   }
}




void InitSoftUART(void) // Initialize UART pins to proper values
{
 UART_TX = 1; // TX pin is high in idle state
 
 UART_RX_DIR = 1; // Input
 UART_TX_DIR = 0; // Output
}

unsigned char UART_Receive(void)
{
 // Pin Configurations
    // GP1 is UART RX Pin

 unsigned char DataValue = 0;

 //wait for start bit
 while(UART_RX==1);

 delay_uart(OneBitDelay);
 delay_uart(OneBitDelay/2); // Take sample value in the mid of bit duration

 for ( unsigned char i = 0; i < DataBitCount; i++ )
 {
  if ( UART_RX == 1 ) //if received bit is high
  {
   DataValue += (1<<i);
  }

  delay_uart(OneBitDelay);
 }

 // Check for stop bit
 if ( UART_RX == 1 ) //Stop bit should be high
 {
  delay_uart(OneBitDelay/2);
  return DataValue;
 }
 else //some error occurred !
 {
  delay_uart(OneBitDelay/2);
  return 0x000;
 }
}


void UART_Send_String(const char * send_uart)
{
   for(char index=0; index < UART_BUFFER_SIZE; index++) {
      if (send_uart[index] == 0) {
         UART_Transmit(' ');
         break;
      }
      UART_Transmit(send_uart[index]);
   }
}

void UART_New_Line()
{
   UART_Transmit('\r');
   UART_Transmit('\n');
}

void UART_Transmit(const char DataValue)
{
 /* Basic Logic
    
    TX pin is usually high. A high to low bit is the starting bit and 
    a low to high bit is the ending bit. No parity bit. No flow control.
    BitCount is the number of bits to transmit. Data is transmitted LSB first.

 */

 //bit intcon_GIE = intcon.GIE;
 //intcon.GIE = 0;
 // Send Start Bit
 UART_TX = 0;
 delay_uart(OneBitDelay);

 for ( unsigned char i = 0; i < DataBitCount; i++ )
 {
  //Set Data pin according to the DataValue
  if( ((DataValue>>i)&0x1) == 0x1 ) //if Bit is high
  {
   UART_TX = 1;
  }
  else //if Bit is low
  {
   UART_TX = 0;
  }

     delay_uart(OneBitDelay);
 }

 //Send Stop Bit
 UART_TX = 1;
 
 //intcon.GIE = intcon_GIE;
 delay_uart(OneBitDelay);
}




















