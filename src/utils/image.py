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

import micropython

@micropython.viper
def qvga2qvga(src: ptr16, dst: ptr16, start_step: int, step_size: int):
    columns_image = 320
    rows_image = 240

    image_size = columns_image * rows_image
    index = start_step
    while index < image_size:
        dst[index] = src[index]
        index += step_size

@micropython.viper
def qqvga2qvga(src: ptr16, dst: ptr16):
    """ Fast method to increase the resolution from QQVGA to QVGA (approx time 7ms) """
    columns_image = 160
    rows_image = 120
    image_size = columns_image * rows_image
    icolumn_screen = 0
    icolumn_screen_1 = icolumn_screen + 1
    irow_screen = 0
    irow_screen_1 = irow_screen + 1

    columns_screen = 320
    # assumption that the screen has double the lines of the image

    index_image = 0
    while index_image < image_size:
        pixel = src[index_image]
        index_image += 1

        icolumn_screen_1 = icolumn_screen + 1
        irow_screen_index = irow_screen   * columns_screen
        dst[icolumn_screen   + irow_screen_index] = pixel
        dst[icolumn_screen_1 + irow_screen_index] = pixel
        irow_screen_index = irow_screen_1   * columns_screen
        dst[icolumn_screen   + irow_screen_index] = pixel
        dst[icolumn_screen_1 + irow_screen_index] = pixel

        icolumn_screen += 2

        if icolumn_screen >= columns_screen:
            icolumn_screen = 0
            irow_screen += 2
            irow_screen_1 = irow_screen + 1


@micropython.viper
def qqgrey2qvga(src: ptr8, dst: ptr16):
    """ Fast method to increase the resolution from QQVGA to QVGA (approx time 7ms) """
    columns_image = 160
    rows_image = 120
    image_size = columns_image * rows_image
    icolumn_screen = 0
    icolumn_screen_1 = icolumn_screen + 1
    irow_screen = 0
    irow_screen_1 = irow_screen + 1

    columns_screen = 320
    # assumption that the screen has double the lines of the image

    index_image = 0
    pixel565 = int(0)
    while index_image < image_size:
        pixel = int(src[index_image])
        pixel_2 = pixel >> 2
        pixel_3 = pixel_2 >> 1
        pixel565 = (pixel_3 << 11) | (pixel_2 << 5) | (pixel_3)
        index_image += 1

        icolumn_screen_1 = icolumn_screen + 1
        irow_screen_index = irow_screen   * columns_screen
        dst[icolumn_screen   + irow_screen_index] = pixel565
        dst[icolumn_screen_1 + irow_screen_index] = pixel565
        irow_screen_index = irow_screen_1   * columns_screen
        dst[icolumn_screen   + irow_screen_index] = pixel565
        dst[icolumn_screen_1 + irow_screen_index] = pixel565

        icolumn_screen += 2

        if icolumn_screen >= columns_screen:
            icolumn_screen = 0
            irow_screen += 2
            irow_screen_1 = irow_screen + 1

@micropython.viper
def increase_image_viper(src: ptr16, dst: ptr16, pixels: int):
    columns_image = 160
    rows_image = 120
    icolumn_image = 0
    irow_image = 0
    icolumn_screen = 0
    irow_screen = 0
    icolumn_pixel = 0
    irow_pixel = 0

    columns_screen = 320

    icolumn_screen_1 = icolumn_screen + 1
    irow_screen_1 = irow_screen + 1
    while irow_image < rows_image:
        pixel = src[icolumn_image + irow_image * columns_image]

        irow_pixel = 0
        while irow_pixel < pixels:
            icolumn_pixel = 0
            while icolumn_pixel < pixels:
                dst[icolumn_screen + icolumn_pixel + (irow_screen + irow_pixel) * columns_screen] = pixel
                icolumn_pixel += 1
            irow_pixel += 1

        icolumn_image += 1
        if icolumn_image >= columns_image:
            icolumn_image = 0
            irow_image += 1
            irow_screen = 2 * irow_image
            irow_screen_1 = irow_screen + 1
        icolumn_screen = 2 * icolumn_image

@micropython.viper
def pixel2pixel(src: ptr8):
    columns_image = 320
    rows_image = 240

    image_size = columns_image * rows_image * 2
    index = 0
    while index < image_size:
        pix1 = src[index]
        pix2 = src[index+1]
        src[index] = pix2
        src[index+1] = pix1
        index += 2

@micropython.viper
def qvgafov2qvga(
    src: ptr16,
    dst: ptr16,
    column_offset: int,
    row_offset: int,
    column_zoom_numerator: int,
    column_zoom_denominator: int,
    row_zoom_numerator: int,
    row_zoom_denominator: int,
):
    """ Fast method to expand the FOI to the full dst frame buffer """
    columns = 320
    rows = 240
    image_size = columns * rows

    icolumn_src = column_offset
    irow_src = row_offset
    icolumn_dst = 0
    irow_dst = 0

    # assumption that the screen has double the lines of the image

    # assume column_zoom_denominator < column_zoom_numerator
    column_fraction_copy = column_zoom_numerator - column_zoom_denominator
    row_fraction_copy = row_zoom_numerator - row_zoom_denominator

    icolumn_action = 0
    irow_action = 0
    index_src = icolumn_src + irow_src * columns

    copies_per_column_copy = column_zoom_numerator // column_zoom_denominator
    columns_to_copy = 0  # Per block columns to be copied
    columns_copied = 0
    column_copied = 0

    copies_per_row_copy = row_zoom_numerator // row_zoom_numerator
    rows_to_copy = 0
    rows_copied = 0
    row_copied = 0
    #print(
        #"column_fraction_copy", column_fraction_copy, "copies_per_column_copy", copies_per_column_copy,
        #"row_fraction_copy", row_fraction_copy, "copies_per_row_copy", copies_per_row_copy
    #)
    while True:

        index_src = icolumn_src + irow_src * columns
        pixel = src[index_src]
        dst[icolumn_dst   + irow_dst   * columns] = pixel
        #print(icolumn_src, irow_src, icolumn_dst, irow_dst, "action", icolumn_action, irow_action, "copy", columns_to_copy, rows_to_copy)
        if columns_to_copy == 0 and column_copied != icolumn_src and columns_copied < column_fraction_copy:
            columns_to_copy = copies_per_column_copy

        if columns_to_copy > 0:
            columns_to_copy -= 1
            column_copied = icolumn_src
            columns_copied += 1
        else:
            icolumn_src += 1

        icolumn_action += 1
        if icolumn_action >= column_zoom_numerator:
            icolumn_action = 0
            columns_copied = 0

        icolumn_dst += 1
        if icolumn_dst >= columns or icolumn_src >= columns:
            icolumn_dst = 0
            icolumn_src = column_offset
            icolumn_action = 0
            columns_copied = 0

            #print(icolumn_src, irow_src, icolumn_dst, irow_dst, "action", icolumn_action, irow_action, "copy", columns_to_copy, rows_to_copy)

            if rows_to_copy == 0 and row_copied != irow_src and rows_copied < row_fraction_copy:
                rows_to_copy = copies_per_row_copy

            if rows_to_copy > 0:
                rows_to_copy -= 1
                row_copied = irow_src
                rows_copied += 1
            else:
                irow_src += 1

            irow_action += 1
            if irow_action >= row_zoom_numerator:
                irow_action = 0
                rows_copied = 0

            irow_dst += 1
            if irow_dst >= rows or irow_src >= rows:
                return
