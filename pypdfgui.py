"""
    Author: lefkovitj (https://lefkovitzj.com)
    File Last Modified: 8/28/2025
    Project Name: PyPdfApp
    File Name: pypdfgui.py
"""

# Python Standard Library Imports.
import json
import math
import os
import subprocess
import sys
from tkinter import *
from tkinter import ttk
import warnings
import webbrowser
import threading

# Third-party Module Imports.
import customtkinter as ctk
import pymupdf
import PIL
import requests

# Project Imports.
from gui import GuiMenu
from load import open_pdf
from manipulate import (
    create_blank_pdf,
    gui_get_file,
    PageDeletePDF,
    PageInsertBlankPDF,
    PageMovePDF,
    PageRotatePDF,
    WatermarkPDF,
    PdfExtractor,
    PdfMerger
)
from save import save_pdf
from sign import gen_signature_keys, sign_pdf, verify_pdf_signature
from utils import PdfDocInstance, PdfQueue


def on_enter(_event, canvas, rect, set_color):
    """Update color of canvas rectangle on mouse hover enter.  """
    canvas.itemconfig(rect, outline=set_color)
    canvas.update()

def on_leave(_event, canvas, rect, set_color):
    """Update color of canvas rectangle on mouse hover exit.  """
    canvas.itemconfig(rect, outline=set_color)
    canvas.update()


