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

import utime
from pyb import SPI, Pin, LED

class DynamicSPI():

    _spi = None
    _locked = None
    _hash_arguments = None
    _release_callback = None
    _release_callback_arguments = None
    _verbose = False

    def create(*args, **kwargs):
        if DynamicSPI._spi:
            DynamicSPI._spi.deinit()
            del DynamicSPI._spi
        DynamicSPI._spi = SPI(2, mode=SPI.MASTER, **kwargs)
        DynamicSPI._hash_arguments = hash(frozenset(kwargs.items()))
        return DynamicSPI._hash_arguments

    def __init__(self, pin_cs, start_delay=0, byte_delay=0, **arguments):
        self._hash_arguments = self.create(**arguments)
        self.pin_cs = Pin(pin_cs, Pin.OUT_PP)
        self.arguments = arguments
        self._allow_relock = False
        self.start_delay = start_delay
        self.byte_delay = byte_delay
        self.write = self.send

        # make sure that the CS line is high to not disturb other devices
        self.pin_cs.value(1)

    @property
    def locked(self):
        return DynamicSPI._locked is not None

    def lock(self, allow_relock=False, release_callback=None, **arguments):
        if self.locked and self._allow_relock and DynamicSPI._hash_arguments == self._hash_arguments:
            if self._verbose:
                print("Re-using")
        else:
            if self.locked:
                if release_callback:
                    if self._verbose:
                        print("SPI schedulled callback")

                    DynamicSPI._release_callback = release_callback
                    DynamicSPI._release_callback_arguments = arguments
                    return False
                else:
                    LED(1).on()
                    LED(2).on()
                    LED(3).on()
                    utime.sleep_ms(1000)
                    if self._verbose:
                        print("\n\nALREADY LOCKED", DynamicSPI._spi, DynamicSPI._locked)
                    raise NotImplementedError("ALREADY LOCKED")

            if DynamicSPI._hash_arguments != self._hash_arguments:
                if self._verbose:
                    print("Change to", self.arguments)
                self._hash_arguments = DynamicSPI.create(**self.arguments)

        self._allow_relock = allow_relock

        DynamicSPI._locked = self.arguments
        if self._verbose:
            print("Lock", self.arguments)
        self.pin_cs.value(0)
        utime.sleep_us(self.start_delay)
        return True

    def release(self):
        if not self.locked:
            print("It was not locked")
            raise NotImplementedError
        self._allow_relock = False
        self.pin_cs.value(1)
        release_callback = DynamicSPI._release_callback
        release_arguments = DynamicSPI._release_callback_arguments
        DynamicSPI._release_callback = None
        DynamicSPI._release_callback_arguments = None
        DynamicSPI._locked = None

        if self._verbose:
            print("Released", self.arguments)
        if release_callback:
            release_callback(**release_arguments)

    def send(self, send, **kwargs):
        auto_lock = not self.locked or self._allow_relock
        if auto_lock:
            if self._verbose:
                print("Autolock")
            self.lock()

        if self.byte_delay == 0:
            result=DynamicSPI._spi.send(send, **kwargs)
        else:
            end = len(send)
            send_mv = memoryview(send)
            for i in range(0, end):
                utime.sleep_us(self.byte_delay)
                DynamicSPI._spi.send(send_mv[i:(i+1)])
        if auto_lock:
            if self._verbose:
                print("Autorelease")
            self.release()

    def recv(self, receive, **kwargs):
        auto_lock = not self.locked or self._allow_relock
        if auto_lock:
            if self._verbose:
                print("Autolock")
            self.lock()

        if self.byte_delay == 0:
            result=DynamicSPI._spi.recv(receive, **kwargs)
        else:
            end = len(receive)
            receive_mv = memoryview(receive)
            for i in range(0, end):
                utime.sleep_us(self.byte_delay)
                DynamicSPI._spi.recv(receive_mv[i:(i+1)])
        if auto_lock:
            if self._verbose:
                print("Autorelease")
            self.release()

    def send_recv(self, send, receive, **kwargs):
        auto_lock = not self.locked or self._allow_relock
        if auto_lock:
            if self._verbose:
                print("Autolock")
            self.lock()

        if self.byte_delay == 0:
            result=DynamicSPI._spi.send_recv(send, receive, **kwargs)
        else:
            end = min(len(send), len(receive))
            send_mv = memoryview(send)
            receive_mv = memoryview(receive)
            for i in range(0, end):
                utime.sleep_us(self.byte_delay)
                DynamicSPI._spi.send_recv(send_mv[i:(i+1)], receive_mv[i:(i+1)])
        if auto_lock:
            if self._verbose:
                print("Autorelease")
            self.release()
