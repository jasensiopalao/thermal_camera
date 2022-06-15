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

from ucollections import namedtuple

class Menu():

    Entity = namedtuple("Entity", ("text", "action"))
    NoText = None
    NoAction = None

    def __init__(self):
        self.ancestor = []
        self.ancestor_cursor = []
        self._structure = {}
        self.active = self._structure
        self.entity_order = []
        self.cursor = 0
        self.cursor_display_start = 0
        self.cursor_display_end = 0
        self.cursor_items = []
        self.cursor_entity = None
        self.cursor_lines = 6
        self.state = ""
        self.page = ""
        
        self.entity_scroll_up = Menu.Entity(text=None, action=self.cursor_decrement)
        self.entity_scroll_down = Menu.Entity(text=None, action=self.cursor_increment)
        self.entity_scroll_selection = Menu.Entity(text=None, action=self.cursor_action)

        self.entity_back_action = Menu.Entity(text="Back", action=self.back)
        self.entity_back_no_text = Menu.Entity(text=None, action=self.back)
        self.entity_reset_no_text = Menu.Entity(text=None, action=self.reset)

    def cursor_text(self):
        if not self.cursor_entity:
            return ""
        return self.string_callback(self.cursor_entity.text)

    def cursor_action(self):
        if not self.cursor_entity:
            return ""
        return self.string_callback(self.cursor_entity.action)

    def cursor_increment(self):
        self.cursor += 1
        self.cursor_update()

    def cursor_decrement(self):
        self.cursor -= 1
        self.cursor_update()

    def cursor_update(self):
        cursor_max = len(self.active["items"]) - 1
        # Wrap around
        if self.cursor < 0:
            self.cursor = cursor_max
        if self.cursor > cursor_max:
            self.cursor = 0
        self.cursor_entity = self.cursor_items[self.cursor]
        half_lines = round(self.cursor_lines)//2
        self.cursor_display_start = max(0, self.cursor - half_lines,  )
        self.cursor_display_end = min(cursor_max, self.cursor_display_start + self.cursor_lines )

    def cursor_load(self, position=0):
        self.cursor = position
        self.cursor_entity = None
        self.cursor_items = []
        if "items" in self.active:
            print("Load list")
            self.cursor_items = self.active["items"]
            if self.active["items"]:
                self.cursor_update()

    def state_load(self):
        if "state" in self.active:
            self.state = self.active["state"]
        if "page" in self.active:
            self.page = self.active["page"]
        else:
            self.page = ""
    @property
    def structure(self):
        return self._structure

    @structure.setter
    def structure(self, structure):
        self._structure = structure
        self.reset()

    def reset(self):
        self.ancestor.clear()
        self.ancestor_cursor.clear()
        self.active = self.structure
        self.cursor_load()
        self.state_load()

    def enter(self, submenu):
        print("From level. Title: ", self.get_title())
        self.ancestor.append(self.active)
        self.ancestor_cursor.append(self.cursor)
        self.active = submenu
        print("Enter sublevel. Title: ", self.get_title())
        self.cursor_load()
        self.state_load()

    def back(self):
        if self.ancestor:
            print("Exit sublevel. Title: ", self.get_title())
            self.active = self.ancestor.pop()
        print("Back to sublevel. Title: ", self.get_title())
        self.cursor_load(position=self.ancestor_cursor.pop())
        self.state_load()

    def string_callback(self, parameters):
        if isinstance(parameters, str):
            return parameters
        if isinstance(parameters, tuple):
            function, arguments = parameters
            return function(**arguments)
        elif callable(parameters):
            return parameters()
        elif isinstance(parameters, dict):
            return self.enter(submenu=parameters)
        elif isinstance(parameters, list):
            for parameter in parameters:
                self.string_callback(parameter)

    def get_title(self):
        if "title" in self.active:
            string = self.string_callback(self.active["title"])
        else:
            string = " --- "
        if string is None:
            string = ""
        return string

    def generate_entity_line(self, entity):
        if entity.text is None:
            return ""

        string = "\n"
        if isinstance(entity.text, dict):
            raise NotImplementedError("Dictionary not allowed in text field")
        text = self.string_callback(entity.text)

        if text is None:
            return string

        if entity is self.cursor_entity:
            string += "@ "
        else:
            string += "-  "
        string += text
        return string

    def generate_text(self):
        string = self.get_title()

        for name in self.entity_order:
            if name not in self.active:
                continue
            string += self.generate_entity_line(self.active[name])

        if self.cursor_items:
            string += "\nOptions:"
            for entity in self.cursor_items[self.cursor_display_start:(self.cursor_display_end+1)]:
                string += self.generate_entity_line(entity)

        return string

    def process_action(self, name):
        if name not in self.active:
            return False
        entity = self.active[name]
        if not entity.action:
            return False
        action = entity.action
        return self.string_callback(action)
