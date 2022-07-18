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

class CameraSlaveControl():
    COLUMN_OFFSET = const(0)
    ROW_OFFSET = const(1)
    COLUMN_ZOOM_NUMERATOR = const(2)
    COLUMN_ZOOM_DENOMINATOR = const(3)
    ROW_ZOOM_NUMERATOR = const(4)
    ROW_ZOOM_DENOMINATOR = const(5)

    def __init__(self):
        self.buff = bytearray(6)

    @property
    def column_offset(self):
        return self.buff[COLUMN_OFFSET]

    @column_offset.setter
    def column_offset(self, column_offset):
        self.buff[COLUMN_OFFSET] = column_offset

    @property
    def row_offset(self):
        return self.buff[ROW_OFFSET]

    @row_offset.setter
    def row_offset(self, row_offset):
        self.buff[ROW_OFFSET] = row_offset

    @property
    def column_zoom_numerator(self):
        return self.buff[COLUMN_ZOOM_NUMERATOR]

    @column_zoom_numerator.setter
    def column_zoom_numerator(self, column_zoom_numerator):
        self.buff[COLUMN_ZOOM_NUMERATOR] = column_zoom_numerator


    @property
    def column_zoom_denominator(self):
        return self.buff[COLUMN_ZOOM_DENOMINATOR]

    @column_zoom_denominator.setter
    def column_zoom_denominator(self, column_zoom_denominator):
        self.buff[COLUMN_ZOOM_DENOMINATOR] = column_zoom_denominator

    @property
    def row_zoom_numerator(self):
        return self.buff[ROW_ZOOM_NUMERATOR]

    @row_zoom_numerator.setter
    def row_zoom_numerator(self, row_zoom_numerator):
        self.buff[ROW_ZOOM_NUMERATOR] = row_zoom_numerator

    @property
    def row_zoom_denominator(self):
        return self.buff[ROW_ZOOM_DENOMINATOR]

    @row_zoom_denominator.setter
    def row_zoom_denominator(self, row_zoom_denominator):
        self.buff[ROW_ZOOM_DENOMINATOR] = row_zoom_denominator
