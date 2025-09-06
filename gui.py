"""
    Author: lefkovitj (https://lefkovitzj.com)
    File Last Modified: 8/29/2025
    Project Name: PyPdfApp
    File Name: gui.py
"""

class GuiMenu():
    """Represent a menu that can be selected via the menus dropdown"""
    def __init__(self, menu_name, button_texts, button_binds, button_statuses):
        if len(button_texts) != len(button_binds):
            raise ValueError(
                ("Lists button_text and button_binds must be of the same size. "
                 f"Got lists of length {len(button_texts)} and {len(button_binds)} instead.")
            )

        self.name = menu_name
        self.buttons = []
        self.texts = button_texts
        self.binds = button_binds
        self.states = button_statuses

    def get_button_texts(self):
        """Getter for .texts"""
        return self.texts

    def get_button_commands(self):
        """Getter for .binds"""
        return self.binds

    def get_button_states(self):
        """Reformatted getter for .states"""
        return_list = []
        for item in self.states:
            if item is True:
                return_list.append("normal")
            else:
                return_list.append("disabled")
        return return_list

    def get_name(self):
        """Getter for .name"""
        return self.name