class App():
    """ The primary GUI used by PyPdfApp """
    #  APPLICATION STARTUP
    def __init__(self):
        """Internal Application Data & Settings """
        self.pdfs = PdfQueue()
        self.pdf_id = None
        self.file_selected = ""
        self.signer_private_key_path = None
        self.signer = None
        self.scale = 1.0
        self.link_images = [] # Must be kept otherwise the link icon flashes in and out.
        self.thread = None

        # Define attributes for later initialization.
        self.tkimgs = None
        self.save_path = None
        self.tkimg = None
        self.redact_toggle = None
        self.freehand_start_bind = None
        self.freehand_end_bind = None
        self.redact_start_bind = None
        self.redact_end_bind = None
        self.highlight_toggle = None
        self.highlight_start_bind = None
        self.highlight_end_bind = None
        self.active_highlight_start = None
        # Get the settings file data.
        with open("settings.json", "r", encoding="utf-8") as json_settings:
            self.settings = json.load(json_settings)
        # Startup checks.
        self.needs_update = self.on_startup_update_check()
        self.license_agreed = self.on_startup_license_check()

        """Application GUI - Layout & Contents """
        # Create the GUI window.
        self.root = ctk.CTk(fg_color="#333333")
        ctk.set_default_color_theme("blue")
        ctk.set_appearance_mode("Dark")

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
        self.mode = ctk.CTkOptionMenu(
            self.menu,
            values=[
                "File",
                "Pages",
                "Encrypt & Compress",
                "Insert",
                "Extract",
                "Meta Data",
                "Signatures",
                "Markup"],
            command=self.set_menu,
            width=175)
        self.mode.grid(row=0, column=0, columnspan=2, padx=5)
        self.prev = ctk.CTkButton(self.menu, text = "<", command = self.previous_page, width = 25)
        self.next = ctk.CTkButton(self.menu, text = ">", command = self.next_page, width = 25)
        self.prev.grid(row = 0, column = 2, padx=5)
        self.next.grid(row = 0, column = 3, padx=5)

        # Add the middle menu content (buttons).
        self.menu_button_1 = ctk.CTkButton(self.submenu, text=" ",  command = lambda: print(""))
        self.menu_button_1.grid(row = 0, column=0, columnspan=3, padx=5, pady=10, sticky="nsew")
        self.menu_button_2 = ctk.CTkButton(self.submenu, text=" ", command = lambda: print(""))
        self.menu_button_2.grid(row = 0,column=3, columnspan=3, padx=5, pady=10, sticky="nsew")
        self.menu_button_3 = ctk.CTkButton(self.submenu, text=" ", command = lambda: print(""))
        self.menu_button_3.grid(row = 0,column=6, columnspan=3, padx=5, pady=10, sticky="nsew")
        self.menu_button_4 = ctk.CTkButton(self.submenu, text=" ", command = lambda: print(""))
        self.menu_button_4.grid(row = 0,column=9, columnspan=3, padx=5, pady=10, sticky="nsew")

        # Add the Edit Settings area.
        self.settings_frame = ctk.CTkFrame(self.menu_middle, height=25)
        #self.settings_frame.pack(anchor="nw", fill='x', expand=True)


        # Open bottom menu (file selector).
        self.file_menu = ctk.CTkFrame(self.menu_middle)
        self.file_menu.pack(anchor="ne", fill="x", expand=True)

        for i in range(11): # Configure the resizeable grid columns.
            self.file_menu.columnconfigure(i, weight=1)
        self.file_select_bar = ctk.CTkSegmentedButton(
            self.file_menu,
            command=self.file_selector_callback,
            width=self.file_menu.winfo_width())
        self.file_select_bar.grid(
            row=0,
            column=0,
            padx=(0, 0),
            pady=(10, 10),
            columnspan=12,
            sticky="ew")
        self.file_select_bar.configure(values=self.pdfs.get_keys())
        self.root.update()
        self.mode.configure(width=self.root.winfo_width()/4 - 10)

        # Add the Page Quickselect area.
        self.page_quickset_frame = ctk.CTkFrame(self.root, width=150, fg_color="#333333")

        # Zoom controls.
        self.scale_frame = ctk.CTkFrame(self.page_quickset_frame, fg_color = "transparent")
        self.scale_frame.pack()
        self.zoom_minus = ctk.CTkButton(
            self.scale_frame,
            text = "-",
            command = self.scale_down,
            width = 25)
        self.zoom_minus.grid(row=0, column = 0, padx=5)
        self.scale_display = ctk.CTkLabel(
            self.scale_frame,
            text = "Zoom: 100%",
            fg_color = "transparent")
        self.scale_display.grid(row=0, column=1, padx=5)
        self.zoom_plus = ctk.CTkButton(
            self.scale_frame,
            text = "+",
            command = self.scale_up,
            width = 25)
        self.zoom_plus.grid(row=0, column = 2, padx=5)

        separator = ttk.Separator(self.scale_frame, orient='horizontal')
        separator.grid(sticky="ew", columnspan=3, pady = 25)


        # Page Quickselect Images.
        self.page_count = ctk.CTkLabel(
            self.page_quickset_frame,
            text = "page x/x",
            fg_color = "transparent")
        if self.pdfs.is_empty():
            self.page_count.configure(text="Page: 0/0")
        else:
            self.page_count.configure(
                text=(
                    f"Page: {self.pdfs[self.pdf_id].page_i+1}"
                    f"/{len(self.pdfs[self.pdf_id].doc)}")
                )
        self.page_count.pack()

        self.page_quickset_frame.pack(
            anchor="center",
            fill='both',
            expand=False,
            side="left",
            padx=(0,20))
        self.quickset_canvas = Canvas(self.page_quickset_frame, bg="#333333", highlightthickness=0)
        self.quickset_canvas.pack(side="left", anchor='center', fill='both', expand=True)
        self.quickset_scrollbar = ctk.CTkScrollbar(
            self.page_quickset_frame,
            orientation="vertical",
            fg_color="#333333")
        self.quickset_scrollbar.pack(side="right", fill="y")
        self.quickset_scrollbar.configure(command=self.quickset_canvas.yview)
        self.quickset_canvas.configure(yscrollcommand=self.quickset_scrollbar.set)

        # Add the PDF render area, with vertical and horizontal scrollbars and the canvas.
        self.canvas_frame = ctk.CTkFrame(self.root, width=290)
        self.canvas_frame.pack(anchor="center", fill='both', expand=True, side="left")
        self.pdf_canvas = Canvas(self.canvas_frame, bg="#333333", highlightthickness=0)
        self.canvas_frame.bind(
            "<Configure>",
            lambda e: self.pdf_canvas.configure(scrollregion=self.pdf_canvas.bbox("all")))
        self.scrollbar = ctk.CTkScrollbar(
            self.canvas_frame,
            orientation="vertical",
            fg_color="#333333")
        self.scrollbar.pack(side="right", fill="y")
        self.scrollbar.configure(command=self.pdf_canvas.yview)
        self.h_scrollbar = ctk.CTkScrollbar(
            self.canvas_frame,
            orientation="horizontal",
            fg_color="#333333")
        self.h_scrollbar.pack(side="bottom", fill="x")
        self.h_scrollbar.configure(command=self.pdf_canvas.xview)
        self.pdf_canvas.configure(
            yscrollcommand=self.scrollbar.set,
            xscrollcommand=self.h_scrollbar.set)
        self.pdf_canvas.pack(side="left", anchor='center', fill='both', expand=True)


        # Startup Checks - Update & License.
        # Application update screen.
        if self.needs_update:
            self.update_area = ctk.CTkFrame(self.root)
            self.update_area.place(anchor="nw", relheight=1.0, relwidth=1.0)
            ctk.CTkLabel(
                self.update_area,
                text = "Your software is not up to date. A new version is available!",
                fg_color = "transparent"
            ).pack()
            textbox = ctk.CTkTextbox(self.update_area)
            textbox.insert(
                0.0,
                ("Your software is no longer up to date. Software updates "
                 "are strongly encouraged. \nWhile this version should "
                 "continue to operate, you will potentially be missing "
                 "out on:\n  1. New application features.\n  2. Security "
                 "updates.\n  3. Critical bug fixes.\n  4. Improved "
                 "application efficiency.\n\nBy continuing to use this "
                 "version of PyPdfApp you may experience some of the "
                 "following issues:\n  1. Unexpected program crashes.\n  "
                 "2. User interface glitches.\n  3. Functionality failures.\n "
                 " 4. Possible corruption of PDF files. \n\n To ensure "
                 "you are using the most recent version of PyPdfApp, select "
                 "'Open browser for update'. \nFrom there, you can download "
                 "the newest version of PyPdfApp avaialable! "))
            textbox.configure(state="disabled")
            textbox.pack(anchor="nw", fill="both", expand=True)
            ctk.CTkButton(
                self.update_area,
                text="Open browser for update.",
                command = self.update_web_event
            ).pack(side="right")
            ctk.CTkButton(
                self.update_area,
                text="Continue without update.",
                command = self.update_skip_event
            ).pack(side="left")
        # Application license agreement screen.
        if not self.license_agreed:
            self.license_area = ctk.CTkFrame(self.root)
            self.license_area.place(anchor="nw", relheight=1.0, relwidth=1.0)
            ctk.CTkLabel(
                self.license_area,
                text = "You must agree to the MIT license to continue!",
                fg_color = "transparent"
            ).pack(anchor="nw", fill="x")
            with open("license.txt", "r", encoding="utf-8") as license_doc:
                license_text = license_doc.read()
            textbox = ctk.CTkTextbox(self.license_area)
            textbox.insert(0.0, license_text)
            textbox.configure(state="disabled")
            textbox.pack(anchor="nw", fill="both", expand=True)
            ctk.CTkButton(
                self.license_area,
                text="I agree to the MIT License.",
                command = self.license_agree_event
            ).pack(anchor="nw", fill="x", side="right")

        # Initial Configuration - Window, Binds, and Graphics.
        # Set window title.
        self.root.title("PyPdfApp")
        # Set window close functionality.
        if bool(self.settings["ask_save_before_exit"]):
            # Add on-exit "Are you sure?" event.
            self.root.protocol("WM_DELETE_WINDOW", self.app_exit_event)
        # Binds.
        self.enable_all_keybinds()
        self.root.bind("<Control-o>", self.open_new_pdf)
        self.root.bind("<Control-n>", self.open_blank_pdf)

        # Load the menu data.
        self.menus = {
            "File": GuiMenu(
                "File",
                ["New", "Open", "Save", "Close"],
                [self.open_blank_pdf, self.open_new_pdf, self.save_event, self.close_current_pdf],
                [True, True, False, False]),
            "Encrypt & Compress": GuiMenu(
                "Encryption",
                ["Set Encryption", "Remove Encryption", "Compress", "Compress (max)"],
                [
                    self.event_set_encryption,
                    self.event_remove_encryption,
                    self.event_compress,
                    self.event_compress_max
                ],
                [True, True, True, True]),
            "Pages": GuiMenu(
                "Pages",
                ["Move up", "Move down", "Rotate right", "Rotate left"],
                [
                    self.event_move_up,
                    self.event_move_down,
                    self.event_rotate_right,
                    self.event_rotate_left
                ],
                [True, True, True, True]),
            "Meta Data": GuiMenu(
                "Meta Data",
                ["Set Author", "Set Title", "Set Subject", "Add Keywords"],
                [
                    self.event_set_meta_author,
                    self.event_set_meta_title,
                    self.event_set_meta_subject,
                    self.event_set_meta_keywords
                ],
                [True, True, True, True]),
            "Insert": GuiMenu(
                "Insert",
                ["Insert PDF", "Insert Blank", "Watermark page", "Watermark document"],
                [
                    self.event_insert_pdf,
                    self.event_insert_page,
                    self.event_watermark_page,
                    self.event_watermark_document
                ],
                [True, True, True, True]),
            "Extract": GuiMenu(
                "Extract",
                ["Delete page", "Extract text", "Extract images", "Screenshot Page"],
                [
                    self.event_delete,
                    self.event_extract_text,
                    self.event_extract_images,
                    self.event_screenshot_page
                ],
                [True, True, True, True]),
            "Signatures": GuiMenu(
                "Signatures",
                ["Sign PDF", "Verfiy Signature", "Add Signer Account", "Select Signer Account"],
                [
                    self.event_sign_pdf,
                    self.event_verify_signature,
                    self.event_add_signer_account,
                    self.event_select_signer_account
                ],
                [False, True, True, True]),
            "Markup": GuiMenu(
                "Markup",
                ["Freehand Draw", "Link Editor", "Redact", "Highlight"],
                [
                    self.event_toggle_freehand_draw,
                    self.event_toggle_link_editor,
                    self.event_toggle_redact,
                    self.event_toggle_highlight
                ],
                [True, True, True, True]),
        }
        # Set initial menu value.
        self.menu = None
        self.mode.set("File")
        self.set_menu("File")
        self.freehand_draw_toggle = False
        self.link_editor_toggle = False
        self.redact_toggle = False
        self.active_redact_start = (None, None)
        self.highlight_toggle = False

        # Render the starting screen contents.
        if not self.pdfs.is_empty(): # Load the first page if a document is specified.
            self.update_page(0)
        else: # No document open, disable all actions that require an open PDF.
            self.disable_all_buttons()
            self.disable_all_keybinds()
        self.root.update()
        # Set window minimum dimensions.
        self.root.minsize(int(self.root.geometry().split("x")[0]), 250)
        self.root.update()
        # Start the main application loop.
        self.root.mainloop()



    # ASSORTED APPLICATION FUNCTIONALITY
    # Buttons & Keybinds
    def disable_all_buttons(self, *_args):
        """Disable all buttons related to manipulating a PDF. Used when no PDF is open"""
        if self.mode.get() != "File":
            self.menu = self.menus["File"]
        self.menu_button_1.configure(state="normal")
        self.menu_button_2.configure(state="normal")
        self.menu_button_3.configure(state="disabled")
        self.menu_button_4.configure(state="disabled")
        self.next.configure(state="disabled")
        self.prev.configure(state="disabled")
        self.zoom_plus.configure(state="disabled")
        self.zoom_minus.configure(state="disabled")
        self.mode.configure(state="disabled")
    def enable_all_buttons(self, *_args):
        """Disable all buttons related to manipulating a PDF. Used when no PDF is open"""
        self.menu_button_1.configure(state="normal")
        self.menu_button_2.configure(state="normal")
        self.menu_button_3.configure(state="normal")
        self.menu_button_4.configure(state="normal")
        self.next.configure(state="normal")
        self.prev.configure(state="normal")
        self.zoom_plus.configure(state="normal")
        self.zoom_minus.configure(state="normal")
        self.mode.configure(state="normal")
    def disable_all_keybinds(self, *_args):
        """Disable all keybinds that require an open PDF. Used when no PDF is open"""
        if bool(self.settings["allow_keyboard_events"]):
            self.root.unbind("<Control-s", self.bind_save)
            self.root.unbind("<Left>", self.bind_prev_page)
            self.root.unbind("<Right>", self.bind_next_page)
            self.root.unbind("Control-Key-plus>", self.bind_zoom_out)
            self.root.unbind("Control-Key-minus>", self.bind_zoom_in)
            self.root.unbind("<Control-w>",self.bind_close)

        self.pdf_canvas.unbind("<B1-Motion>")
        self.pdf_canvas.unbind("<ButtonRelease-1>")

        self.quickset_canvas.unbind("<Button-1>")
        self.quickset_canvas.unbind("<MouseWheel>")
    def enable_all_keybinds(self, *_args):
        """Enable all keybinds that require an open PDF. Used when the first PDF is (re)opened"""
        if bool(self.settings["allow_keyboard_events"]):
            self.bind_save = self.root.bind("<Control-s>", self.save_event)
            self.bind_prev_page = self.root.bind("<Left>", self.previous_page)
            self.bind_next_page = self.root.bind("<Right>", self.next_page)
            self.bind_zoom_out = self.root.bind("<Control-Key-plus>", self.scale_up)
            self.bind_zoom_in = self.root.bind("<Control-Key-minus>", self.scale_down)
            self.bind_close = self.root.bind("<Control-w>", self.close_current_pdf)

        self.freehand_start_bind = self.pdf_canvas.bind(
            "<B1-Motion>",
            self.freehand_mouse_add_coords)
        self.freehand_end_bind = self.pdf_canvas.bind(
            "<ButtonRelease-1>",
            self.freehand_mouse_set_end)
        self.quickset_canvas.bind("<Button-1>", self.quickset_canvas_clicked)
        self.quickset_canvas.bind("<MouseWheel>", self.quickset_on_mousewheel)

    def link_edit_popup(self, _event, rect, initial_url):
        """Create a popup window with contents defined by the args"""
        popup = ctk.CTkToplevel(self.root)
        popup.title("PyPdfApp")
        # Add content to the popup
        popup_title_label = ctk.CTkLabel(popup, text="")
        popup_title_label.pack(padx=20, pady=20)
        url_input = ctk.CTkEntry(popup)
        url_input.insert(0, initial_url)
        url_input.pack()
        label = ctk.CTkLabel(popup, text="")
        label.pack(padx=20, pady=20)
        popup.grab_set()

        save_button = ctk.CTkButton(
            popup,
            text="Update Link",
            command=lambda: self.process_link_update(rect, popup, url_input))
        save_button.pack(pady=0, side="right")
        close_button = ctk.CTkButton(popup, text="Cancel Changes", command=popup.destroy)
        close_button.pack(pady=0, side="left")

    def on_click(self, _event, rect):
        """Handle click of URL"""
        mydoc = self.pdfs[self.pdf_id].doc
        mypage = self.pdfs[self.pdf_id].page_i
        for page_i, page in enumerate(mydoc):
            if page_i == mypage:
                for link in page.get_links():
                    if str([corner * self.scale for corner in list(link["from"])]) == rect:
                        webbrowser.open(link["uri"])
    def process_link_update(self, rect, popup, url_input):
        """Parse a link update event with a new URL"""
        for page_link in self.pdfs[self.pdf_id].doc[self.pdfs[self.pdf_id].page_i].links():
            if str([corner * self.scale for corner in list(page_link["from"])]) == rect:
                page_link["uri"] = url_input.get()
                self.pdfs[self.pdf_id].doc[self.pdfs[self.pdf_id].page_i].update_link(page_link)
        self.pdfs[self.pdf_id].doc.reload_page(
            self.pdfs[self.pdf_id].doc[self.pdfs[self.pdf_id].page_i])
        self.set_unsaved()
        popup.destroy()
    def create_popup(self, popup_title, popup_text, popup_close_message):
        """Create a popup window content dictated by arguments"""
        popup = ctk.CTkToplevel(self.root)
        popup.title("PyPdfApp")
        # Add content to the popup
        popup_title_label = ctk.CTkLabel(popup, text=popup_title)
        popup_title_label.pack(padx=20, pady=20)
        label = ctk.CTkLabel(popup, text=popup_text)
        label.pack(padx=20, pady=20)
        button = ctk.CTkButton(
            popup,
            text=popup_close_message,
            command=popup.destroy)
        button.pack(pady=10)
    def window_close_popup(self):
        """Create a popup to offer a chance to save and exit"""
        unsaved = self.pdfs.get_unsaved()
        if unsaved:
            popup = ctk.CTkToplevel(self.root)
            popup.title("PyPdfApp - Save & Exit")
            # Add content to the popup
            title_label = ctk.CTkLabel(popup, text="Save changes before leaving?")
            title_label.pack(padx=20, pady=10)
            label = ctk.CTkLabel(
                popup,
                text=f"You have unsaved changes in the following files: \n{','.join(unsaved)}")
            label.pack(padx=20, pady=10, fill="x")
            back_button = ctk.CTkButton(
                popup,
                text="Go back",
                command=popup.destroy)
            back_button.pack(pady=0, side="left")
            exit_button = ctk.CTkButton(
                popup,
                text="Close anyway",
                command=sys.exit) # Close button.
            exit_button.pack(pady=0, side="right")
            popup.resizable(False, False)
            popup.grab_set()
        else:
            sys.exit()

    # Save Status
    def set_saved(self):
        """Update the file and GUI for a save event"""
        if self.pdfs[self.pdf_id].mods_made:
            self.pdfs.set_saved(self.pdf_id)
            self.file_select_bar.configure(values=self.pdfs.get_keys())
            self.update_file_select()
    def set_unsaved(self):
        """Update the file and GUI for a new modification"""
        if not self.pdfs[self.pdf_id].mods_made:
            self.pdfs.set_unsaved(self.pdf_id)
            self.file_select_bar.configure(values=self.pdfs.get_keys())
            self.update_file_select()
    # Boolean Checks
    def has_open_pdf(self, *_args):
        """Return True if a PDF is open in the GUI"""
        try:
            return isinstance(self.pdfs[self.pdf_id], PdfDocInstance)
        except:
            return False


    # STARTUP CHECKS FUNCTIONALITY
    # Update
    def on_startup_update_check(self):
        """Verify that the software is up to date with the most recent version"""
        # Load from settings.json's data.
        settings_url = self.settings["newest_version_settings_url"]
        version = self.settings["version"]
        try:
            # Get the data at "newest_version_settings_url" as JSON data.
            url_data = requests.get(settings_url, timeout=10).json()
            if url_data["version"] != version:
                return True
            return False
        except: # Request failed due to lack of internet connection or missing online file.
            return False
    def update_skip_event(self):
        """Process an update skip button event"""
        try: # Frame exists, destroy it and its contents.
            self.update_area.destroy()
        except: # Frame was not created, should never happen unless source code is tampered with.
            pass
    def update_web_event(self):
        """Process an web update button event"""
        webbrowser.open(self.settings["newest_version_url"])
        sys.exit()
    # License
    def on_startup_license_check(self):
        """Verify that the user has already agreed to the MIT License terms and conditions"""
        if self.settings["license_agreed_to"] is True: # The license has been agreed to.
            return True
        return False
    def license_agree_event(self):
        """Process a license agreement button event"""
        try: # Frame exists, destroy it and its contents.
            self.license_area.destroy()
            self.settings["license_agreed_to"] = True
            with open("settings.json", "w", encoding="utf-8") as json_settings:
                json.dump(self.settings, json_settings, indent=4)
                json_settings.save()
        except: # Frame was not created, should never happen unless source code is tampered with.
            pass


    # MENU FUNCTIONALITY
    # Window Exit Event
    def app_exit_event(self):
        """Process an appliction exit event"""
        if self.has_open_pdf():
            self.window_close_popup()
        else:
            sys.exit()
    # Top Menu
    def set_menu(self, choice):
        """Proces a menu selection event"""
        self.menu = self.menus[choice]
        updated_texts = self.menu.get_button_texts()
        updated_binds = self.menu.get_button_commands()
        updated_states = self.menu.get_button_states()
        self.menu_button_1.configure(
            text = updated_texts[0],
            command=updated_binds[0],
            state = updated_states[0])
        self.menu_button_2.configure(
            text = updated_texts[1],
            command=updated_binds[1],
            state = updated_states[1])
        self.menu_button_3.configure(
            text = updated_texts[2],
            command=updated_binds[2],
            state = updated_states[2])
        self.menu_button_4.configure(
            text = updated_texts[3],
            command=updated_binds[3],
            state = updated_states[3])
    def previous_page(self, *_args):
        """Change the page (-)"""
        page_i = self.pdfs[self.pdf_id].page_i
        if page_i-1 >= 0:
            self.pdfs[self.pdf_id].page_i = page_i-1
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def next_page(self, *_args):
        """Change the page (+)"""
        page_i = self.pdfs[self.pdf_id].page_i
        if page_i+1 <= len(self.pdfs[self.pdf_id].doc)-1:
            self.pdfs[self.pdf_id].page_i = page_i+1
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def save_event(self, *_args):
        """Process a save event"""
        self.save_path = save_pdf(self.pdfs[self.pdf_id], forced_save=False)
        if self.save_path is not None:
            self.set_saved()
    def save_pdf(self, _event):
        """Save the modified pdf document"""
        self.save_path = save_pdf(self.pdfs[self.pdf_id])
        if self.save_path is not None:
            self.set_saved()
    def open_new_pdf(self, *_args):
        """Open a new PDF with the file selector"""
        num_current_keys = len(list(self.pdfs.get_keys()))
        result = open_pdf()

        if result is not None: # Check that a file was actually selected.
            file_path, doc, password = result
            new_pdf = PdfDocInstance(file_path, doc, password)
            new_id = self.pdfs.add_pdf(new_pdf)
            self.pdf_id = new_id
            self.file_selected = f"{new_id}"
            self.update_file_select()
            self.file_select_bar.configure(values=self.pdfs.get_keys())

            if num_current_keys < 1:
                self.enable_all_buttons()
                self.enable_all_keybinds()
            num_pages = len(self.pdfs[self.pdf_id].doc)
            self.quickset_canvas.config(scrollregion=(0, 0, 250, num_pages * 320))
            self.quickset_scrollbar.set(0,(1/num_pages))

            self.update_page(self.pdfs[self.pdf_id].page_i)
            self.load_quickset()

    def load_quickset(self):
        """Use multithreading to load the quickset images on the fly, as large files take a while"""
        self.thread = threading.Thread(target=self.update_page_quickset_images)
        self.thread.start()

    def open_blank_pdf(self, *_args):
        """Open a new PDF with one blank page"""
        num_current_keys = len(list(self.pdfs.get_keys()))
        file_path = "New File"
        doc = create_blank_pdf()
        password = ""
        new_pdf = PdfDocInstance(file_path, doc, password)
        new_id = self.pdfs.add_pdf(new_pdf)
        self.pdf_id = new_id
        self.file_selected = f"{new_id}"
        self.update_file_select()
        self.file_select_bar.configure(values=self.pdfs.get_keys())

        if num_current_keys < 1:
            self.enable_all_buttons()
            self.enable_all_keybinds()

        self.update_page(self.pdfs[self.pdf_id].page_i)
        self.load_quickset()

    def close_current_pdf(self, *_args):
        """Close the current PDF only"""
        if not self.has_open_pdf():
            return
        current_keys_list = self.pdfs.get_keys()
        num_current_keys = len(current_keys_list)
        current_index = current_keys_list.index(self.file_selected)
        self.pdfs.remove_pdf(self.pdf_id)

        self.file_select_bar.destroy()
        self.file_select_bar = ctk.CTkSegmentedButton(
            self.file_menu,
            command=self.file_selector_callback)
        self.file_select_bar.grid(
            row=0,
            column=0,
            padx=(0, 0),
            pady=(10, 10),
            columnspan=12,
            sticky="ew")
        self.file_select_bar.configure(values=self.pdfs.get_keys())
        self.quickset_canvas.delete("all") # Start with an empty canvas.

        if num_current_keys <= 1: # Handle closing of last file.
            self.page_count.configure(text="Page: 0/0")
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
            self.load_quickset()

    def scale_up(self, *_args):
        """Process a scale up event"""
        if self.scale < int(self.settings["app_max_zoom_scale"]):
            if self.scale == 0.25: # Enable scale down.
                self.zoom_minus.configure(state="normal")
            self.scale += 0.25
            if self.scale == int(self.settings["app_max_zoom_scale"]): # Disable scale up.
                self.zoom_plus.configure(state="disabled")
            self.update_scale()

    def scale_down(self, *_args):
        """Process a scale down event"""
        if self.scale > 0.25:
            if self.scale == int(self.settings["app_max_zoom_scale"]): # Enable scale up.
                self.zoom_plus.configure(state="normal")
            self.scale -= 0.25
            if self.scale == 0.25: # Disable scale down.
                self.zoom_minus.configure(state="disabled")
            self.update_scale()
    # File Select Menu
    def file_selector_callback(self, value):
        """Change which PDF is being viewed currently"""
        self.pdf_id = value.replace('*', '')
        self.file_selected = value
        self.file_select_bar.set(value)
        self.update_page(self.pdfs[self.pdf_id].page_i)
        self.load_quickset()


    # DISPLAY UPDATE FUNCTIONALITY
    def update_page_quickset_images(self, *_args):
        """Update the images based on the scroll position of the h_scrollbar."""
        # Only call this function using threading,
        # due to running in O(n) with the document page number as n.
        try:
            num_pages = len(self.pdfs[self.pdf_id].doc)
            self.quickset_canvas.delete("all") # Start with an empty canvas.
            self.quickset_canvas.config(scrollregion=(0, 0, 250, num_pages * 320))
            _preview_width = 200
            _center_x = self.quickset_canvas.winfo_width() / 2
            _preview_x = (self.quickset_canvas.winfo_width() - _preview_width) / 2
            _preview_y = self.quickset_scrollbar.winfo_height()

            start_page, end_page = self.quickset_scrollbar.get()
            start_page = int(num_pages * math.floor(start_page))
            end_page = int(num_pages * math.ceil(end_page))
            page_range = end_page - start_page

            self.tkimgs = []
            for i in range(page_range):
                page_i = i + start_page
                page = self.pdfs[self.pdf_id].doc[page_i]
                pix = page.get_pixmap()
                if pix.alpha:
                    mode = "RGBA"
                else:
                    mode = "RGB"
                img = PIL.Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                # Resize and prepare the pdf page image.
                img = img.resize(
                    (_preview_width, int(pix.height * (_preview_width/pix.width))),
                     resample=PIL.Image.Resampling.NEAREST
                )
                tkimg = PIL.ImageTk.PhotoImage(img)
                self.tkimgs.append(tkimg)

                # Prevent console warning for CTkLabel with non-CTkImage as "image" argument.
                # https://stackoverflow.com/questions/14463277/how-to-disable-python-warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")

                    self.quickset_canvas.create_text(
                        _center_x,
                        i * (300 + 20) + 15,
                        fill="white",
                        font="Times 24 bold",
                        text=f"{i + 1}"
                    )
                    self.quickset_canvas.create_image(
                        _preview_x,
                        i * (300 + 20) + 35,
                        image=self.tkimgs[i],
                        anchor="nw",
                        tag="pdf_img"
                    ) # Add the image to the canvas.
            self.quickset_canvas.config(scrollregion=(0, 0, 250, num_pages * 320))
        # Raised when the active PDF is switched while the thread is still running.
        except IndexError:
            return

    def update_quickset(self, *_args):
        """Update the images based on the scroll position of the h_scrollbar."""
        canvas_start = (self.quickset_canvas.canvasx(0), self.quickset_canvas.canvasy(0))
        canvas_end = (self.quickset_canvas.canvasx(self.quickset_canvas.winfo_width()),
                      self.quickset_canvas.canvasy(self.quickset_canvas.winfo_height())
        )

        first_visible_page_i = math.floor((canvas_start[1]) / 320)
        last_visible_page_i = math.floor((canvas_end[1]-15) / 320)

        _preview_width = 200
        _preview_x = (self.quickset_canvas.winfo_width() - _preview_width) / 2

        visible_pages = []
        pages_range = list(
            range(last_visible_page_i - first_visible_page_i)
        ) + [self.pdfs[self.pdf_id].page_i]
        for page_num in pages_range:
            if page_num < len(self.pdfs[self.pdf_id].doc):
                visible_pages.append(page_num)

        for i in visible_pages: # Do this for the visible pages and the current page.
            page_i = first_visible_page_i + i

            page = self.pdfs[self.pdf_id].doc[page_i]
            pix = page.get_pixmap()
            if pix.alpha:
                mode = "RGBA"
            else:
                mode = "RGB"
            img = PIL.Image.frombytes(mode, [pix.width, pix.height], pix.samples)
             # Resize and prepare the pdf page image.
            img = img.resize(
                (_preview_width,
                 int(pix.height * (_preview_width/pix.width))
                ),
                resample=PIL.Image.Resampling.NEAREST)
            scale = _preview_width / pix.width

            tkimg = PIL.ImageTk.PhotoImage(img)

            # Prevent console warning for CTkLabel with non-CTkImage as "image" argument.
            # https://stackoverflow.com/questions/14463277/how-to-disable-python-warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.quickset_canvas.create_image(
                    _preview_x,
                    (i + first_visible_page_i) * (320) + 35,
                    image=tkimg,
                    anchor="nw",
                    tag="pdf_img"
                ) # Add the image to the canvas.

            # Update the quickset for various markup types.
            self.update_quickset_freehand(page_i, scale, _preview_width, _preview_x)
            self.update_quickset_highlight(page_i, scale, _preview_width, _preview_x)
            self.update_quickset_redact(page_i, scale, _preview_width, _preview_x)

    def update_quickset_freehand(self, page_i, scale, width_x, start_x):
        """Update the freehand drawings for the specified page on the quickset"""
        for freehand_point_set in self.pdfs[self.pdf_id].freehand_points[page_i]:
            point_set = []
            for point in freehand_point_set:
                scaled_point = (
                    point[0] * scale + start_x,
                    (point[1] * scale) + (page_i)*(320) + 35
                )
                if (scaled_point[0] < start_x
                    or scaled_point[0] > width_x+start_x
                    or scaled_point[1]-(35 + 320 * (page_i)) > 320
                    or scaled_point[1]-(35 + 320 * (page_i)) < 0):
                    # Point is outside the page bounding box, and therefore invalid.
                    pass
                else:
                    point_set.append(scaled_point)
            if len(point_set) > 1:
                self.quickset_canvas.create_line(point_set, fill="red")
    def update_quickset_redact(self, page_i, scale, width_x, start_x):
        """Update the redacts for the specified page on the quickset"""
        for redact_rect in self.pdfs[self.pdf_id].redact_points[page_i]:
            scaled_rect = (
                redact_rect[0] * scale + start_x,
                (redact_rect[1] * scale) + (page_i)*(320) + 35,
                redact_rect[2] * scale + start_x,
                (redact_rect[3] * scale) + (page_i)*(320) + 35)
            if (scaled_rect[0] < start_x
                or scaled_rect[0] > width_x+start_x
                or scaled_rect[1]-(35 + 320 * (page_i)) > 320
                or scaled_rect[1]-(35 + 320 * (page_i)) < 0):
                # Point is outside the page bounding box, and therefore invalid.
                pass
            else:
                self.quickset_canvas.create_rectangle(
                    scaled_rect,
                    fill="black",
                    outline="black")
    def update_quickset_highlight(self, page_i, scale, width_x, start_x):
        """Update the highlights for the specified page on the quickset"""
        for highlight_rect in self.pdfs[self.pdf_id].highlight_points[page_i]:
            scaled_rect = (
                highlight_rect[0] * scale + start_x,
                (highlight_rect[1] * scale) + (page_i)*(320) + 35,
                highlight_rect[2] * scale + start_x,
                (highlight_rect[3] * scale) + (page_i)*(320) + 35)
            if (scaled_rect[0] < start_x
                or scaled_rect[0] > width_x+start_x
                or scaled_rect[1]-(35 + 320 * (page_i)) > 320
                or scaled_rect[1]-(35 + 320 * (page_i)) < 0):
                # Point is outside the page bounding box, and therefore invalid.
                pass
            else:
                self.quickset_canvas.create_rectangle(
                    scaled_rect,
                    fill="yellow",
                    outline="yellow",
                    stipple="gray50")

    def quickset_canvas_clicked(self, event):
        """Process a click within the quickset canvas, select the correct page"""
        event_y = self.quickset_canvas.canvasy(event.y)
        if event_y <= 35:
            page = 0
        else:
            page = math.floor(event_y/320)
        if page >= len(self.pdfs[self.pdf_id].doc):
            return
        self.pdfs[self.pdf_id].page_i = page
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def quickset_on_mousewheel(self, event):
        """Process a scroll event within the quickset canvas, adjust its position"""
        self.quickset_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def update_button_states(self):
        """Wrapper for set_menu, used in update_page"""
        self.set_menu(self.mode.get())
    def update_file_select(self):
        """Update the file selection menu bar"""
        if f"*{self.pdf_id}" in self.pdfs.get_keys():
            self.file_select_bar.set(f"*{self.pdf_id}")
            self.file_selected = f"*{self.pdf_id}"
        else:
            self.file_select_bar.set(self.pdf_id)
            self.file_selected = f"{self.pdf_id}"
    def update_scale(self):
        """Update the zoom scale text"""
        self.update_page(self.pdfs[self.pdf_id].page_i)
        if self.scale < 1:
            # Has extra space (" ") to account for missing hundreds place digit.
            self.scale_display.configure(text=f"Zoom:  {self.scale * 100}%")
        else:
            self.scale_display.configure(text=f"Zoom: {self.scale * 100}%")
        if self.scale >= 1:
            new_width = int(150 + 20 + self.img.size[0]*0.5 + self.scrollbar.cget("width"))
            self.root.geometry(f"{new_width}x{self.root.winfo_height}")
            self.root.minsize(int(new_width), 250)

    def update_image(self, img, pix):
        """Compute and update the PDF page render"""
        self.root.update()
        self.pdf_canvas.pack(side="left", anchor='center', fill='both', expand=True)
        self.pdf_canvas.delete("all") # Start with an empty canvas.

        # Resize and prepare the pdf page image.
        img = img.resize(
            (int(pix.width), int(pix.height)), resample=PIL.Image.Resampling.NEAREST)
        self.tkimg = PIL.ImageTk.PhotoImage(img)

        self.pdf_canvas.configure(
            width=self.tkimg.width(),
            height=self.tkimg.height()) # Resize the canvas.
        self.pdf_canvas.create_image(
            self.pdf_canvas.winfo_width(),
            0,
            image=self.tkimg,
            anchor="nw",
            tag="pdf_img") # Add the image to the canvas.
        self.pdf_canvas.xview(MOVETO, 0.0) # Reset the viewing field for the canvas.
        self.pdf_canvas.yview(MOVETO, 0.0)
    def update_drawings(self, page_num):
        """Redraw all mouse strokes on the page"""
        for pointset in self.pdfs[self.pdf_id].freehand_points[page_num]:
            scale_adjusted_pointset = [
                (point[0]*self.scale, point[1]*self.scale)
                for point in pointset]
            self.pdf_canvas.create_line(scale_adjusted_pointset, fill="red")
    def update_highlights(self, page_num):
        """Redraw all highlights on the page"""
        for rectlike_set in self.pdfs[self.pdf_id].highlight_points[page_num]:
            rectlike = (rectlike_set[0]*self.scale, rectlike_set[1]*self.scale, rectlike_set[2]*self.scale, rectlike_set[3]*self.scale)
            print(rectlike)
            self.pdf_canvas.create_rectangle(
                rectlike,
                fill="yellow",
                outline="yellow",
                stipple="gray50"
            )
    def update_redactions(self, page_num):
        """Redraw all redactions on the page"""
        for rectlike_set in self.pdfs[self.pdf_id].redact_points[page_num]:
            rectlike = (rectlike_set[0]*self.scale, rectlike_set[1]*self.scale, rectlike_set[2]*self.scale, rectlike_set[3]*self.scale)
            print(rectlike)
            self.pdf_canvas.create_rectangle(
                rectlike,
                fill="black",
                outline="black"
            )
    def update_link_graphics(self, page_num):
        """Redraw all link bounding boxes"""
        link_i = 0
        self.link_images = []
        for page_link in self.pdfs[self.pdf_id].doc[page_num].links():
            try:
                assert page_link["uri"] is not None

                link_rect = [corner * self.scale for corner in list(page_link["from"])]
                link_id = self.pdf_canvas.create_rectangle(link_rect, outline="#333333", width=5)
                self.pdf_canvas.tag_bind(
                    link_id,
                    '<Button-1>',
                    lambda event,
                    rect=link_rect,
                    initial_url=page_link['uri']: self.link_edit_popup(
                        event,
                        f"{rect}",
                        f"{initial_url}"),
                    add="+")
                self.pdf_canvas.tag_bind(
                    link_id,
                    '<Button-3>',
                    lambda event,
                    rect=link_rect: self.on_click(event, f"{rect}"),
                    add="+")
                self.pdf_canvas.tag_bind(
                    link_id,
                    '<Enter>',
                    lambda event,
                    canvas=self.pdf_canvas,
                    rect=link_id: on_enter(event, canvas, rect, "#1F6AA5"),
                    add="+")
                self.pdf_canvas.tag_bind(
                    link_id,
                    '<Leave>',
                    lambda event,
                    canvas=self.pdf_canvas,
                    rect=link_id: on_leave(event, canvas, rect, "#333333"),
                    add="+")
                image_path = "link_icon.png"  # Replace with the actual path to your image file
                try:
                    link_img = PIL.Image.open(image_path)
                    resized_link_img = link_img.resize((int(25 * self.scale), int(25 * self.scale)))
                    image = PIL.ImageTk.PhotoImage(resized_link_img)
                except FileNotFoundError:
                    print(f"Error: Image file not found at {image_path}")
                    exit()

                # Calculate the center coordinates
                x = link_rect[2]+(25 * 0.5 * self.scale / math.sqrt(2))
                y = link_rect[1]-(25 * 0.5 * self.scale / math.sqrt(2))

                # Place the image on the canvas
                link_icon = self.pdf_canvas.create_image(x, y, image=image)
                self.pdf_canvas.tag_bind(
                    link_icon,
                    '<Button-1>',
                    lambda event,
                    rect=link_rect,
                    initial_url=page_link['uri']: self.link_edit_popup(
                        event,
                        f"{rect}",
                        f"{initial_url}"),
                    add="+")
                self.pdf_canvas.tag_bind(
                    link_icon,
                    '<Button-3>',
                    lambda event,
                    rect=link_rect: self.on_click(event, f"{rect}"),
                    add="+")
                self.pdf_canvas.tag_bind(
                    link_icon,
                    '<Enter>',
                    lambda event,
                    canvas=self.pdf_canvas,
                    rect=link_id: on_enter(event, canvas, rect, "#1F6AA5"),
                    add="+")
                self.pdf_canvas.tag_bind(
                    link_icon,
                    '<Leave>',
                    lambda event,
                    canvas=self.pdf_canvas,
                    rect=link_id: on_leave(event, canvas, rect, "#333333"),
                    add="+")

                self.link_images.append([image, link_icon])
                link_i += 1
            except:
                pass
        self.pdf_canvas.update_idletasks()

    def config_update_image(self):
        """Update PDF page render without new computations"""
        self.pdf_canvas.delete("all") # Start with an empty canvas.
        self.pdf_canvas.create_image(
            0,
            0,
            image=self.tkimg,
            anchor="nw",
            tag="pdf_img") # Add the image to the canvas.
        self.pdf_canvas.xview(MOVETO, 0.0) # Reset the viewing field for the canvas.
        self.pdf_canvas.yview(MOVETO, 0.0)

    def update_quickset_canvas(self):
        """Update the quickset page images"""
        canvas_scrollregion = self.quickset_canvas.config('scrollregion')[4].split(" ")
        canvas_scrollregion_size = int(canvas_scrollregion[3]) - int(canvas_scrollregion[1])
        page_num = self.pdfs[self.pdf_id].page_i
        self.quickset_canvas.yview("moveto", (page_num * 320)/canvas_scrollregion_size)

    def update_page(self, page_num):
        """Update the entire GUI for a page change"""
        # Select the page and load it as an image.
        page = self.pdfs[self.pdf_id].doc[page_num]
        mat = pymupdf.Matrix(self.scale, self.scale)
        self.pix = page.get_pixmap(matrix=mat)
        if self.pix.alpha:
            mode = "RGBA"
        else:
            mode = "RGB"
        self.img = PIL.Image.frombytes(mode, [self.pix.width, self.pix.height], self.pix.samples)
        self.update_image(self.img, self.pix)
        self.config_update_image()

        # Configure the Menu Buttons (MB 1-4).
        # Prevent scrolling left on first page.
        if self.pdfs[self.pdf_id].page_i == 0:
            self.menus["Pages"].states[0] = False
        else:
            self.menus["Pages"].states[0] = True

         # Prevent scrolling right on last page.
        if self.pdfs[self.pdf_id].page_i == (len(self.pdfs[self.pdf_id].doc)-1):
            self.menus["Pages"].states[1] = False
        else:
            self.menus["Pages"].states[1] = True

        # Prevent last page deletion.
        if len(self.pdfs[self.pdf_id].doc) == 1:
            self.menus["Pages"].states[2] = False
        else:
            self.menus["Pages"].states[2] = True

        # Prevent setting/removing password if exists/missing.
        if (self.pdfs[self.pdf_id].password is None
            or self.pdfs[self.pdf_id].password == ""):
            self.menus["Encrypt & Compress"].states[0] = True
            self.menus["Encrypt & Compress"].states[1] = False
        else:
            self.menus["Encrypt & Compress"].states[0] = False
            self.menus["Encrypt & Compress"].states[1] = True

        # Configure the page number.
        try:
            self.page_count.configure(
                text=f"Page: {self.pdfs[self.pdf_id].page_i + 1}/{len(self.pdfs[self.pdf_id].doc)}")
            self.update_quickset_canvas()
            self.update_button_states()
        except:
            pass
        self.update_drawings(page_num)
        self.update_highlights(page_num)
        self.update_redactions(page_num)
        self.update_quickset(page_num)
        if self.link_editor_toggle:
            self.update_link_graphics(page_num)


    # MENU BUTTON FUNCTIONALITY
    # Pages
    def event_rotate_left(self, *_args):
        """Rotate the page left by 90 degrees"""
        self.set_unsaved() # A modification has been made to the document.
        rotater = PageRotatePDF(self.pdfs[self.pdf_id].doc, None)
        rotater.rotate_l(self.pdfs[self.pdf_id].page_i)
        self.pdfs[self.pdf_id].doc = rotater.get()
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_rotate_right(self, *_args):
        """Rotate the page right by 90 degrees"""
        self.set_unsaved() # A modification has been made to the document.
        rotater = PageRotatePDF(self.pdfs[self.pdf_id].doc, None)
        rotater.rotate_r(self.pdfs[self.pdf_id].page_i)
        self.pdfs[self.pdf_id].doc = rotater.get()
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_move_up(self, *_args):
        """Move the current page up (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        if self.pdfs[self.pdf_id].page_i > 0:
            mover = PageMovePDF(self.pdfs[self.pdf_id].doc, None)
            mover.move(self.pdfs[self.pdf_id].page_i, self.pdfs[self.pdf_id].page_i - 1)
            self.pdfs[self.pdf_id].doc = mover.get()
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_move_down(self, *_args):
        """Move the current page down (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        if self.pdfs[self.pdf_id].page_i < len(self.pdfs[self.pdf_id].doc):
            mover = PageMovePDF(self.pdfs[self.pdf_id].doc, None)
            mover.move(self.pdfs[self.pdf_id].page_i+1, self.pdfs[self.pdf_id].page_i)
            self.pdfs[self.pdf_id].doc = mover.get()
            self.update_page(self.pdfs[self.pdf_id].page_i)
    # Encrypt & Compress
    def event_set_encryption(self, *_args):
        """Set Encryption Password for PDF (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        p1 = ""
        p2 = ""
        pass_dialog = ctk.CTkInputDialog(text="Password", title="Create Password")
        p1 = pass_dialog.get_input()
        if p1 is None:
            return
        pass_dialog2 = ctk.CTkInputDialog(text="Confirm Password", title="Create Password")
        p2 = pass_dialog2.get_input()
        if p2 is None:
            return

        if p1 == p2 and p1!= "":
            self.pdfs[self.pdf_id].password = p1
            self.menus["Encrypt & Compress"].states[0] = False
            self.menus["Encrypt & Compress"].states[1] = True
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_remove_encryption(self, *_args):
        """Remove Encryption Password for PDF (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        self.pdfs[self.pdf_id].password = None
        self.menus["Encrypt & Compress"].states[0] = True
        self.menus["Encrypt & Compress"].states[1] = False
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_compress(self, *_args):
        """Add basic compression to PDF (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        if self.pdfs[self.pdf_id].compress_basic is False:
            self.pdfs[self.pdf_id].compress_basic = True
            self.menu_button_3.configure(text="Remove Compression")
        else:
            self.pdfs[self.pdf_id].compress_basic = False
            self.menu_button_3.configure(text="Compress")
    def event_compress_max(self, *_args):
        """Add basic and maximum compression to PDF (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        if self.pdfs[self.pdf_id].compress_max is False:
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
    # Insert
    def event_insert_pdf(self, *_args):
        """Insert another PDF (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        merge_fp = open_pdf()[1]
        if merge_fp is not None and merge_fp != "":
            merger = PdfMerger(self.pdfs[self.pdf_id].doc)
            merger.add_fitz_doc(merge_fp, self.pdfs[self.pdf_id].page_i)
            self.pdfs[self.pdf_id].doc = merger.get()
            self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_insert_page(self, *_args):
        """Insert a blank page (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        inserter = PageInsertBlankPDF(self.pdfs[self.pdf_id].doc, None)
        inserter.insert(self.pdfs[self.pdf_id].page_i)
        self.pdfs[self.pdf_id].doc = inserter.get()
        self.pdfs[self.pdf_id].add_page_data(self.pdfs[self.pdf_id].page_i)
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_watermark_page(self, *_args):
        """Watermark the current page"""
        self.set_unsaved() # A modification has been made to the document.
        watermarker = WatermarkPDF(self.pdfs[self.pdf_id].doc, None)
        watermarker.watermark(
            self.pdfs[self.pdf_id].page_i,
            gui_get_file(limit_filetypes=[("PNG",".png"), ("JPEG",".jpg")])[0])
        self.pdfs[self.pdf_id].doc = watermarker.get()
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_watermark_document(self, *_args):
        """Watermark all pages"""
        self.set_unsaved() # A modification has been made to the document.
        watermarker = WatermarkPDF(self.pdfs[self.pdf_id].doc, None)
        watermarker.watermark(
            self.pdfs[self.pdf_id].page_i,
            gui_get_file(limit_filetypes=[("PNG",".png"), ("JPEG",".jpg")])[0],
            all_pages=True)
        self.pdfs[self.pdf_id].doc = watermarker.get()
        self.update_page(self.pdfs[self.pdf_id].page_i)
    # Extract
    def event_delete(self, *_args):
        """Delete the current page (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        deleter = PageDeletePDF(self.pdfs[self.pdf_id].doc, None)
        deleter.delete(self.pdfs[self.pdf_id].page_i)
        self.pdfs[self.pdf_id].doc = deleter.get()
        self.pdfs[self.pdf_id].remove_page_data(self.pdfs[self.pdf_id].page_i)

        if self.pdfs[self.pdf_id].page_i ==  len(self.pdfs[self.pdf_id].doc):
            self.pdfs[self.pdf_id].page_i -= 1
        self.update_page(self.pdfs[self.pdf_id].page_i)
    def event_extract_text(self, *_args):
        """Extract text from the PDF to a .txt (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        fname_dialog = ctk.CTkInputDialog(text="File Name", title="Extract Text")
        fname = fname_dialog.get_input()
        if fname is not None and fname.strip() != "":
            extractor = PdfExtractor(self.pdfs[self.pdf_id].doc)
            extractor.extract_text(fname)
            # Open file explorer to the folder location.
            subprocess.Popen(f'explorer "{os.getcwd()}"')
    def event_extract_images(self, *_args):
        """Extract images from the PDF to a folder (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        foldername_dialog = ctk.CTkInputDialog(text="Folder Name", title="Extract Images")
        foldername = foldername_dialog.get_input()
        if foldername is not None and foldername.strip() != "":
            extractor = PdfExtractor(self.pdfs[self.pdf_id].doc)
            extractor.extract_images(foldername)
            # Open file explorer to the folder location.
            subprocess.Popen(f'explorer "{os.getcwd()}"')
    def event_screenshot_page(self, *_args):
        """Save a screenshot of the current PDF page (Button Event)"""
        self.set_unsaved() # A modification has been made to the document.
        fname_dialog = ctk.CTkInputDialog(text="File Name", title="Screenshot Page")
        fname = fname_dialog.get_input()
        if fname is not None and fname.strip() != "":
            fname.replace(".png", "").replace(".PNG", "")
            fname += ".png"
            page = self.pdfs[self.pdf_id].doc[self.pdfs[self.pdf_id].page_i]
            pix = page.get_pixmap()
            pix.save(fname)
            # Open file explorer to the folder location.
            subprocess.Popen(f'explorer "{os.getcwd()}"')
    # Meta Data
    def event_set_meta_author(self, *_args):
        """Set the metadata "author" tag"""
        self.set_unsaved() # A modification has been made to the document.
        author_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Author: ")
        author = author_dialog.get_input()
        if author.strip() != "":
            self.pdfs[self.pdf_id].custom_metadata["author"] = author.strip()
    def event_set_meta_title(self, *_args):
        """Set the metadata "title" tag"""
        self.set_unsaved() # A modification has been made to the document.
        title_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Author: ")
        title = title_dialog.get_input()
        if title.strip() != "":
            self.pdfs[self.pdf_id].custom_metadata["title"] = title.strip()
    def event_set_meta_subject(self, *_args):
        """Set the metadata "subject" tag"""
        self.set_unsaved() # A modification has been made to the document.
        subject_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Subject: ")
        subject = subject_dialog.get_input()
        if subject.strip() != "":
            self.pdfs[self.pdf_id].custom_metadata["subject"] = subject.strip()
    def event_set_meta_keywords(self, *_args):
        """Set the metadata "keywords" tag"""
        self.set_unsaved() # A modification has been made to the document.
        keywords_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Keywords: ")
        keywords = keywords_dialog.get_input()
        if keywords.strip() != "":
            self.pdfs[self.pdf_id].custom_metadata["keywords"] = keywords.strip()
    # Signature
    def event_sign_pdf(self, *_args):
        """Sign a PDF with the current Signer Account key file and the necessary password"""
        if self.pdfs[self.pdf_id].mods_made is not False:
            self.save_path = save_pdf(
                self.pdfs[self.pdf_id],
                dialog_text = "Filename",
                dialog_title="Save a Copy to Sign",
                forced_save = True
            )
            self.set_saved()

        sig_dir = f"PDF Signatures/{self.save_path.split('/')[-1].replace('.pdf', '')}"
        if not os.path.exists(sig_dir):
            os.makedirs(sig_dir)

        status = sign_pdf(
            f"{sig_dir}/{self.signer}.sig",
            self.save_path,
            self.signer,
            ctk.CTkInputDialog(
                text=f"Password for {self.signer}",
                title="Sign PDF"
            ).get_input(),
            self.signer_private_key_path)
        self.create_popup("PDF Signature Creation Status", status, "OK")
    def event_verify_signature(self, *_args):
        """Verify a signature file (.sig) using a selected PDF and the public key from storage.  """
        signed_pdf = gui_get_file(limit_filetypes=[("PDF", ".pdf")])[0]
        if signed_pdf != "":
            signature_file = gui_get_file(limit_filetypes=[("SIG", ".sig")])[0]
            if signature_file != "":
                signer = signature_file.split("/")[-1].replace(".sig", "")
                status = verify_pdf_signature(
                    signature_file,
                    signed_pdf,
                    f"{self.settings['pubkey_storage_base']}{signer}.pem",
                    signer)
                self.create_popup("PDF Signature Verification Status", status, "OK")
    def event_add_signer_account(self, *_args):
        """Create the public and private keys necessary for PDF signature"""
        uname = None
        pwd = None
        pwd_verify = None
        while uname is None or uname.strip() == "": # Get a username for the Signer Account.
            uname_dialog = ctk.CTkInputDialog(text="Username", title="Add Signer Account")
            uname = uname_dialog.get_input()
        # Get and confirm a password for the Signer Account.
        while pwd != pwd_verify or (pwd is None or pwd.strip() == ""):
            pwd = ctk.CTkInputDialog(text="Password", title="Add Signer Account").get_input()
            pwd_verify = ctk.CTkInputDialog(
                text="Password (confirm)",
                title="Add Signer Account").get_input()
        self.signer_private_key_path = gen_signature_keys(
            f"{self.settings['pubkey_storage_base']}{uname}.pem",
            uname,
            pwd)[1] # Create and register the two keys.
        self.signer = uname
        self.menus["Signatures"].states[0] = True
        self.update_button_states()
    def event_select_signer_account(self, *_args):
        """Select a key file (.pem) file for a Signer Account"""
        self.signer_private_key_path = gui_get_file(limit_filetypes=[("PEM", ".pem")])[0]
        if self.signer_private_key_path != "":
            self.signer = os.path.split(
                self.signer_private_key_path
            )[-1].replace("_private_key.pem", "")
            self.menus["Signatures"].states[0] = True
            self.update_button_states()

    # Markup
    def event_toggle_freehand_draw(self, *_args):
        """Sign a PDF with the current Signer Account key file and the necessary password"""
        self.disable_all_markup_keybinds()
        self.freehand_draw_toggle = not self.freehand_draw_toggle
        self.freehand_start_bind = self.pdf_canvas.bind(
            "<B1-Motion>",
            self.freehand_mouse_add_coords
        )
        self.freehand_end_bind = self.pdf_canvas.bind(
            "<ButtonRelease-1>",
            self.freehand_mouse_set_end
        )

    def event_toggle_link_editor(self, *_args):
        """Verify a signature file (.sig) using a selected PDF and the public key from storage.  """
        self.disable_all_markup_keybinds()
        self.link_editor_toggle = not self.link_editor_toggle
        self.update_page(self.pdfs[self.pdf_id].page_i)

    def event_toggle_redact(self, *_args):
        """Create the public and private keys necessary for PDF signature"""
        self.disable_all_markup_keybinds()
        self.redact_toggle = not self.redact_toggle
        self.redact_start_bind = self.pdf_canvas.bind("<Button-1>", self.redact_mouse_set_start)
        self.redact_end_bind = self.pdf_canvas.bind("<ButtonRelease-1>", self.redact_mouse_set_end)

    def event_toggle_highlight(self, *_args):
        """Select a key file (.pem) file for a Signer Account"""
        self.disable_all_markup_keybinds()
        self.highlight_toggle = not self.highlight_toggle
        self.highlight_start_bind = self.pdf_canvas.bind(
            "<Button-1>",
            self.highlight_mouse_set_start
        )
        self.highlight_end_bind = self.pdf_canvas.bind(
            "<ButtonRelease-1>",
            self.highlight_mouse_set_end
        )

    def disable_all_markup_keybinds(self, *_args):
        """Disable all the keybinds related to "Markup" menu functionality"""
        try:
            self.pdf_canvas.unbind("<B1-Motion>", self.freehand_start_bind)
            self.pdf_canvas.unbind("<ButtonRelease-1>", self.freehand_end_bind)
        except: # Catch if not bound.
            pass
        try:
            self.pdf_canvas.unbind("<Button-1>", self.redact_start_bind)
            self.pdf_canvas.unbind("<ButtonRelease-1>", self.redact_end_bind)
        except: # Catch if not bound.
            pass
        try:
            self.pdf_canvas.unbind("<Button-1>", self.highlight_start_bind)
            self.pdf_canvas.unbind("<ButtonRelease-1>", self.highlight_end_bind)
        except: # Catch if not bound.
            pass

    # Drawing
    def freehand_mouse_add_coords(self, event): # Add to a click stroke.
        """Add a point to the path of the current mouse stroke"""
        scaled_point = (self.pdf_canvas.canvasx(event.x)/self.scale,
             self.pdf_canvas.canvasy(event.y)/self.scale)
        print(self.pix.width, self.pix.height)
        print(scaled_point)
        if (scaled_point[0] < 0
            or scaled_point[0] > self.pix.width
            or scaled_point[1] > self.pix.height
            or scaled_point[1] < 0):
            # Point is outside the page bounding box, and therefore invalid.
            print("Outside!")
            return
        self.pdfs[self.pdf_id].active_stroke.append(scaled_point)

        if len(self.pdfs[self.pdf_id].active_stroke) > 1:
            scale_adjusted_stroke = [
                (stroke[0]*self.scale, stroke[1]*self.scale)
                for stroke in self.pdfs[self.pdf_id].active_stroke
            ]
            self.pdf_canvas.create_line(scale_adjusted_stroke, fill="red")

    def freehand_mouse_set_end(self, _event): # End of a click stroke.
        """End the current mouse stroke"""
        if len(self.pdfs[self.pdf_id].active_stroke) > 1:
            self.pdfs[self.pdf_id].freehand_points[
                self.pdfs[self.pdf_id].page_i
            ].append(self.pdfs[self.pdf_id].active_stroke)
            scale_adjusted_stroke = [
                (stroke[0]*self.scale, stroke[1]*self.scale)
                for stroke in self.pdfs[self.pdf_id].active_stroke
            ]

            self.pdf_canvas.create_line(scale_adjusted_stroke, fill="red")
            self.set_unsaved() # A modification has been made to the document.
        self.pdfs[self.pdf_id].active_stroke = []
        self.update_quickset(self.pdfs[self.pdf_id].page_i)

    def redact_mouse_set_start(self, event): # Add to a click stroke.
        """Add a point to start a redaction"""
        self.active_redact_start = (event.x, event.y)

    def redact_mouse_set_end(self, event): # End of a click stroke.
        """End the current redaction"""
        if (self.active_redact_start[0] is not None) and (self.active_redact_start[1] is not None):
            # Create and add rect-like (4-value tuple) to redactions.
            rectlike = (self.active_redact_start[0], self.active_redact_start[1], event.x, event.y)
            self.pdfs[self.pdf_id].redact_points[self.pdfs[self.pdf_id].page_i].append(rectlike)
            self.active_redact_start = (None, None)
            self.pdf_canvas.create_rectangle(rectlike, fill="black", outline="black")
            self.set_unsaved() # A modification has been made to the document.
            self.update_quickset(self.pdfs[self.pdf_id].page_i)

    def highlight_mouse_set_start(self, event): # Add to a click stroke.
        """Add a point to start a redaction"""
        self.active_highlight_start = (
            self.pdf_canvas.canvasx(event.x)/self.scale,
            self.pdf_canvas.canvasy(event.y)/self.scale
        )
    def highlight_mouse_set_end(self, event): # End of a click stroke.
        """End the current redaction"""
        if (self.active_highlight_start[0] is not None
            and self.active_highlight_start[1] is not None):
            rectlike = (
                self.active_highlight_start[0],
                self.active_highlight_start[1],
                self.pdf_canvas.canvasx(event.x)/self.scale,
                self.pdf_canvas.canvasy(event.y)/self.scale
            ) # Create and add rect-like (4-value tuple) to redactions.
            if rectlike[0] == rectlike[2] and rectlike[1] == rectlike[3]: # Just one point.
                self.active_highlight_start = (None, None)
                return
            self.pdfs[self.pdf_id].highlight_points[self.pdfs[self.pdf_id].page_i].append(rectlike)
            self.active_highlight_start = (None, None)
            self.pdf_canvas.create_rectangle(
                rectlike,
                fill="yellow",
                outline="yellow",
                stipple="gray50"
            )
            self.set_unsaved() # A modification has been made to the document.
            self.update_quickset(self.pdfs[self.pdf_id].page_i)

if __name__ == "__main__":
    # Run the PyPdfApp application
    App()
