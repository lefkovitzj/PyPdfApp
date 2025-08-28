"""
    Author: lefkovitj (https://lefkovitzj.github.io)
    File Last Modified: 1/4/2025
    Project Name: PyPdfApp
    File Name: save.py
"""

# Python Standard Library Imports.
from datetime import date

# Third-party Module Imports.
import fitz
import customtkinter as ctk

def save_pdf(pdf_doc_instance_object, compress_basic = False, compress_max = False, password = None, dialog_text=None, dialog_title=None, forced_save = True, *args):
    file_path = None
    if dialog_text == None:
        dialog_text = "Filename"
    if dialog_title == None:
        dialog_title = "Save PDF"
    while file_path == "" or file_path == None:
        fp_dialog = ctk.CTkInputDialog(text=dialog_text, title=dialog_title)
        file_path = fp_dialog.get_input()
        if forced_save != True: # Exit after one round.
            if file_path == "" or file_path == None:
                return None
            else:
                break
    file_path = file_path.lower().replace(".pdf", "") + ".pdf"
    garbage_num = 0
    compress = False

    if pdf_doc_instance_object.compress_max:
        garbage_num  = 4

    if pdf_doc_instance_object.compress_basic or pdf_doc_instance_object.compress_max:
        compress = True

    if pdf_doc_instance_object.custom_metadata["title"] == None:
        pdf_doc_instance_object.custom_metadata["title"] = file_path.lower().replace(".pdf","").title()
    pdf_doc_instance_object.custom_metadata["creationDate"] = str(date.today())
    pdf_doc_instance_object.custom_metadata["modDate"] = str(date.today())

    pdf_doc_instance_object.doc.set_metadata(pdf_doc_instance_object.custom_metadata)
    pdf_doc_instance_object.doc.save(file_path, deflate = compress, garbage = garbage_num) # Save the document.

    for page_i in range(len(pdf_doc_instance_object.doc)):
        page = pdf_doc_instance_object.doc[page_i]

        # Freehand drawings.
        markings = pdf_doc_instance_object.freehand_points[page_i]
        page.add_ink_annot(markings)

        # Redactions.
        for redaction_rectlike in pdf_doc_instance_object.redact_points[page_i]:
            page.add_redact_annot(redaction_rectlike, fill=(0,0,0))
        page.apply_redactions()

        # Highlights.
        for highlight_rectlike in pdf_doc_instance_object.highlight_points[page_i]:
            highlight = page.add_highlight_annot(highlight_rectlike)
            highlight.update()


    if pdf_doc_instance_object.password != None and pdf_doc_instance_object.password != "":
        perm = int( # Set the permissions for the file.
            fitz.PDF_PERM_ACCESSIBILITY
            | fitz.PDF_PERM_PRINT
            | fitz.PDF_PERM_COPY
            | fitz.PDF_PERM_ANNOTATE
        )
        owner_password = pdf_doc_instance_object.password
        owner_pass = owner_password
        user_pass = pdf_doc_instance_object.password
        encrypt_method = fitz.PDF_ENCRYPT_AES_256 # Use the strongest algorithm available.

        pdf_doc_instance_object.doc.save(file_path, deflate = compress, garbage = garbage_num, encryption = fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password, permissions=perm) # Save the document (with encryption).
    else:
        pdf_doc_instance_object.doc.save(file_path, deflate = compress, garbage = garbage_num) # Save the document.
    return file_path