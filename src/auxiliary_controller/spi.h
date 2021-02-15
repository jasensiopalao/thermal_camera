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
*/

volatile unsigned char spi_tx_size = SPI_BUFFER_SIZE;  // spi_rx_size is just local
volatile unsigned char spi_tx_array[SPI_BUFFER_SIZE];
volatile unsigned char spi_rx_array[SPI_BUFFER_SIZE];

volatile unsigned char tx_package_id = 0;
volatile unsigned char rx_package_id = 0;

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

inline void deinit_spi(void) {
   pie1.SSPIE = 0;  // Disable SPI interrupt
   sspcon.SSPEN= 0; // Disable module
   
   PIN_SPI_SS_PULL_UP_DIR = 1;
}

inline void init_spi(void) {
   char dummy;
   // Serial Data Out (SDO) – RC5/SDO
   // Serial Data In (SDI) – RC4/SDI/SDA
   // Serial Clock (SCK) – RC3/SCK/SCL
   // Slave Select (SS) – RA5/SS/AN4

   deinit_spi();
   
   PIN_SPI_SS_PULL_UP = 1;
   PIN_SPI_SS_PULL_UP_DIR = 0;
   
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
   
   PIN_SPI_SS_DIR = 1;  // RA5/AN4 as input
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