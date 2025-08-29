"""
    Author: lefkovitj (https://lefkovitzj.com)
    File Last Modified: 8/28/2025
    Project Name: PyPdfApp
    File Name: manipulate.py
"""

# Standard library imports.
from tkinter import *
from tkinter import filedialog
import os

# Third-party imports.
import fitz

def gui_get_file(initial_directory="", limit_filetypes=None):
    """Open file explorer (using tkinter) to select a file"""
    if limit_filetypes is None:
        limit_filetypes = []
    root = Tk()
    root.withdraw()
    complete_file_path = filedialog.askopenfilename(
        title="File Select",
        initialdir = os.getcwd() + "/" + initial_directory,
        filetypes = limit_filetypes
    )
    root.destroy()
    _file_path, file_name = os.path.split(complete_file_path)
    return complete_file_path, file_name

class PDFManipulator:
    """A base class for PDF manipulation tasks."""
    def __init__(self, fitz_doc, save_path):
        self.doc = fitz_doc
        self.save_path = save_path

    def get(self):
        """Get the updated document object."""
        return self.doc

    def save(self):
        """Save the document."""
        self.doc.save(self.save_path)

class PageRotatePDF(PDFManipulator):
    """Rotate pages within the document"""
    def rotate_l(self, page_i):
        """Rotate the page (left)"""
        spec_page = self.doc[page_i]
        spec_page.set_rotation(spec_page.rotation - 90)
    def rotate_r(self, page_i):
        """Rotate the page (right)"""
        spec_page = self.doc[page_i]
        spec_page.set_rotation(spec_page.rotation + 90)

class PageMovePDF(PDFManipulator):
    """Re-arrange pages within the document"""
    def move(self, from_page, to_page):
        """Move a page"""
        if from_page <= len(self.doc) and from_page >= 0:
            self.doc.move_page(from_page, to_page)

class PageDeletePDF(PDFManipulator):
    """Delete pages within the document"""
    def delete(self, page_i):
        """Delete page"""
        self.doc.delete_page(page_i)

class PageInsertBlankPDF(PDFManipulator):
    """Insert blank page within the document"""
    def insert(self, page_i):
        """Insert a blank page"""
        self.doc.insert_page(page_i)

class WatermarkPDF(PDFManipulator):
    """Watermark pages within the document"""
    def watermark(self, page_i, source_image, all_pages=False):
        """Insert a the watermark on the selected page(s)"""
        if not all_pages:
            page = self.doc[page_i]
            if not page.is_wrapped:
                page.wrap_contents()
            page.insert_image(page.bound(), filename = source_image, overlay = True)
        else:
            for page in self.doc:
                # Solution for flipped/rotated watermark without reason.
                # https://pymupdf.readthedocs.io/en/latest/recipes-common-issues-and-their-solutions.html#misplaced-item-insertions-on-pdf-pages
                if not page.is_wrapped:
                    page.wrap_contents()
                page.insert_image(page.bound(), filename = source_image, overlay = True)

def create_blank_pdf():
    """Return a PDF item with only one blank page"""
    new_doc = fitz.open()
    new_doc.new_page()
    return new_doc
