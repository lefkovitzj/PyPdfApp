"""
    Author: lefkovitj (https://lefkovitzj.com)
    File Last Modified: 8/31/2025
    Project Name: PyPdfApp
    File Name: load.py
"""

# Python Standard Library Imports.
import sys
import traceback

# Third-party Module Imports.
import fitz
import customtkinter as ctk

# Project imports.
from manipulate import gui_get_file

def open_pdf():
    """Open and load a PDF via the system filedialog"""
    if len(sys.argv) == 1: # No argument provided, request file path.
        file_path = gui_get_file(limit_filetypes=[("PDF",".pdf")])[0]
        if file_path == "":
            return None
    else: # File path was included as a command-line argument.
        file_path = sys.argv[1]

    try:
        fitz_doc = fitz.open(file_path)
        doc_password = ""
        while fitz_doc.is_encrypted:
            if doc_password is None:
                return None
            pass_dialog = ctk.CTkInputDialog(text="Password", title="Open PDF")
            doc_password = pass_dialog.get_input()
            fitz_doc.authenticate(doc_password)
        return file_path, fitz_doc, doc_password

    # Handle any application errors by returning them to the user without crashing.
    except Exception:
        print(f"Error Message: \"{traceback.format_exc()}\"")
        return None
