"""
    Author: lefkovitj (https://lefkovitzj.github.io)
    File Last Modified: 8/29/2024
    Project Name: PyPdfApp
    File Name: save.py
"""

# Python Standard Library Imports.
from datetime import date

# Third-party Module Imports.
import fitz
import customtkinter as ctk

def save_pdf(fitz_doc, custom_metadata, compress_basic = False, compress_max = False, password = None, dialog_text=None, dialog_title=None, forced_save = True, *args):
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
                return
            else:
                break
    file_path = file_path.lower().replace(".pdf", "") + ".pdf"
    garbage_num = 0
    compress = False

    if compress_max:
        garbage_num  = 4

    if compress_basic or compress_max:
        compress = True

    if custom_metadata["title"] == None:
        custom_metadata["title"] = file_path.lower().replace(".pdf","").title()
    custom_metadata["creationDate"] = str(date.today())
    custom_metadata["modDate"] = str(date.today())

    fitz_doc.set_metadata(custom_metadata)

    if password != None:
        perm = int( # Set the permissions for the file.
            fitz.PDF_PERM_ACCESSIBILITY
            | fitz.PDF_PERM_PRINT
            | fitz.PDF_PERM_COPY
            | fitz.PDF_PERM_ANNOTATE
        )
        owner_password = password
        owner_pass = owner_password
        user_pass = password
        encrypt_method = fitz.PDF_ENCRYPT_AES_256 # Use the strongest algorithm available.

        fitz_doc.save(file_path, deflate = compress, garbage = garbage_num, encryption = fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password, permissions=perm) # Save the document (with encryption).
    else:
        fitz_doc.save(file_path, deflate = compress, garbage = garbage_num) # Save the document.