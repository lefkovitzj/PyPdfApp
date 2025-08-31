"""
    Author: lefkovitj (https://lefkovitzj.com)
    File Last Modified: 8/28/2025
    Project Name: PyPdfApp
    File Name: merge.py
"""

# Standard library imports.
import datetime

# Third-party module imports.
import fitz

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
