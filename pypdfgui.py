"""
    Author: lefkovitj (https://lefkovitzj.github.io)
    File Last Modified: 8/30/2024
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

class App():
    def __init__(self):
        """ Create the PyPdfApp Application GUI.  """
        # Create the GUI window.
        self.root = ctk.CTk()

        # Start program by opening a PDF.
        self.file_path, self.doc, self.password = open_pdf()

        # Initialize status data for the PDF.
        self.mods_made = False # Document has been modified from its orignal state.
        self.compress_basic = False
        self.compress_max = False
        self.page_i = 0
        self.scale = 1.0
        self.custom_metadata = {"creator": "PyPdfApp", "producer": "PyPdfApp"}

        # Get the settings file data.
        with open("settings.json", "r") as json_settings:
            self.settings = json.load(json_settings)

        # Startup checks.
        self.needs_update = self.on_startup_update_check()
        self.license_agreed = self.on_startup_license_check()

        # Load the menu data.
        self.menus = {
                            "Encrypt & Compress":       GUI_Menu("Encryption", self.root, ["Set Encryption", "Remove Encryption", "Compress", "Compress (max)"], [self.event_set_encryption, self.event_remove_encryption, self.event_compress, self.event_compress_max], [True, True, True, True]),
                            "Pages":                    GUI_Menu("Pages", self.root, ["Move up", "Move down", "Delete", "Insert Blank"], [self.event_move_up, self.event_move_down, self.event_delete, self.event_insert_page], [True, True, True, True]),
                            "Meta Data":                GUI_Menu("Meta Data", self.root, ["Set Author", "Set Title", "Set Subject", "Add Keywords"], [self.event_set_meta_author, self.event_set_meta_title, self.event_set_meta_subject, self.event_set_meta_keywords], [True, True, True, True]),
                            "Insert & Extract":         GUI_Menu("Insert &  Extract", self.root, ["Insert PDF", "Extract text", "Extract images", "Screenshot Page"], [self.event_insert_pdf, self.event_extract_text, self.event_extract_images, self.event_screenshot_page], [True, True, True, True])
        }

        # Add the menu area.
        self.menu_area = ctk.CTkFrame(self.root)
        self.menu_area.pack(anchor="nw", fill="x")

        # Create and configure the area for the submenu.
        self.submenu = ctk.CTkFrame(self.menu_area)
        self.submenu.pack(anchor="nw", fill="x", expand=True)
        for i in range(11): # Configure the resizeable grid columns.
            self.submenu.columnconfigure(i, weight=1)

        # Add the frame and tkinter Canvas for the PDF.
        self.canvas_frame = ctk.CTkFrame(self.root)
        self.canvas_frame.pack(anchor="center", fill='both', expand=True)
        self.pdf_canvas = Canvas(self.canvas_frame, bg="#333333", highlightthickness=0)
        self.canvas_frame.bind("<Configure>", lambda e: self.pdf_canvas.configure(scrollregion=self.pdf_canvas.bbox("all")))

        # Create and configure the vertical and horizontal scrollbars.
        self.scrollbar = ctk.CTkScrollbar(self.canvas_frame, orientation="vertical", fg_color="#333333")
        self.scrollbar.pack(side="right", fill="y")
        self.scrollbar.configure(command=self.pdf_canvas.yview)
        self.Hscrollbar = ctk.CTkScrollbar(self.canvas_frame, orientation="horizontal", fg_color="#333333")
        self.Hscrollbar.pack(side="bottom", fill="x")
        self.Hscrollbar.configure(command=self.pdf_canvas.xview)

        # Configure the PDF viewer Canvas.
        self.pdf_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.pdf_canvas.pack(side="left", anchor='center', fill='both', expand=True)

        # Load the first page.
        self.update_page(0)
        self.root.update()

        # Set the minimum window dimensions.
        self.root.minsize(self.root.winfo_width()+34, 250)

        # First menu column.
        self.B1 = ctk.CTkFrame(self.submenu, fg_color="#333333")
        self.mode = ctk.CTkOptionMenu(self.B1, values=["Pages", "Encrypt & Compress", "Insert & Extract", "Meta Data"], command=self.set_menu, width=self.menu_area.winfo_width()/4)
        self.MB1 = ctk.CTkButton(self.submenu, text=" ",  command = lambda: print(""))
        self.MB1.grid(row = 1, column=0, columnspan=3, padx=10, pady=10)
        self.B1.grid(row = 0, column=0, columnspan=3)
        self.mode.grid(row=0, column=0, columnspan=3)

        # Second menu column.
        self.B2 = ctk.CTkFrame(self.submenu, fg_color="#333333")
        self.prev = ctk.CTkButton(self.B2, text = "<", command = self.previous_page, width = 25)
        self.next = ctk.CTkButton(self.B2, text = ">", command = self.next_page, width = 25)
        self.save = ctk.CTkButton(self.B2, text = "💾", command = self.save_event, width = 25)
        self.MB2 = ctk.CTkButton(self.submenu, text=" ", command = lambda: print(""))
        self.MB2.grid(row = 1,column=3, columnspan=3, padx=10, pady=10)
        self.B2.grid(row = 0,column=3, columnspan=3)
        self.prev.grid(row = 0, column = 3, columnspan=3, padx=5)
        self.next.grid(row = 0, column = 6, columnspan=3, padx=5)
        self.save.grid(row = 0, column = 9, columnspan=3, padx=5)

        # Third menu column.
        self.B3 = ctk.CTkFrame(self.submenu, height=40, fg_color="#333333")
        self.scale_display = ctk.CTkLabel(self.B3, text = "Zoom: 100%", fg_color = "transparent")
        self.scale_slider = ctk.CTkSlider(self.B3, from_=1, to=int(self.settings["app_max_zoom_scale"]) * 4, command=self.adjust_scale, width=75, number_of_steps = int(self.settings["app_max_zoom_scale"]) * 4 - 1)#, width=self.menu_area.winfo_width()/4)
        self.MB3 = ctk.CTkButton(self.submenu, text=" ", command = lambda: print(""))
        self.MB3.grid(row = 1,column=6, columnspan=3, padx=10, pady=10)
        self.B3.grid(row = 0,column=6, columnspan=3)
        self.scale_display.grid(row=0, column=6, columnspan=1, padx=5)
        self.scale_slider.grid(row=0, column=7, columnspan=2, padx=5)

        # Fourth menu column.
        self.B4 = ctk.CTkFrame(self.submenu, height=40, fg_color="#333333")
        self.page_count = ctk.CTkLabel(self.B4, text = "page x/x", fg_color = "transparent")
        self.page_count.configure(text=f"Page: {self.page_i+1}/{len(self.doc)}")
        self.MB4 = ctk.CTkButton(self.submenu, text=" ", command = lambda: print(""))
        self.MB4.grid(row = 1,column=9, columnspan=3, padx=10, pady=10)
        self.B4.grid(row = 0,column=9)
        self.page_count.grid()

        # Load the initial menu data.
        self.menu = None
        self.mode.set("Pages")
        self.set_menu("Pages")

        # Name the window.
        self.root.title("PyPdfApp")

        # Configure keybinds.
        if bool(self.settings["allow_keyboard_events"]):
            self.root.bind("<Control-s>", self.save_event)
            self.root.bind("<Left>", self.previous_page)
            self.root.bind("<Right>", self.next_page)
            self.root.bind("<Control-Key-plus>", self.scale_up)
            self.root.bind("<Control-Key-minus>", self.scale_down)

        self.root.bind("<Configure>", lambda event: self.config_update_image())

        # Application update screen.
        if self.needs_update:
            self.update_area = ctk.CTkFrame(self.root)
            self.update_area.place(anchor="nw", relheight=1.0, relwidth=1.0)
            ctk.CTkLabel(self.update_area, text = "Your software is not up to date. A new version is available!", fg_color = "transparent").pack()

            textbox = ctk.CTkTextbox(self.update_area)
            textbox.insert(0.0,
                                """Your software is no longer up to date. Software updates are strongly encouraged. \nWhile this version should continue to operate, you will potentially be missing out on:\n  1. New application features.\n  2. Security updates.\n  3. Critical bug fixes.\n  4. Improved application efficiency.\n\nBy continuing to use this version of PyPdfApp you may experience some of the following issues:\n  1. Unexpected program crashes.\n  2. User interface glitches.\n  3. Functionality failures.\n  4. Possible corruption of PDF files. \n\n To ensure you are using the most recent version of PyPdfApp, select "Open browser for update". \nFrom there, you can download the newest version of PyPdfApp avaialable! """
                        )
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

        # Set window behavior.
        if bool(self.settings["ask_save_before_exit"]):
            self.root.protocol("WM_DELETE_WINDOW", self.app_exit_event) # Add on-exit "Are you sure?" event.

        # Load the first page of the PDF document.
        self.update_page(0)

        # Start the main application loop.
        self.root.mainloop()

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

    def save_event(self, *args):
        """ Process a save event. """
        save_pdf(self.doc, self.custom_metadata, self.compress_basic, self.compress_max, self.password, forced_save=False)
        self.mods_made = False

    def set_menu(self, choice):
        """ Proces a menu selection event. """
        self.menu = self.menus[choice]
        updated_texts = self.menu.get_button_texts()
        updated_binds = self.menu.get_button_commands()
        updated_states = self.menu.get_button_states()

        self.MB1.configure(text = updated_texts[0], command=updated_binds[0], state = updated_states[0])
        self.MB2.configure(text = updated_texts[1], command=updated_binds[1], state = updated_states[1])
        self.MB3.configure(text = updated_texts[2], command=updated_binds[2], state = updated_states[2])
        self.MB4.configure(text = updated_texts[3], command=updated_binds[3], state = updated_states[3])

    def update_button_states(self):
        """ Wrapper for set_menu, used in update_page. """
        self.set_menu(self.mode.get())

    def update_scale(self):
        """ Update the zoom scale text and slider. """
        self.update_page(self.page_i)
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

    def config_update_image(self):
        """ Update PDF page render without new computations. """
        self.pdf_canvas.delete("all") # Start with an empty canvas.
        self.pdf_canvas.create_image(0, 0, image=self.tkimg, anchor="nw", tag="pdf_img") # Add the image to the canvas.
        self.pdf_canvas.xview(MOVETO, 0.0) # Reset the viewing field for the canvas.
        self.pdf_canvas.yview(MOVETO, 0.0)

    def update_page(self, page_num): # Load the page.
        """ Update the entire GUI for a page change. """
        # Select the page and load it as an image.
        page = self.doc[page_num]
        self.pix = page.get_pixmap()
        if self.pix.alpha:
            mode = "RGBA"
        else:
            mode = "RGB"
        self.img = PIL.Image.frombytes(mode, [self.pix.width, self.pix.height], self.pix.samples)
        self.update_image(self.img, self.pix)
        self.config_update_image()

        # Configure the Menu Buttons (MB 1-4).
        if self.page_i == 0: # Prevent scrolling left on first page.
            self.menus["Pages"].states[0] = False
        else:
            self.menus["Pages"].states[0] = True

        if self.page_i == (len(self.doc)-1): # Prevent scrolling right on last page.
            self.menus["Pages"].states[1] = False
        else:
            self.menus["Pages"].states[1] = True

        if len(self.doc) == 1: # Prevent last page deletion.
            self.menus["Pages"].states[2] = False
        else:
            self.menus["Pages"].states[2] = True

        if self.password == None or self.password == "": # Prevent setting/removing password if exists/missing.
            self.menus["Encrypt & Compress"].states[0] = True
            self.menus["Encrypt & Compress"].states[1] = False
        else:
            self.menus["Encrypt & Compress"].states[0] = False
            self.menus["Encrypt & Compress"].states[1] = True

        # Configure the page number.
        try:
            self.page_count.configure(text=f"Page: {self.page_i + 1}/{len(self.doc)}")
            self.update_button_states()
        except:
            pass

    def next_page(self, *args):
        """ Change the page (+). """
        page_i = self.page_i
        if page_i+1 <= len(self.doc)-1:
            self.update_page(page_i+1)
            self.page_i = page_i+1
            self.update_page(self.page_i)


    def previous_page(self, *args):
        """ Change the page (-). """
        page_i = self.page_i
        if page_i-1 >= 0:
            self.page_i = page_i-1
            self.update_page(self.page_i)


    def save_pdf(self, event):
        """ Save the modified pdf document. """
        save_pdf(self.doc, self.custom_metadata, compress_basic = self.compress_basic, compress_max = self.compress_max, password = self.password)


    def app_exit_event(self):
        """ Process an appliction exit event. """
        if self.mods_made:
            save_pdf(self.doc, self.custom_metadata, compress_basic = self.compress_basic, compress_max = self.compress_max, password = self.password, dialog_text = "Filename", dialog_title="Save File Changes?",forced_save = False)
        sys.exit()

    """ MB Event actions by Menu Category.
    Encrypt & Compress: "Set Encryption", "Remove Encryption", "Compress", "Compress (max)"
    Pages: "Move up", "Move down", "Delete", "Insert Blank"
    Insert & Extract: "Insert PDF", "Extract text", "Extract images", "Screenshot Page"
    Meta Data: "Set Author", "Set Title", "Set Subject", "Add Keywords"
    """

    def event_set_meta_author(self, *args):
        """ Set the metadata "author" tag. """
        author_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Author: ")
        author = author_dialog.get_input()
        if author.strip() != "":
            self.custom_metadata["author"] = author.strip()

    def event_set_meta_title(self, *args):
        """ Set the metadata "title" tag. """
        title_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Author: ")
        title = title_dialog.get_input()
        if title.strip() != "":
            self.custom_metadata["title"] = title.strip()

    def event_set_meta_subject(self, *args):
        """ Set the metadata "subject" tag. """
        subject_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Subject: ")
        subject = subject_dialog.get_input()
        if subject.strip() != "":
            self.custom_metadata["subject"] = subject.strip()

    def event_set_meta_keywords(self, *args):
        """ Set the metadata "keywords" tag. """
        keywords_dialog = ctk.CTkInputDialog(text="Set Meta Data", title="PDF Keywords: ")
        keywords = keywords_dialog.get_input()
        if keywords.strip() != "":
            self.custom_metadata["keywords"] = keywords.strip()

    def event_set_encryption(self, *args):
        """ Set Encryption Password for PDF (Button Event). """
        self.mods_made = True # A modification has been made to the document.
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
            self.password = p1
            self.menus["Encrypt & Compress"].states[0] = False
            self.menus["Encrypt & Compress"].states[1] = True
            self.update_page(self.page_i)

    def event_remove_encryption(self, *args):
        """ Remove Encryption Password for PDF (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        self.password = None
        self.menus["Encrypt & Compress"].states[0] = True
        self.menus["Encrypt & Compress"].states[1] = False
        self.update_page(self.page_i)

    def event_compress(self, *args):
        """ Add basic compression to PDF (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        if self.compress_basic == False:
            self.compress_basic = True
            self.MB3.configure(text="Remove Compression")
        else:
            self.compress_basic = False
            self.MB3.configure(text="Compress")

    def event_compress_max(self, *args):
        """ Add basic and maximum compression to PDF (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        if self.compress_max == False:
            self.compress_basic = True
            self.compress_max = True
            self.MB3.configure(text="Remove Compression")
            self.MB3.configure(state="disabled")
            self.menus["Encrypt & Compress"].states[2] = False
            self.MB4.configure(text="Remove Compression")
        else:
            self.compress_basic = False
            self.compress_max = False
            self.MB3.configure(text="Compress")
            self.MB3.configure(state="normal")
            self.menus["Encrypt & Compress"].states[2] = True
            self.MB4.configure(text="Compress (Max)")

    def event_move_up(self, *args):
        """ Move the current page up (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        if self.page_i > 0:
            mover = Page_Move_PDF(self.doc, None)
            mover.move(self.page_i, self.page_i - 1)
            self.doc = mover.get()
            self.update_page(self.page_i)

    def event_move_down(self, *args):
        """ Move the current page down (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        if self.page_i < len(self.doc):
            mover = Page_Move_PDF(self.doc, None)
            mover.move(self.page_i+1, self.page_i)
            self.doc = mover.get()
            self.update_page(self.page_i)

    def event_delete(self, *args):
        """ Delete the current page (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        deleter = Page_Delete_PDF(self.doc, None)
        deleter.delete(self.page_i)
        self.doc = deleter.get()
        if self.page_i ==  len(self.doc):
            self.page_i -= 1
        self.update_page(self.page_i)

    def event_insert_page(self, *args):
        """ Insert a blank page (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        inserter = Page_Insert_Blank_PDF(self.doc, None)
        inserter.insert(self.page_i)
        self.doc = inserter.get()
        self.update_page(self.page_i)

    def event_insert_pdf(self, *args):
        """ Insert another PDF (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        merge_fp = open_pdf()[1]
        if merge_fp != None and merge_fp != "":
            merger = PDF_Merger(self.doc)
            merger.add_fitz_doc(merge_fp, self.page_i)
            self.doc = merger.get()
            self.update_page(self.page_i)

    def event_extract_text(self, *args):
        """ Extract text from the PDF to a .txt (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        fname_dialog = ctk.CTkInputDialog(text="File Name", title="Extract Text")
        fname = fname_dialog.get_input()
        if fname != None and fname.strip() != "":
            extractor = PDF_Extractor(self.doc)
            extractor.extract_text(fname)
            subprocess.Popen(f'explorer "{os.getcwd()}"') # Open file explorer to the folder location.

    def event_extract_images(self, *args):
        """ Extract images from the PDF to a folder (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        foldername_dialog = ctk.CTkInputDialog(text="Folder Name", title="Extract Images")
        foldername = foldername_dialog.get_input()
        if foldername != None and foldername.strip() != "":
            extractor = PDF_Extractor(self.doc)
            extractor.extract_images(foldername)
            subprocess.Popen(f'explorer "{os.getcwd()}"') # Open file explorer to the folder location.

    def event_screenshot_page(self, *args):
        """ Save a screenshot of the current PDF page (Button Event). """
        self.mods_made = True # A modification has been made to the document.
        fname_dialog = ctk.CTkInputDialog(text="File Name", title="Screenshot Page")
        fname = fname_dialog.get_input()
        if fname != None and fname.strip() != "":
            fname.replace(".png", "").replace(".PNG", "")
            fname += ".png"
            page = self.doc[self.page_i]
            pix = page.get_pixmap()
            pix.save(fname)
            subprocess.Popen(f'explorer "{os.getcwd()}"') # Open file explorer to the folder location.
