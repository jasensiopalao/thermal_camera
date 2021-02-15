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

import micropython, utime
from pyb import Pin, ExtInt

import micropython
micropython.alloc_emergency_exception_buf(100)

class InterruptHandler():

    def __init__(self, pin_interrupt, callback=None, **arguments):
        self._enabled = False
        self._calling_callback = False
        self.pin = pin_interrupt
        self._callback = None
        self._callback_arguments = {}
        self._allocation_scheduled_callback = self.scheduled_callback
        self._interrupt = None
        self.interrupt_time = utime.ticks_ms()
        if callback:
            self.enable(callback, arguments)

    def enable(self, callback=None, trigger=ExtInt.IRQ_FALLING, initial_check=False, **arguments):
        if self._interrupt:
            if not self._calling_callback:
                self._interrupt.enable()
        elif callback:
            self._callback = callback
            if arguments:
                self._callback_arguments = arguments
            print("Creating interrupt on pin", self.pin, "on", trigger)
            self._interrupt = ExtInt(
                self.pin, trigger, Pin.PULL_NONE, self.interrupt_callback
            )
            print()
        else:
            raise NotImplementedError("No callback defined")

        self._enabled = True

    def disable(self):
        self._enabled = False
        self._interrupt.disable()

    def time_since_interrupt(self):
        return utime.ticks_diff(utime.ticks_ms(), self.interrupt_time)

    def interrupt_callback(self, line=None):
        self.interrupt_time = utime.ticks_ms()
        if self._calling_callback:
            return
        if self._interrupt:
            self._interrupt.disable()
        self._calling_callback = True
        micropython.schedule(self._allocation_scheduled_callback, line)

    def scheduled_callback(self, line):
        self._callback_arguments["line"] = line
        self._callback(**self._callback_arguments)
        self._calling_callback = False
        if self._interrupt and self._enabled:
            self._interrupt.enable()
