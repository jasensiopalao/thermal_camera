// Code concept from:
// - https://www.microchip.com/forums/m926980.aspx
#ifndef _UART_H_
#define _UART_H_

volatile char uart_tx_array[UART_BUFFER_SIZE];

void InitSoftUART(void) // Initialize UART pins to proper values
{
 UART_TX = 1; // TX pin is high in idle state
 
 UART_RX_DIR = 1; // Input
 UART_TX_DIR = 0; // Output
}

void DeinitSoftUART(void) // Initialize UART pins to proper values
{
 UART_TX = 0; // TX pin is high in idle state
 
 UART_RX_DIR = 1; // Input
 UART_TX_DIR = 1; // Output
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

void UART_Transmit(const char DataValue)
{
 /* Basic Logic
    
    TX pin is usually high. A high to low bit is the starting bit and 
    a low to high bit is the ending bit. No parity bit. No flow control.
    BitCount is the number of bits to transmit. Data is transmitted LSB first.

 */

#ifdef UART_DISABLE_INT
 bit intcon_GIE = intcon.GIE;
 intcon.GIE = 0; 
#endif
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
 
#ifdef UART_DISABLE_INT 
 intcon.GIE = intcon_GIE;
#endif
 delay_uart(OneBitDelay);
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


#endif