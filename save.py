"""
    Author: lefkovitj (https://lefkovitzj.com)
    File Last Modified: 8/28/2025
    Project Name: PyPdfApp
    File Name: save.py
"""

# Python Standard Library Imports.
from datetime import date

# Third-party Module Imports.
import fitz
import customtkinter as ctk

def save_pdf(
        pdf_doc,
        password = None,
        dialog_text=None,
        dialog_title=None,
        forced_save = True,
        *_args):
    """Save a PDF with encryption, markup, & compression handling"""
    file_path = None
    if dialog_text is None:
        dialog_text = "Filename"
    if dialog_title is None:
        dialog_title = "Save PDF"
    while file_path == "" or file_path is None:
        fp_dialog = ctk.CTkInputDialog(text=dialog_text, title=dialog_title)
        file_path = fp_dialog.get_input()
        if forced_save is not True: # Exit after one round.
            if file_path == "" or file_path is None:
                return None
            else:
                break
    file_path = file_path.lower().replace(".pdf", "") + ".pdf"
    garbage_num = 0
    compress = False

    if pdf_doc.compress_max:
        garbage_num  = 4

    if pdf_doc.compress_basic or pdf_doc.compress_max:
        compress = True

    if pdf_doc.custom_metadata["title"] is None:
        pdf_doc.custom_metadata["title"] = file_path.lower().replace(".pdf","").title()
    pdf_doc.custom_metadata["creationDate"] = str(date.today())
    pdf_doc.custom_metadata["modDate"] = str(date.today())

    pdf_doc.doc.set_metadata(pdf_doc.custom_metadata)
    pdf_doc.doc.save(file_path, deflate = compress, garbage = garbage_num) # Save the document.

    for page_i, page in enumerate(pdf_doc.doc):

        # Freehand drawings.
        markings = pdf_doc.freehand_points[page_i]
        page.add_ink_annot(markings)

        # Redactions.
        for redaction_rectlike in pdf_doc.redact_points[page_i]:
            page.add_redact_annot(redaction_rectlike, fill=(0,0,0))
        page.apply_redactions()

        # Highlights.
        for highlight_rectlike in pdf_doc.highlight_points[page_i]:
            highlight = page.add_highlight_annot(highlight_rectlike)
            highlight.update()


    if pdf_doc.password is not None and pdf_doc.password != "":
        perm = int( # Set the permissions for the file.
            fitz.PDF_PERM_ACCESSIBILITY
            | fitz.PDF_PERM_PRINT
            | fitz.PDF_PERM_COPY
            | fitz.PDF_PERM_ANNOTATE
        )
        password = pdf_doc.password
        encrypt_method = fitz.PDF_ENCRYPT_AES_256 # Use the strongest algorithm available.

        # Save the document (with encryption).
        pdf_doc.doc.save(
            file_path,
            deflate = compress,
            garbage = garbage_num,
            encryption = encrypt_method,
            owner_pw=password,
            user_pw=password,
            permissions=perm)
    else:
        # Save the document.
        pdf_doc.doc.save(
            file_path,
            deflate = compress,
            garbage = garbage_num)
    return file_path
