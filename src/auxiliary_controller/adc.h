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

volatile unsigned char battery_voltage_sample = 0;
volatile unsigned char battery_voltage_samples = 0;
// Split array because:
//  - Arrays of shorts seem to not get the memory size allocated well according to the type, it seems to only count on char
//  - Also arrays must fit in one signle page
volatile unsigned char battery_voltage_samples_h[BATTERY_VOLTAGE_SAMPLES];
volatile unsigned char battery_voltage_samples_l[BATTERY_VOLTAGE_SAMPLES];

volatile unsigned short battery_average = 0;
volatile unsigned short battery_last = 0;
volatile unsigned short board_vout_last = 0;
volatile unsigned long max_adc_x_vref = (0x000003FF) * VOLTAGE_FVR_VP6_MILLIVOLTS;

volatile unsigned char adc_channel = 0;
volatile unsigned char adc_measurement_count = 0;

inline void adc_start_measurement() {
   adc_measurement_count = 0;
   ADC_ACTIVE = 1;
}

inline bool is_adc_measurement_finished() {
   return (adc_measurement_count >= ADC_STABLE_MEASUREMENT_COUNT) ? true : false;
}

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
   pie1.ADIE = 1;  // To enable the interrupt
   
   // NOTES 
   // 1011 = AN11
   //anselh.3 = 1;  // RB4/AN11 as ADC
   //trisb.4 = 1;
}


inline void process_board_vout(void) {
   // adc -- v_out
   // 0x3FF -- battery_last
   unsigned short adc_measurement = (adresh << 8) | adresl;
   unsigned short voltage = ((unsigned long)adc_measurement * (unsigned long)battery_last ) / 0x3FF;
   if (voltage > MAXIMUM_POSSIBLE_MILLIVOLTS) {
      return;
   }
   board_vout_last = voltage;
}

inline void process_battery_voltage(void) {
   
   // adc -- 0.6
   // 0x3FF -- battery
   if (adresh == 0xFF) {
      return;
   }
   unsigned short adc_measurement = (adresh << 8) | adresl;
   unsigned short voltage = max_adc_x_vref / adc_measurement;
   if (voltage > MAXIMUM_POSSIBLE_MILLIVOLTS) {
      return;
   }
   battery_last = voltage;
   
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
   
   if (board_vout_last < BOARD_VOUT_POWER_OFF_MILLIVOLTS) {
      battery_average += VOLTAGE_VCC_DIODE_PIC_LOW_POWER;
   } else {
      battery_average += VOLTAGE_VCC_DIODE_PIC_HIGH_POWER;
   }
   
   bit spi_enabled = pie1.SSPIE;
   pie1.SSPIE = 0;
   spi_tx_array[TX_VOLTAGE_H] = (unsigned char)(battery_average >> 8);
   spi_tx_array[TX_VOLTAGE_L] = (unsigned char)(battery_average);
   pie1.SSPIE = spi_enabled;
}