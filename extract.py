"""
    Author: lefkovitj (https://lefkovitzj.github.io)
    File Last Modified: 8/15/2024
    Project Name: PyPdfApp
    File Name: extract.py
"""

import fitz
import datetime
import os

def calculate_pdf_temp_title(action, file_ending=".pdf"):
    tb = str(datetime.datetime.today()) # Basic timestamp string, with the type of action included.
    file_title = tb[:4] + "-" + tb[5:7] + "-" + tb[8:10] + "_" + tb[11:13] + "-" + tb[14:16] + "-" + tb[17:19] + "_" + action + file_ending
    return file_title

class PDF_Extractor():
    def __init__(self, fitz_doc):
        """ Initialize the object. """
        if "temporary_files" not in os.listdir(os.getcwd()): # Ensure that the necessary save folder exists.
            os.makedirs("temporary_files")
        self.doc = fitz_doc
    def extract_text(self, file_loc):
        """ Extract text from the PDF. """
        file_loc.replace(".txt", "")
        file_loc += ".txt"
        with open(file_loc, "w") as text_file: # Open the output .txt file.
            for page_i in self.doc: # Iterate through each page.
                page_text = page_i.get_text("text") # Extract the page's text and add it to the .txt file.
                text_file.write("Text extracted from PDF file by PyPdfUtils: \n\nSTART OF EXTRACTED TEXT\n")
                text_file.write(page_text + "\n")
                text_file.write("END OF EXTRACTED TEXT")
        text_file.close() # Close the .txt file.
        return True, file_loc
    def extract_images(self, file_dir):
        """ Extract images from the PDF. """
        os.mkdir(file_dir)
        img_num = 1
        for page_i in self.doc: # Iterate through each page.
            for page_image_list in page_i.get_images():
                xref_id = page_image_list[0] # Get the xref of the image.
                page_image = self.doc.extract_image(xref_id) # Extract the image from the page.
                with open(file_dir + "\\image_" + str(img_num) + "." + page_image["ext"], 'wb') as img_bin: # Save the extracted image to the temporary file directory.
                    img_bin.write(page_image["image"])
                img_bin.close()
                img_num += 1
        return True, file_dir