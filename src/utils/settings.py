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

import ujson

class Settings():
    def __init__(self, file_name):
        self.file_name = file_name
        self.dict = {}
        self.read()

    def read(self, from_backup=False):
        file_name = self.file_name
        if from_backup:
            file_name += ".bak"
        try:
            with open(file_name, "r") as f:
                dict = ujson.load(f)
            if dict is None:
                print("Empty file")
                dict = {}
            # Update the values in self.dict, not by replacing, since users already have a ref
            self.dict.clear()
            for key,value in dict.items():
                self.dict[key] = value

        except Exception as e:
            print("Exception", e)
            with open(file_name, "w") as f:
                ujson.dump(self.dict, f)

        print("read:", ujson.dumps(self.dict))

    def write(self, to_backup=False):
        file_name = self.file_name
        if to_backup:
            file_name += ".bak"
        print("save:", ujson.dumps(self.dict))
        with open(file_name, "w") as f:
            ujson.dump(self.dict, f)
