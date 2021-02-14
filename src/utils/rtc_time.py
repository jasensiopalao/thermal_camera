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

from pyb import RTC
import utime, time

def time_datetime2string():
    year, month, mday, hour, minute, second, weekday, yearday = utime.localtime()
    return "{:4d}-{}-{} {:02d}:{:02d}:{:02d}".format(year, month, mday, hour, minute, second)

def tuple_time2rtc(time_tuple):
    year, month, mday, hour, minute, second, weekday, yearday = time_tuple
    day = mday
    weekday = weekday + 1   # weekday is 1-7 for Monday through Sunday """
    hours = hour
    minutes = minute
    seconds = second
    subseconds = 0
    return (year, month, day, weekday, hours, minutes, seconds, subseconds)


def time_rtc2dictionary(dictionary):
    year, month, day, weekday, hours, minutes, seconds, subseconds = RTC().datetime()
    dictionary["year"] = year
    dictionary["month"] = month
    dictionary["day"] = day
    dictionary["weekday"] = weekday
    dictionary["hours"] = hours
    dictionary["minutes"] = minutes
    dictionary["seconds"] = seconds


def time_dictionary2rtc(dictionary):
    year = dictionary.get("year", 2021)
    month = dictionary.get("month", 1)
    day = dictionary.get("day", 14)
    weekday = dictionary.get("weekday", 4)
    hours = dictionary.get("hours", 14)
    minutes = dictionary.get("minutes", 1)
    seconds = dictionary.get("seconds", 0)
    subseconds = 0
    rtc_tuple_base = year, month, day, weekday, hours, minutes, seconds, subseconds
    RTC().datetime(rtc_tuple_base)


def time_modify_rtc(
    modify_amount=0, modify_unit=None
):
    modify_amount = int(modify_amount)
    base_time = utime.localtime()
    year, month, mday, hour, minute, second, weekday, yearday = base_time

    change_time = False
    if modify_amount != 0:
        year, month, mday, hour, minute, second, weekday, yearday = base_time
        if modify_unit == "year":
            change_time = True
            year += modify_amount
        elif modify_unit == "month":
            change_time = True
            month += modify_amount
        elif modify_unit == "day":
            change_time = True
            mday += modify_amount
        elif modify_unit == "hour":
            change_time = True
            hour += modify_amount
        elif modify_unit == "minute":
            change_time = True
            minute += modify_amount
        elif modify_unit == "second":
            change_time = True
            second += modify_amount
        if not change_time:
            raise NotImplementedError("Wrong unit %s" % modify_unit)

    if change_time:
        future_time = utime.mktime((year, month, mday, hour, minute, second, weekday, yearday))
        base_time_target = time.localtime(future_time)

        RTC().datetime(tuple_time2rtc(base_time_target))
        base_time_saved = utime.localtime()
        if base_time_target == base_time_saved:
            return True
        else:
            print("target", base_time_target)
            print("after", base_time_saved)
    return False

# (year, month, mday, hour, minute, second, weekday, yearday)
# weekday is 0-6 for Mon-Sun
