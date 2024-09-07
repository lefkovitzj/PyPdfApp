"""
    Author: lefkovitj (https://lefkovitzj.github.io)
    File Last Modified: 9/7/2024
    Project Name: PyPdfApp
    File Name: manipulate.py
"""

import fitz
from tkinter import *
from tkinter import filedialog
import os
import sys

def gui_get_file(initial_directory="", limit_filetypes=[]):
    """ Open file explorer (using tkinter) to select a file. """
    root = Tk() # Create the GUI window.
    root.withdraw()
    complete_file_path = filedialog.askopenfilename(title="File Select", initialdir = os.getcwd() + "/" + initial_directory, filetypes = limit_filetypes) # Select the file.
    root.destroy()
    file_path, file_name = os.path.split(complete_file_path) # Get the filepath and filename to return to the user.
    return complete_file_path, file_name

class Page_Rotate_PDF():
    """ Rotate pages within the document. """
    def __init__(self, fitz_doc, save_path):
        # Initialize the object.
        self.doc = fitz_doc
        self.save_path = save_path
    def rotate_l(self, page_i):
        # Rotate the page (left).
        spec_page = self.doc[page_i]
        spec_page.set_rotation(spec_page.rotation - 90)
    def rotate_r(self, page_i):
        # Rotate the page (right).
        spec_page = self.doc[page_i]
        spec_page.set_rotation(spec_page.rotation + 90)
    def get(self):
        # Get the updated document object.
        return self.doc
    def save(self):
        # Save the document.
        self.doc.save(self.save_path)

class Page_Move_PDF():
    """ Re-arrange pages within the document. """
    def __init__(self, fitz_doc, save_path):
        # Initialize the object.
        self.doc = fitz_doc
        self.save_path = save_path
    def move(self, from_page, to_page):
        # Move a page.
        if from_page <= len(self.doc) and from_page >= 0:
            self.doc.move_page(from_page, to_page)
    def get(self):
        # Get the updated document object.
        return self.doc
    def save(self):
        # Save the document.
        self.doc.save(self.save_path)

class Page_Delete_PDF():
    """ Delete pages within the document. """
    def __init__(self, fitz_doc, save_path):
        # Initialize the object.
        self.doc = fitz_doc
        self.save_path = save_path
    def delete(self, page_i):
        # Delete page.
        self.doc.delete_page(page_i)
    def get(self):
        # Get the updated document object.
        return self.doc
    def save(self):
        # Save the document.
        self.doc.save(self.save_path)

class Page_Insert_Blank_PDF():
    """ Delete pages within the document. """
    def __init__(self, fitz_doc, save_path):
        # Initialize the object.
        self.doc = fitz_doc
        self.save_path = save_path
    def insert(self, page_i):
        # Insert a blank page.
        self.doc.insert_page(page_i)
    def get(self):
        # Get the updated document object.
        return self.doc
    def save(self):
        # Save the document.
        self.doc.save(self.save_path)

class Watermark_PDF():
    """ Watermark pages within the document. """
    def __init__(self, fitz_doc, save_path):
        # Initialize the object.
        self.doc = fitz_doc
        self.save_path = save_path
    def watermark(self, page_i, source_image, all_pages=False):
        # Insert a the watermark on the selected page(s).
        if not all_pages:
            page = self.doc[page_i]
            if not page.is_wrapped:
                page.wrap_contents()
            page.insert_image(page.bound(), filename = source_image, overlay = True)
        else:
            for page in self.doc:
                if not page.is_wrapped: # Solution for flipped/rotated watermark without reason. Documentation: https://pymupdf.readthedocs.io/en/latest/recipes-common-issues-and-their-solutions.html#misplaced-item-insertions-on-pdf-pages
                    page.wrap_contents()
                page.insert_image(page.bound(), filename = source_image, overlay = True)
    def get(self):
        # Get the updated document object.
        return self.doc
    def save(self):
        # Save the document.
        self.doc.save(self.save_path)