"""
    Author: lefkovitj (https://lefkovitzj.com)
    File Last Modified: 8/28/2025
    Project Name: PyPdfApp
    File Name: gui.py
"""

import customtkinter as ctk

class GUI_Menu():
    def __init__(self, menu_name, tk_parent, button_texts, button_binds, button_statuses):
        if len(button_texts) != len(button_binds):
            raise ValueError(f"Lists button_text and button_binds must be of the same size. Got lists of length {len(button_texts)} and {len(button_binds)} instead.")

        self.name = menu_name
        self.buttons = []
        self.texts = button_texts
        self.binds = button_binds
        self.states = button_statuses
    def get_button_texts(self):
        return self.texts
    def get_button_commands(self):
        return self.binds
    def get_button_states(self):
        return_list = []
        for item in self.states:
            if item == True:
                return_list.append("normal")
            else:
                return_list.append("disabled")
        return return_list
    def get_name(self):
        return self.name

def gui_get_file(initial_directory="", limit_filetypes=[]):
    """Open file explorer (using tkinter) to select a file"""
    root = Tk() # Create the GUI window.
    root.withdraw()
    complete_file_path = filedialog.askopenfilename(title="File Select", initialdir = os.getcwd() + "/" + initial_directory, filetypes = limit_filetypes) # Select the file.
    root.destroy()
    file_path, file_name = os.path.split(complete_file_path) # Get the filepath and filename to return to the user.
    return complete_file_path, file_name