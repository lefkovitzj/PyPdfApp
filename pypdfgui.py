"""
    Author: lefkovitj (https://lefkovitzj.github.io)
    File Last Modified: 1/4/2025
    Project Name: PyPdfApp
    File Name: pypdfgui.py
"""

# Python Standard Library Imports.
import copy
import json
import os
import requests
import subprocess
import sys
import traceback
from tkinter import *
import warnings
import webbrowser

# Third-party Module Imports.
import customtkinter as ctk
import fitz
import PIL

# Project Imports.
from extract import PDF_Extractor
from gui import GUI_Menu, gui_get_file
from load import open_pdf
from manipulate import *
from merge import PDF_Merger
from save import save_pdf
from sign import *
from utils import *

class App():
    """  =========================================  APPLICATION STARTUP ========================================= """
    def __init__(self):
        """ Internal Application Data & Settings """
        self.pdfs = PDF_Queue()
        self.pdf_id = None
        self.file_selected = ""
        self.signer_private_key_path = None
        self.signer = None
        self.scale = 1.0
        # Get the settings file data.
        with open("settings.json", "r") as json_settings:
            self.settings = json.load(json_settings)
        # Startup checks.
        self.needs_update = self.on_startup_update_check()
        self.license_agreed = self.on_startup_license_check()

        """ Application GUI - Layout & Contents """
        # Create the GUI window.
        self.root = ctk.CTk()
        # Add the menu areas.
        self.menu_top = ctk.CTkFrame(self.root)
        self.menu_top.pack(anchor="nw", fill="x")
        self.menu_middle = ctk.CTkFrame(self.root)
        self.menu_middle.pack(anchor="nw", fill="x")
        self.menu = ctk.CTkFrame(self.menu_top)
        self.menu.pack(anchor="nw", fill="x")
        self.submenu = ctk.CTkFrame(self.menu_middle)
        self.submenu.pack(anchor="nw", fill="x", expand=True)
        for i in range(11): # Configure the resizeable grid columns.
            self.menu.columnconfigure(i, weight=0)
            self.submenu.columnconfigure(i, weight=1)
        # Add the top menu and its contents.
        self.mode = ctk.CTkOptionMenu(self.menu, values=["Pages", "Encrypt & Compress", "Insert", "Extract", "Meta Data", "Signatures"], command=self.set_menu, width=175)
        self.mode.grid(row=0, column=0, columnspan=2, padx=5)
        self.prev = ctk.CTkButton(self.menu, text = "<", command = self.previous_page, width = 25)
        self.next = ctk.CTkButton(self.menu, text = ">", command = self.next_page, width = 25)
        self.save = ctk.CTkButton(self.menu, text = "💾", command = self.save_event, width = 25)
        self.open = ctk.CTkButton(self.menu, text = "📂", command = self.open_new_pdf, width = 25)
        self.close = ctk.CTkButton(self.menu, text = "x", command = self.close_current_pdf, width = 25)
        self.prev.grid(row = 0, column = 2, padx=5)
        self.next.grid(row = 0, column = 3, padx=5)
        self.save.grid(row = 0, column = 4, padx=5)
        self.open.grid(row = 0, column = 5, padx=5)
        self.close.grid(row = 0, column = 6, padx=5)
        self.scale_display = ctk.CTkLabel(self.menu, text = "Zoom: 100%", fg_color = "transparent")
        self.scale_slider = ctk.CTkSlider(self.menu, from_=1, to=int(self.settings["app_max_zoom_scale"]) * 4, command=self.adjust_scale, width=75, number_of_steps = int(self.settings["app_max_zoom_scale"]) * 4 - 1)#, width=self.menu_middle.winfo_width()/4)
        self.scale_display.grid(row=0, column=7, padx=5)
        self.scale_slider.grid(row=0, column=8, padx=5)
        self.page_count = ctk.CTkLabel(self.menu, text = "page x/x", fg_color = "transparent")
        if self.pdfs.is_empty():
            self.page_count.configure(text=f"Page: 0/0")
        else:
            self.page_count.configure(text=f"Page: {self.pdfs[self.pdf_id].page_i+1}/{len(self.pdfs[self.pdf_id].doc)}")
        self.page_count.grid(row=0, column=9)
        # Add the middle menu content (buttons).
        self.menu_button_1 = ctk.CTkButton(self.submenu, text=" ",  command = lambda: print(""))
        self.menu_button_1.grid(row = 0, column=0, columnspan=3, padx=5, pady=10, sticky="nsew")
        self.menu_button_2 = ctk.CTkButton(self.submenu, text=" ", command = lambda: print(""))
        self.menu_button_2.grid(row = 0,column=3, columnspan=3, padx=5, pady=10, sticky="nsew")
        self.menu_button_3 = ctk.CTkButton(self.submenu, text=" ", command = lambda: print(""))
        self.menu_button_3.grid(row = 0,column=6, columnspan=3, padx=5, pady=10, sticky="nsew")
        self.menu_button_4 = ctk.CTkButton(self.submenu, text=" ", command = lambda: print(""))
        self.menu_button_4.grid(row = 0,column=9, columnspan=3, padx=5, pady=10, sticky="nsew")
        # Open bottom menu (file selector).
        self.file_menu = ctk.CTkFrame(self.menu_middle)
        self.file_menu.pack(anchor="nw", fill="x", expand=True)
        for i in range(11): # Configure the resizeable grid columns.
            self.file_menu.columnconfigure(i, weight=1)
        self.file_select_bar = ctk.CTkSegmentedButton(self.file_menu, command=self.file_selector_callback, width=self.file_menu.winfo_width())
        self.file_select_bar.grid(row=0, column=0, padx=(0, 0), pady=(10, 10), columnspan=12, sticky="ew")
        self.file_select_bar.configure(values=self.pdfs.get_keys())
        # Update the window graphics and readjust the size of the "mode" dropdown to match one of "menu_button_1" in width.
        self.root.update() 
        self.mode.configure(width=self.root.winfo_width()/4 - 10)
        # Add the PDF render area, with vertical and horizontal scrollbars and the canvas.
        self.canvas_frame = ctk.CTkFrame(self.root)
        self.canvas_frame.pack(anchor="center", fill='both', expand=True)
        self.pdf_canvas = Canvas(self.canvas_frame, bg="#333333", highlightthickness=0)
        self.canvas_frame.bind("<Configure>", lambda e: self.pdf_canvas.configure(scrollregion=self.pdf_canvas.bbox("all")))
        self.scrollbar = ctk.CTkScrollbar(self.canvas_frame, orientation="vertical", fg_color="#333333")
        self.scrollbar.pack(side="right", fill="y")
        self.scrollbar.configure(command=self.pdf_canvas.yview)
        self.Hscrollbar = ctk.CTkScrollbar(self.canvas_frame, orientation="horizontal", fg_color="#333333")
        self.Hscrollbar.pack(side="bottom", fill="x")
        self.Hscrollbar.configure(command=self.pdf_canvas.xview)
        self.pdf_canvas.configure(yscrollcommand=self.scrollbar.set, xscrollcommand=self.Hscrollbar.set)
        self.pdf_canvas.pack(side="left", anchor='center', fill='both', expand=True)

        """ Startup Checks - Update & License """
        # Application update screen.
        if self.needs_update: 
            self.update_area = ctk.CTkFrame(self.root)
            self.update_area.place(anchor="nw", relheight=1.0, relwidth=1.0)
            ctk.CTkLabel(self.update_area, text = "Your software is not up to date. A new version is available!", fg_color = "transparent").pack()
            textbox = ctk.CTkTextbox(self.update_area)
            textbox.insert(0.0, """Your software is no longer up to date. Software updates are strongly encouraged. \nWhile this version should continue to operate, you will potentially be missing out on:\n  1. New application features.\n  2. Security updates.\n  3. Critical bug fixes.\n  4. Improved application efficiency.\n\nBy continuing to use this version of PyPdfApp you may experience some of the following issues:\n  1. Unexpected program crashes.\n  2. User interface glitches.\n  3. Functionality failures.\n  4. Possible corruption of PDF files. \n\n To ensure you are using the most recent version of PyPdfApp, select "Open browser for update". \nFrom there, you can download the newest version of PyPdfApp avaialable! """)
            textbox.configure(state="disabled")
            textbox.pack(anchor="nw", fill="both", expand=True)
            ctk.CTkButton(self.update_area, text="Open browser for update.", command = self.update_web_event).pack(side="right")
            ctk.CTkButton(self.update_area, text="Continue without update.", command = self.update_skip_event).pack(side="left")
        # Application license agreement screen.
        if not self.license_agreed: 
            self.license_area = ctk.CTkFrame(self.root)
            self.license_area.place(anchor="nw", relheight=1.0, relwidth=1.0)
            ctk.CTkLabel(self.license_area, text = "You must agree to the MIT license to continue!", fg_color = "transparent").pack(anchor="nw", fill="x")
            with open("license.txt", "r") as license_doc:
                license_text = license_doc.read()
            textbox = ctk.CTkTextbox(self.license_area)
            textbox.insert(0.0, license_text)
            textbox.configure(state="disabled")
            textbox.pack(anchor="nw", fill="both", expand=True)
            ctk.CTkButton(self.license_area, text="I agree to the MIT License.", command = self.license_agree_event).pack(anchor="nw", fill="x", side="right")

        """ Initial Configuration - Window, Binds, and Graphics """
        # Set window title.
        self.root.title("PyPdfApp") 
        # Set window close functionality.
        if bool(self.settings["ask_save_before_exit"]):
            self.root.protocol("WM_DELETE_WINDOW", self.app_exit_event) # Add on-exit "Are you sure?" event.
        # Set window minimum dimensions.
        self.root.minsize(self.root.winfo_width(), 250) 
        # Binds.
        if bool(self.settings["allow_keyboard_events"]):
            self.root.bind("<Control-s>", self.save_event)
            self.root.bind("<Left>", self.previous_page)
            self.root.bind("<Right>", self.next_page)
            self.root.bind("<Control-Key-plus>", self.scale_up)
            self.root.bind("<Control-Key-minus>", self.scale_down)
            self.root.bind("<Control-o>", self.open_new_pdf)
            self.root.bind("<Control-w>", self.close_current_pdf)
        self.pdf_canvas.bind("<B1-Motion>", self.mouse_add_coords)
        self.pdf_canvas.bind("<ButtonRelease-1>", self.mouse_set_end)
        # Load the menu data.
        self.menus = {
                            "Encrypt & Compress":       GUI_Menu("Encryption", self.root, ["Set Encryption", "Remove Encryption", "Compress", "Compress (max)"], [self.event_set_encryption, self.event_remove_encryption, self.event_compress, self.event_compress_max], [True, True, True, True]),
                            "Pages":                    GUI_Menu("Pages", self.root, ["Move up", "Move down", "Rotate right", "Rotate left"], [self.event_move_up, self.event_move_down, self.event_rotate_right, self.event_rotate_left], [True, True, True, True]),
                            "Meta Data":                GUI_Menu("Meta Data", self.root, ["Set Author", "Set Title", "Set Subject", "Add Keywords"], [self.event_set_meta_author, self.event_set_meta_title, self.event_set_meta_subject, self.event_set_meta_keywords], [True, True, True, True]),
                            "Insert":                   GUI_Menu("Insert", self.root, ["Insert PDF", "Insert Blank", "Watermark page", "Watermark document"], [self.event_insert_pdf, self.event_insert_page, self.event_watermark_page, self.event_watermark_document], [True, True, True, True]),
                            "Extract":                  GUI_Menu("Extract", self.root, ["Delete page", "Extract text", "Extract images", "Screenshot Page"], [self.event_delete, self.event_extract_text, self.event_extract_images, self.event_screenshot_page], [True, True, True, True]),
                            "Signatures":               GUI_Menu("Signatures", self.root, ["Sign PDF", "Verfiy Signature", "Add Signer Account", "Select Signer Account"], [self.event_sign_pdf, self.event_verify_signature, self.event_add_signer_account, self.event_select_signer_account], [False, True, True, True]),
        }
        # Set initial menu value.
        self.menu = None 
        self.mode.set("Pages")
        self.set_menu("Pages")
        # Render the starting screen contents.
        if not self.pdfs.is_empty(): # Load the first page if a document is specified.
            self.update_page(0)
        else: # No document open, disable all actions that require an open PDF.
            self.disable_all_buttons()
            self.disable_all_keybinds()
        # Start the main application loop.
        self.root.mainloop() 


    """  ================================= ASSORTED APPLICATION FUNCTIONALITY =============================== """
    """ ------------------------------------------ Buttons & Keybinds ----------------------------------------- """
    def disable_all_buttons(self, *args):
        """ Disable all buttons related to manipulating a PDF. Used when no PDF is open. """
        self.menu_button_1.configure(state="disabled")
        self.menu_button_2.configure(state="disabled")
        self.menu_button_3.configure(state="disabled")
        self.menu_button_4.configure(state="disabled")
        self.next.configure(state="disabled")
        self.prev.configure(state="disabled")
        self.save.configure(state="disabled")
        self.close.configure(state="disabled")
        self.scale_slider.configure(state="disabled")
        self.mode.configure(state="disabled")
    def enable_all_buttons(self, *args):
        """ Disable all buttons related to manipulating a PDF. Used when no PDF is open. """
        self.menu_button_1.configure(state="normal")
        self.menu_button_2.configure(state="normal")
        self.menu_button_3.configure(state="normal")
        self.menu_button_4.configure(state="normal")
        self.next.configure(state="normal")
        self.prev.configure(state="normal")
        self.save.configure(state="normal")
        self.close.configure(state="normal")
        self.scale_slider.configure(state="normal")
        self.mode.configure(state="normal")
    def disable_all_keybinds(self, *args):
        """ Disable all keybinds that require an open PDF. Used when no PDF is open. """
        if bool(self.settings["allow_keyboard_events"]):
            self.root.unbind("<Control-s")
            self.root.unbind("<Left>")
            self.root.unbind("<Right>")
            self.root.unbind("Control-Key-plus>")
            self.root.unbind("Control-Key-minus>")
            self.root.unbind("<Control-w>")
        self.pdf_canvas.unbind("<B1-Motion>")
        self.pdf_canvas.unbind("<ButtonRelease-1>")
    def enable_all_keybinds(self, *args):
        """ Enable all keybinds that require an open PDF. Used when the first PDF is (re)opened. """
        if bool(self.settings["allow_keyboard_events"]):
            self.root.bind("<Control-s>", self.save_event)
            self.root.bind("<Left>", self.previous_page)
            self.root.bind("<Right>", self.next_page)
            self.root.bind("<Control-Key-plus>", self.scale_up)
            self.root.bind("<Control-Key-minus>", self.scale_down)
            self.root.bind("<Control-w>", self.close_current_pdf)
        self.pdf_canvas.bind("<B1-Motion>", self.mouse_add_coords)
        self.pdf_canvas.bind("<ButtonRelease-1>", self.mouse_set_end)
    def create_popup(self, popupTitle, popupText, popupCloseMessage):
        """ Create a popup window with the passed arguments used to generate the content of the winow. """
        popup = ctk.CTkToplevel(self.root)
        popup.title("PyPdfApp")
        # Add content to the popup
        titleLabel = ctk.CTkLabel(popup, text=popupTitle)
        titleLabel.pack(padx=20, pady=20)
        label = ctk.CTkLabel(popup, text=popupText)
        label.pack(padx=20, pady=20)
        button = ctk.CTkButton(popup, text=popupCloseMessage, command=popup.destroy) # Close button.
        button.pack(pady=10)
    def window_close_popup(self):
        """ Create a popup window with the passed arguments used to generate the content of the winow. """
        unsaved = self.pdfs.get_unsaved()
        if unsaved != []:
            popup = ctk.CTkToplevel(self.root)
            popup.title("PyPdfApp - Save & Exit")
            # Add content to the popup
            title_label = ctk.CTkLabel(popup, text="Save changes before leaving?")
            title_label.pack(padx=20, pady=10)
            label = ctk.CTkLabel(popup, text=f"You have unsaved changes in the following files: \n{','.join(unsaved)}")
            label.pack(padx=20, pady=10, fill="x")
            back_button = ctk.CTkButton(popup, text="Go back", command=popup.destroy) # Close button.
            back_button.pack(pady=0, side="left")
            exit_button = ctk.CTkButton(popup, text="Close anyway", command=sys.exit) # Close button.
            exit_button.pack(pady=0, side="right")
            popup.resizable(False, False)
            popup.grab_set()
        else:
            sys.exit()

    """ ---------------------------------------------- Save Status -------------------------------------------- """
    def set_saved(self):
        """ Update the file and GUI for a save event. """
        if self.pdfs[self.pdf_id].mods_made:
            self.pdfs.set_saved(self.pdf_id)
            self.file_select_bar.configure(values=self.pdfs.get_keys())
            self.update_file_select()
    def set_unsaved(self):
        """ Update the file and GUI for a new modification. """
        if not self.pdfs[self.pdf_id].mods_made:
            self.pdfs.set_unsaved(self.pdf_id)
            self.file_select_bar.configure(values=self.pdfs.get_keys())
            self.update_file_select()
    """ -------------------------------------------- Boolean Checks ------------------------------------------- """
    def has_open_pdf(self, *args):
        """ Return True if a PDF is open in the GUI. """
        try:
            return isinstance(self.pdfs[self.pdf_id], PDF_Doc_Instance)
        except:
            return False


    """  ==================================== STARTUP CHECKS FUNCTIONALITY ================================== """
    """ ----------------------------------------------- Update ----------------------------------------------- """
    def on_startup_update_check(self):
        """ Verify that the software is up to date with the most recent version. """
        settings_url = self.settings["newest_version_settings_url"] # Load from settings.json's data.
        version = self.settings["version"]
        try:
            url_data = requests.get(settings_url).json() # Get the data at "newest_version_settings_url" as JSON data.
            if url_data["version"] != version: # The version does not match.
                return True
            return False
        except: # Request failed due to lack of internet connection or missing online file.
            return False
    def update_skip_event(self):
        """ Process an update skip button event. """
        try: # Frame exists, destroy it and its contents.
            self.update_area.destroy()
        except: # Frame was not created, should never happen unless source code is tampered with.
            pass
    def update_web_event(self):
        """ Process an web update button event. """
        webbrowser.open(self.settings["newest_version_url"])
        sys.exit()
    """ ------------------------------------------------ License --------------------------------------------- """
    def on_startup_license_check(self):
        """ Verify that the user has already agreed to the MIT License terms and conditions. """
        if self.settings["license_agreed_to"] == True: # The license has been agreed to.
            return True
        return False
    def license_agree_event(self):
        """ Process a license agreement button event. """
        try: # Frame exists, destroy it and its contents.
            self.license_area.destroy()
            self.settings["license_agreed_to"] = True
            with open("settings.json", "w") as json_settings:
                json.dump(self.settings, json_settings, indent=4)
                json_settings.save()
        except: # Frame was not created, should never happen unless source code is tampered with.
            pass
    
    
    """  ========================================= MENU FUNCTIONALITY ======================================== """
    """ ------------------------------------------ Window Exit Event ---------------------------------------- """
    def app_exit_event(self):
        """ Process an appliction exit event. """
        if self.has_open_pdf():
            self.window_close_popup()
        else:
            sys.exit()
    """ ---------------------------------------------- Top Menu --------------------------------------------- """
    def set_menu(self, choice):
        """ Proces a menu selection event. """
        self.menu = self.menus[choice]
        updated_texts = self.menu.get_button_texts()
        updated_binds = self.menu.get_button_commands()
        updated_states = self.menu.get_button_states()
        self.menu_button_1.configure(text = updated_texts[0], command=updated_binds[0], state = updated_states[0])
        self.menu_button_2.configure(text = updated_texts[1], command=updated_binds[1], state = updated_states[1])
        self.menu_button_3.configure(text = updated_texts[2], command=updated_binds[2], state = updated_states[2])
        self.menu_button_4.configure(text = updated_texts[3], command=updated_binds[3], state = updated_states[3])
    def previous_page(self, *args):
        """ Change the page (-). """
        page_i = self.pdfs[self.pdf_id].page_i
        if page_i-1 >= 0:
            self.pdfs[self.pdf_id].page_i = page_i-1
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def next_page(self, *args):
        """ Change the page (+). """
        page_i = self.pdfs[self.pdf_id].page_i
        if page_i+1 <= len(self.pdfs[self.pdf_id].doc)-1:
            self.update_page(page_i+1)
            self.pdfs[self.pdf_id].page_i = page_i+1
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def save_event(self, *args):
        """ Process a save event. """
        self.save_path = save_pdf(self.pdfs[self.pdf_id].doc, self.pdfs[self.pdf_id].custom_metadata, self.pdfs[self.pdf_id].page_points, compress_basic = self.pdfs[self.pdf_id].compress_basic, compress_max = self.pdfs[self.pdf_id].compress_max, password = self.pdfs[self.pdf_id].password, forced_save=False)
        if self.save_path != None:
            self.set_saved()
    def save_pdf(self, event):
        """ Save the modified pdf document. """
        self.save_path = save_pdf(self.pdfs[self.pdf_id].doc, self.pdfs[self.pdf_id].custom_metadata, self.pdfs[self.pdf_id].page_points, compress_basic = self.pdfs[self.pdf_id].compress_basic, compress_max = self.pdfs[self.pdf_id].compress_max, password = self.pdfs[self.pdf_id].password)
        if self.save_path != None:
            self.set_saved()
    def open_new_pdf(self, *args):
        num_current_keys = len(list(self.pdfs.get_keys()))
        result = open_pdf()
        if result != None: # Check that a file was actually selected.
            file_path, doc, password = result
            new_pdf = PDF_Doc_Instance(file_path, doc, password)
            new_id = self.pdfs.add_pdf(new_pdf)
            self.pdf_id = new_id
            self.file_selected = f"{new_id}"
            self.update_file_select()
            self.file_select_bar.configure(values=self.pdfs.get_keys())
            
            if num_current_keys < 1:
                self.enable_all_buttons()
                self.enable_all_keybinds()
            
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def close_current_pdf(self, *args):
        if not self.has_open_pdf():
            return
        removed_pdf_id = "".join([char for char in list(self.pdf_id)])
        current_keys_list = self.pdfs.get_keys()
        num_current_keys = len(current_keys_list)
        current_index = current_keys_list.index(self.file_selected)
        self.pdfs.remove_pdf(self.pdf_id)

        self.file_select_bar.destroy()
        self.file_select_bar = ctk.CTkSegmentedButton(self.file_menu, command=self.file_selector_callback, width=self.file_menu.winfo_width())
        self.file_select_bar.grid(row=0, column=0, padx=(0, 0), pady=(10, 10), columnspan=12, sticky="ew")
        self.file_select_bar.configure(values=self.pdfs.get_keys())
        
        
        if num_current_keys <= 1: # Handle closing of last file.
            self.page_count.configure(text=f"Page: 0/0")
            self.disable_all_buttons()
            self.disable_all_keybinds()
            self.pdf_canvas.delete('all') 
        else:               
            if current_index > 0: # Switch to the file to the left.
                self.pdf_id = self.pdfs.get_keys()[current_index - 1].replace('*','')
                self.update_page(self.pdfs[self.pdf_id].page_i) # Check.
            else: # Switch to the file to the right.
                self.pdf_id = self.pdfs.get_keys()[current_index].replace('*','')
                self.update_page(self.pdfs[self.pdf_id].page_i)
            self.update_file_select()        
    def adjust_scale(self, event):
        """ Process a slider adjustment event. """
        self.scale = self.scale_slider.get() / 4
        self.update_scale()
    def scale_up(self, event):
        """ Process a scale up event. """
        if self.scale < int(self.settings["app_max_zoom_scale"]):
            self.scale += 0.25
            self.scale_slider.set(self.scale_slider.get() + 1)
            self.update_scale()
    def scale_down(self, event):
        """ Process a scale down event. """
        if self.scale > 0.25:
            self.scale -= 0.25
            self.scale_slider.set(self.scale_slider.get() - 1)
            self.update_scale()
    """ ------------------------------------------- File Select Menu ----------------------------------------- """
    def file_selector_callback(self, value):
        """ Change which PDF is being viewed currently. """
        self.pdf_id = value.replace('*', '')
        self.file_selected = value
        self.file_select_bar.set(value)
        self.update_page(self.pdfs[self.pdf_id].page_i)


    """  ==================================== DISPLAY UPDATE FUNCTIONALITY ================================== """
    def update_button_states(self):
        """ Wrapper for set_menu, used in update_page. """
        self.set_menu(self.mode.get())
    def update_file_select(self):
        """ Update the file selection menu bar. """
        if f"*{self.pdf_id}" in self.pdfs.get_keys():
            self.file_select_bar.set(f"*{self.pdf_id}")
            self.file_selected = f"*{self.pdf_id}"
        else:
            self.file_select_bar.set(self.pdf_id)
            self.file_selected = f"{self.pdf_id}"
    def update_scale(self):
        """ Update the zoom scale text and slider. """
        self.update_page(self.pdfs[self.pdf_id].page_i)
        if self.scale < 1:
            self.scale_display.configure(text=f"Zoom:  {self.scale * 100}%") # Has extra space (" ") to account for missing hundreds place digit.
        else:
            self.scale_display.configure(text=f"Zoom: {self.scale * 100}%")
    def update_image(self, img, pix):
        """ Compute and update the PDF page render. """
        self.root.update()
        self.pdf_canvas.pack(side="left", anchor='center', fill='both', expand=True)
        self.pdf_canvas.delete("all") # Start with an empty canvas.

        img = img.resize((int(pix.width * self.scale), int(pix.height * self.scale)), resample=PIL.Image.Resampling.NEAREST) # Resize and prepare the pdf page image.
        self.tkimg = PIL.ImageTk.PhotoImage(img)

        with warnings.catch_warnings(): # Prevent console warning for CTkLabel with non-CTkImage as "image" argument. Solution found at: https://stackoverflow.com/questions/14463277/how-to-disable-python-warnings
            warnings.simplefilter("ignore")
            pic = ctk.CTkLabel(self.pdf_canvas, text="", image = self.tkimg) # Add the pdf page image.

        self.pdf_canvas.configure(width=self.tkimg.width(), height=self.tkimg.height()) # Resize the canvas.
        self.pdf_canvas.create_image(self.pdf_canvas.winfo_width() / 2, 0, image=self.tkimg, anchor="nw", tag="pdf_img") # Add the image to the canvas.
        self.pdf_canvas.xview(MOVETO, 0.0) # Reset the viewing field for the canvas.
        self.pdf_canvas.yview(MOVETO, 0.0)
    def update_drawings(self, page_num):
        """ Redraw all mouse strokes on the page. """
        for pointset in self.pdfs[self.pdf_id].page_points[page_num]:
            scale_adjusted_pointset = [(point[0]*self.scale, point[1]*self.scale) for point in pointset]
            self.pdf_canvas.create_line(scale_adjusted_pointset, fill="red")
    def config_update_image(self):
        """ Update PDF page render without new computations. """
        self.pdf_canvas.delete("all") # Start with an empty canvas.
        self.pdf_canvas.create_image(0, 0, image=self.tkimg, anchor="nw", tag="pdf_img") # Add the image to the canvas.
        self.pdf_canvas.xview(MOVETO, 0.0) # Reset the viewing field for the canvas.
        self.pdf_canvas.yview(MOVETO, 0.0)
    def update_page(self, page_num): 
        """ Update the entire GUI for a page change. """
        # Select the page and load it as an image.
        page = self.pdfs[self.pdf_id].doc[page_num]
        self.pix = page.get_pixmap()
        if self.pix.alpha:
            mode = "RGBA"
        else:
            mode = "RGB"
        self.img = PIL.Image.frombytes(mode, [self.pix.width, self.pix.height], self.pix.samples)
        self.update_image(self.img, self.pix)
        self.config_update_image()

        # Configure the Menu Buttons (MB 1-4).
        if self.pdfs[self.pdf_id].page_i == 0: # Prevent scrolling left on first page.
            self.menus["Pages"].states[0] = False
        else:
            self.menus["Pages"].states[0] = True

        if self.pdfs[self.pdf_id].page_i == (len(self.pdfs[self.pdf_id].doc)-1): # Prevent scrolling right on last page.
            self.menus["Pages"].states[1] = False
        else:
            self.menus["Pages"].states[1] = True

        if len(self.pdfs[self.pdf_id].doc) == 1: # Prevent last page deletion.
            self.menus["Pages"].states[2] = False
        else:
            self.menus["Pages"].states[2] = True

        if self.pdfs[self.pdf_id].password == None or self.pdfs[self.pdf_id].password == "": # Prevent setting/removing password if exists/missing.
            self.menus["Encrypt & Compress"].states[0] = True
            self.menus["Encrypt & Compress"].states[1] = False
        else:
            self.menus["Encrypt & Compress"].states[0] = False
            self.menus["Encrypt & Compress"].states[1] = True

        # Configure the page number.
        try:
            self.page_count.configure(text=f"Page: {self.pdfs[self.pdf_id].page_i + 1}/{len(self.pdfs[self.pdf_id].doc)}")
            self.update_button_states()
        except:
            pass
        self.update_drawings(page_num)


    """ ======================================= MENU BUTTON FUNCTIONALITY ====================================== """
    """ -------------------------------------------------- Pages ------------------------------------------------ """
    def event_rotate_left(self, *args):
        """ Rotate the page left by 90 degrees. """
        self.set_unsaved() # A modification has been made to the document.
        rotater = Page_Rotate_PDF(self.pdfs[self.pdf_id].doc, None)
        rotater.rotate_l(self.pdfs[self.pdf_id].page_i)
        self.pdfs[self.pdf_id].doc = rotater.get()
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_rotate_right(self, *args):
        """ Rotate the page right by 90 degrees. """
        self.set_unsaved() # A modification has been made to the document.
        rotater = Page_Rotate_PDF(self.pdfs[self.pdf_id].doc, None)
        rotater.rotate_r(self.pdfs[self.pdf_id].page_i)
        self.pdfs[self.pdf_id].doc = rotater.get()
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_move_up(self, *args):
        """ Move the current page up (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        if self.pdfs[self.pdf_id].page_i > 0:
            mover = Page_Move_PDF(self.pdfs[self.pdf_id].doc, None)
            mover.move(self.pdfs[self.pdf_id].page_i, self.pdfs[self.pdf_id].page_i - 1)
            self.pdfs[self.pdf_id].doc = mover.get()
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_move_down(self, *args):
        """ Move the current page down (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        if self.pdfs[self.pdf_id].page_i < len(self.pdfs[self.pdf_id].doc):
            mover = Page_Move_PDF(self.pdfs[self.pdf_id].doc, None)
            mover.move(self.pdfs[self.pdf_id].page_i+1, self.pdfs[self.pdf_id].page_i)
            self.pdfs[self.pdf_id].doc = mover.get()
            self.update_page(self.pdfs[self.pdf_id].page_i)
    """ -------------------------------------------- Encrypt & Compress ----------------------------------------- """
    def event_set_encryption(self, *args):
        """ Set Encryption Password for PDF (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        p1 = ""
        p2 = ""
        pass_dialog = ctk.CTkInputDialog(text="Password", title="Create Password")
        p1 = pass_dialog.get_input()
        if p1 == None:
            return
        pass_dialog2 = ctk.CTkInputDialog(text="Confirm Password", title="Create Password")
        p2 = pass_dialog2.get_input()
        if p2 == None:
            return

        if p1 == p2 and p1!= "":
            self.pdfs[self.pdf_id].password = p1
            self.menus["Encrypt & Compress"].states[0] = False
            self.menus["Encrypt & Compress"].states[1] = True
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_remove_encryption(self, *args):
        """ Remove Encryption Password for PDF (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        self.pdfs[self.pdf_id].password = None
        self.menus["Encrypt & Compress"].states[0] = True
        self.menus["Encrypt & Compress"].states[1] = False
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_compress(self, *args):
        """ Add basic compression to PDF (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        if self.pdfs[self.pdf_id].compress_basic == False:
            self.pdfs[self.pdf_id].compress_basic = True
            self.menu_button_3.configure(text="Remove Compression")
        else:
            self.pdfs[self.pdf_id].compress_basic = False
            self.menu_button_3.configure(text="Compress")
    def event_compress_max(self, *args):
        """ Add basic and maximum compression to PDF (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        if self.pdfs[self.pdf_id].compress_max == False:
            self.pdfs[self.pdf_id].compress_basic = True
            self.pdfs[self.pdf_id].compress_max = True
            self.menu_button_3.configure(text="Remove Compression")
            self.menu_button_3.configure(state="disabled")
            self.menus["Encrypt & Compress"].states[2] = False
            self.menu_button_4.configure(text="Remove Compression")
        else:
            self.pdfs[self.pdf_id].compress_basic = False
            self.pdfs[self.pdf_id].compress_max = False
            self.menu_button_3.configure(text="Compress")
            self.menu_button_3.configure(state="normal")
            self.menus["Encrypt & Compress"].states[2] = True
            self.menu_button_4.configure(text="Compress (Max)")
    """ -------------------------------------------------- Insert ------------------------------------------------- """
    def event_insert_pdf(self, *args):
        """ Insert another PDF (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        merge_fp = open_pdf()[1]
        if merge_fp != None and merge_fp != "":
            merger = PDF_Merger(self.pdfs[self.pdf_id].doc)
            merger.add_fitz_doc(merge_fp, self.pdfs[self.pdf_id].page_i)
            self.pdfs[self.pdf_id].doc = merger.get()
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_insert_page(self, *args):
        """ Insert a blank page (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        inserter = Page_Insert_Blank_PDF(self.pdfs[self.pdf_id].doc, None)
        inserter.insert(self.pdfs[self.pdf_id].page_i)
        self.pdfs[self.pdf_id].doc = inserter.get()
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_watermark_page(self, *args):
        """ Watermark the current page. """
        self.set_unsaved() # A modification has been made to the document.
        watermarker = Watermark_PDF(self.pdfs[self.pdf_id].doc, None)
        watermarker.watermark(self.pdfs[self.pdf_id].page_i, gui_get_file(limit_filetypes=[("PNG",".png"), ("JPEG",".jpg")])[0])
        self.pdfs[self.pdf_id].doc = watermarker.get()
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_watermark_document(self, *args):
        """ Watermark all pages. """
        self.set_unsaved() # A modification has been made to the document.
        watermarker = Watermark_PDF(self.pdfs[self.pdf_id].doc, None)
        watermarker.watermark(self.pdfs[self.pdf_id].page_i, gui_get_file(limit_filetypes=[("PNG",".png"), ("JPEG",".jpg")])[0], all_pages=True)
        self.pdfs[self.pdf_id].doc = watermarker.get()
        self.update_page(self.pdfs[self.pdf_id].page_i)
    """ -------------------------------------------------- Extract ------------------------------------------------ """
    def event_delete(self, *args):
        """ Delete the current page (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        deleter = Page_Delete_PDF(self.pdfs[self.pdf_id].doc, None)
        deleter.delete(self.pdfs[self.pdf_id].page_i)
        self.pdfs[self.pdf_id].doc = deleter.get()
        if self.pdfs[self.pdf_id].page_i ==  len(self.pdfs[self.pdf_id].doc):
            self.pdfs[self.pdf_id].page_i -= 1
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_extract_text(self, *args):
        """ Extract text from the PDF to a .txt (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        fname_dialog = ctk.CTkInputDialog(text="File Name", title="Extract Text")
        fname = fname_dialog.get_input()
        if fname != None and fname.strip() != "":
            extractor = PDF_Extractor(self.pdfs[self.pdf_id].doc)
            extractor.extract_text(fname)
            subprocess.Popen(f'explorer "{os.getcwd()}"') # Open file explorer to the folder location.
    def event_extract_images(self, *args):
        """ Extract images from the PDF to a folder (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        foldername_dialog = ctk.CTkInputDialog(text="Folder Name", title="Extract Images")
        foldername = foldername_dialog.get_input()
        if foldername != None and foldername.strip() != "":
            extractor = PDF_Extractor(self.pdfs[self.pdf_id].doc)
            extractor.extract_images(foldername)
            subprocess.Popen(f'explorer "{os.getcwd()}"') # Open file explorer to the folder location.
    def event_screenshot_page(self, *args):
        """ Save a screenshot of the current PDF page (Button Event). """
        self.set_unsaved() # A modification has been made to the document.
        fname_dialog = ctk.CTkInputDialog(text="File Name", title="Screenshot Page")
        fname = fname_dialog.get_input()
        if fname != None and fname.strip() != "":
            fname.replace(".png", "").replace(".PNG", "")
            fname += ".png"
            page = self.pdfs[self.pdf_id].doc[self.pdfs[self.pdf_id].page_i]
            pix = page.get_pixmap()
            pix.save(fname)
            subprocess.Popen(f'explorer "{os.getcwd()}"') # Open file explorer to the folder location.
    """ ------------------------------------------------- Meta Data ----------------------------------------------- """
    def event_set_meta_author(self, *args):
        """ Set the metadata "author" tag. """
        self.set_unsaved() # A modification has been made to the document.
        author_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Author: ")
        author = author_dialog.get_input()
        if author.strip() != "":
            self.pdfs[self.pdf_id].custom_metadata["author"] = author.strip()
    def event_set_meta_title(self, *args):
        """ Set the metadata "title" tag. """
        self.set_unsaved() # A modification has been made to the document.
        title_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Author: ")
        title = title_dialog.get_input()
        if title.strip() != "":
            self.pdfs[self.pdf_id].custom_metadata["title"] = title.strip()
    def event_set_meta_subject(self, *args):
        """ Set the metadata "subject" tag. """
        self.set_unsaved() # A modification has been made to the document.
        subject_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Subject: ")
        subject = subject_dialog.get_input()
        if subject.strip() != "":
            self.pdfs[self.pdf_id].custom_metadata["subject"] = subject.strip()
    def event_set_meta_keywords(self, *args):
        """ Set the metadata "keywords" tag. """
        self.set_unsaved() # A modification has been made to the document.
        keywords_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Keywords: ")
        keywords = keywords_dialog.get_input()
        if keywords.strip() != "":
            self.pdfs[self.pdf_id].custom_metadata["keywords"] = keywords.strip()
    """ -------------------------------------------------- Signature ----------------------------------------------- """
    def event_sign_pdf(self, *args):
        """ Sign a selected PDF with the current Signer Account key file and the necessary password. """
        if self.pdfs[self.pdf_id].mods_made != False:
            self.save_path = save_pdf(self.pdfs[self.pdf_id].doc, self.pdfs[self.pdf_id].custom_metadata, self.pdfs[self.pdf_id].page_points, self.pdfs[self.pdf_id].compress_basic, self.pdfs[self.pdf_id].compress_max, self.pdfs[self.pdf_id].password, dialog_text = "Filename", dialog_title="Save a Copy to Sign",forced_save = True)
            self.set_saved()

        sig_dir = f"PDF Signatures/{self.save_path.split('/')[-1].replace('.pdf', '')}"
        if not os.path.exists(sig_dir):
            os.makedirs(sig_dir)

        status = sign_pdf(f"{sig_dir}/{self.signer}.sig", self.save_path, self.signer, ctk.CTkInputDialog(text=f"Password for {self.signer}", title="Sign PDF").get_input(), self.signer_private_key_path)
        self.create_popup("PDF Signature Creation Status", status, "OK")
    def event_verify_signature(self, *args):
        """ Verify a signature file (.sig) using a selected PDF and the public key from storage.  """
        signed_pdf = gui_get_file(limit_filetypes=[("PDF", ".pdf")])[0]
        if signed_pdf != "":
            signature_file = gui_get_file(limit_filetypes=[("SIG", ".sig")])[0]
            if signature_file != "":
                signer = signature_file.split("/")[-1].replace(".sig", "")
                status = verify_pdf_signature(signature_file, signed_pdf, f"{self.settings['pubkey_storage_base']}{signer}.pem", signer)
                self.create_popup("PDF Signature Verification Status", status, "OK")
    def event_add_signer_account(self, *args):
        """ Create the public and private keys necessary for PDF signature. """
        uname = None
        pwd = None
        pwd_verify = None
        while uname == None or uname.strip() == "": # Get a username for the Signer Account.
            uname_dialog = ctk.CTkInputDialog(text="Username", title="Add Signer Account")
            uname = uname_dialog.get_input()
        while pwd != pwd_verify or (pwd == None or pwd.strip() == ""): # Get and confirm a password for the Signer Account.
            pwd = ctk.CTkInputDialog(text="Password", title="Add Signer Account").get_input()
            pwd_verify = ctk.CTkInputDialog(text="Password (confirm)", title="Add Signer Account").get_input()
        self.signer_private_key_path = gen_signature_keys(f"{self.settings['pubkey_storage_base']}{uname}.pem", uname, pwd)[1] # Create and register the two keys.
        self.signer = uname
        self.menus["Signatures"].states[0] = True
        self.update_button_states()
    def event_select_signer_account(self, *args):
        """ Select a key file (.pem) file for a Signer Account. """
        self.signer_private_key_path = gui_get_file(limit_filetypes=[("PEM", ".pem")])[0]
        if self.signer_private_key_path != "":
            self.signer = os.path.split(self.signer_private_key_path)[-1].replace("_private_key.pem", "")
            self.menus["Signatures"].states[0] = True
            self.update_button_states()


    """ ===================================================== Drawing ================================================== """
    def mouse_add_coords(self, event): # Add to a click stroke.
        """ Add a point to the path of the current mouse stroke. """
        self.pdfs[self.pdf_id].active_stroke.append((self.pdf_canvas.canvasx(event.x)/self.scale, self.pdf_canvas.canvasy(event.y)/self.scale))
        if len(self.pdfs[self.pdf_id].active_stroke) > 1:
            scale_adjusted_stroke = [(stroke[0]*self.scale, stroke[1]*self.scale) for stroke in self.pdfs[self.pdf_id].active_stroke]
            self.pdf_canvas.create_line(scale_adjusted_stroke, fill="red")
    def mouse_set_end(self, event): # End of a click stroke.
        """ End the current mouse stroke. """
        if len(self.pdfs[self.pdf_id].active_stroke) > 1:
            self.pdfs[self.pdf_id].page_points[self.pdfs[self.pdf_id].page_i].append(self.pdfs[self.pdf_id].active_stroke)
            scale_adjusted_stroke = [(stroke[0]*self.scale, stroke[1]*self.scale) for stroke in self.pdfs[self.pdf_id].active_stroke]
            self.pdf_canvas.create_line(scale_adjusted_stroke, fill="red")
            self.set_unsaved() # A modification has been made to the document.
        self.pdfs[self.pdf_id].active_stroke = []