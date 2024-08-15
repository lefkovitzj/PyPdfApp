"""
    Author: lefkovitj (https://lefkovitzj.github.io)
    File Last Modified: 8/15/2024
    Project Name: PyPdfApp
    File Name: load.py
"""

# Python Standard Library Imports.
import os
import sys
from tkinter import *
from tkinter import filedialog
import traceback

# Third-party Module Imports.
from PIL import Image, ImageTk
import fitz
import customtkinter as ctk


def gui_get_file(initial_directory="", limit_filetypes=[]):
    """ Open file explorer (using tkinter) to select a file. """
    root = Tk() # Create the GUI window.
    root.withdraw()
    complete_file_path = filedialog.askopenfilename(title="File Select", initialdir = os.getcwd() + "/" + initial_directory, filetypes = limit_filetypes) # Select the file.
    root.destroy()
    file_path, file_name = os.path.split(complete_file_path) # Get the filepath and filename to return to the user.
    return complete_file_path, file_name

def open_pdf():
    if len(sys.argv) == 1: # No argument provided, request file path.
        file_path = gui_get_file(limit_filetypes=[("PDF",".pdf")])[0]
        if file_path == "":
            sys.exit()
    else: # File path was included as a command-line argument.
        file_path = sys.argv[1]

    try:
        fitz_doc = fitz.open(file_path)
        doc_password = None
        while fitz_doc.is_encrypted:
            pass_dialog = ctk.CTkInputDialog(text="Password", title="Open PDF")
            doc_password = pass_dialog.get_input()
            fitz_doc.authenticate(doc_password)
        return file_path, fitz_doc, doc_password

    except Exception: # Handle any application errors by returning them to the user without crashing.
            print(f"Error Message: \"{traceback.format_exc()}\"")