"""
    Author: lefkovitj (https://lefkovitzj.com)
    File Last Modified: 8/28/2025
    Project Name: PyPdfApp
    File Name: manipulate.py
"""

# Standard library imports.
import datetime
from tkinter import *
from tkinter import filedialog
import os


# Third-party imports.
import fitz

def create_blank_pdf():
    """Return a PDF item with only one blank page"""
    new_doc = fitz.open()
    new_doc.new_page()
    return new_doc

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

def calculate_pdf_temp_title():
    """Generate a timestamp-based temporary filename"""
    tb = str(datetime.datetime.today()) # Basic timestamp string.
    file_title = (tb[:4] + "-" +
                  tb[5:7] + "-"
                  + tb[8:10] + "_" +
                  tb[11:13] + "-" +
                  tb[14:16] + "-" +
                  tb[17:19] + ".pdf")
    return file_title


class PdfExtractor():
    """Extract data from the PDF of page"""
    def __init__(self, fitz_doc):
        """Initialize the object"""
        # Ensure that the necessary save folder exists.
        if "temporary-files" not in os.listdir(os.getcwd()):
            os.makedirs("temporary-files")
        self.doc = fitz_doc
    def extract_text(self, file_loc):
        """Extract text from the PDF"""
        file_loc.replace(".txt", "")
        file_loc += ".txt"
        with open(file_loc, "w", encoding="utf-8") as text_file: # Open the output .txt file.
            for page_i in self.doc: # Iterate through each page.
                page_text = page_i.get_text("text")
                text_file.write(
                    ("Text extracted from PDF file by PyPdfUtils: "
                     "\n\nSTART OF EXTRACTED TEXT\n")
                )
                text_file.write(page_text + "\n")
                text_file.write("END OF EXTRACTED TEXT")
        text_file.close() # Close the .txt file.
        return True, file_loc
    def extract_images(self, file_dir):
        """Extract images from the PDF"""
        os.mkdir(file_dir)
        img_num = 1
        for page_i in self.doc: # Iterate through each page.
            for page_image_list in page_i.get_images():
                xref_id = page_image_list[0] # Get the xref of the image.
                page_image = self.doc.extract_image(xref_id) # Extract the image from the page.
                # Save the extracted image to the temporary file directory.
                with open(
                    (file_dir + "\\image_" + str(img_num) + "." + page_image["ext"]),
                    'wb') as img_bin: 
                    img_bin.write(page_image["image"])
                img_bin.close()
                img_num += 1
        return True, file_dir

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

class PageMovePDF(PDFManipulator):
    """Re-arrange pages within the document"""
    def move(self, from_page, to_page):
        """Move a page"""
        if from_page <= len(self.doc) and from_page >= 0:
            self.doc.move_page(from_page, to_page)

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

class PdfMerger():
    """An object used to merge two PDF documents (or select pages) into one"""
    def __init__(self, fitz_doc):
        """Initialize the object"""
        self.doc = fitz_doc

    def save(self):
        """Save the document to temporary files"""
        self.doc.save("temporary-files\\" + calculate_pdf_temp_title())

    def add_pages(self, source_file_loc, start_i, start_page, end_page=None):
        """Add the pages from the source document between the given indices."""
        if end_page is None: # No end page was specified, assume only one page was intended.
            end_page = start_page
        source_file = fitz.open(source_file_loc)
        if end_page == -1:
            # No to_page argument, default to last page.
            self.doc.insert_pdf(source_file, from_page=start_page, start_at = start_i)
        else:
            self.doc.insert_pdf(
                source_file,
                from_page=start_page,
                to_page=end_page,
                start_at = start_i)
        source_file.close()

    def add_pdf(self, source_file_loc, start_i):
        """Add all pages from the source document."""
        source_file = fitz.open(source_file_loc)
        self.doc.insert_pdf(source_file, start_at = start_i)
        source_file.close()

    def add_fitz_doc(self, source_fitz_doc, start_i):
        """Add all pages from the source document."""
        self.doc.insert_pdf(source_fitz_doc, start_at = start_i)
        source_fitz_doc.close()

    def remove_page(self, page_i):
        """Remove a page at the given index if it exists"""
        doc_len = len(self.doc)
        if page_i <= doc_len:
            new_doc = fitz.open()
            # Add all the pages up to the page that is to be removed.
            new_doc.insert_pdf(self.doc, from_page = 0, to_page=page_i-1)
            if page_i != doc_len:
                # Add all pages after the page to be removed.
                new_doc.insert_pdf(self.doc, from_page = page_i+1)
            self.doc = new_doc
        else: # The page does not exist at the given index.
            raise IndexError(f"Page index out of range for document of length {doc_len}")

    def get(self):
        """Return the PDF document"""
        return self.doc
