"""
    Author: lefkovitj (https://lefkovitzj.com)
    File Last Modified: 8/28/2025
    Project Name: PyPdfApp
    File Name: utils.py
"""

import os

class PdfDocInstance():
    """ Class to represent an instance in the GUI of a single PDF document. """
    def __init__(self, file_path, doc, password ):
        """Initialize the PDF Document Instance object."""
        self.save_path = file_path
        self.doc = doc
        self.password = password

        self.name = os.path.split(self.save_path)[-1]
        self.compress_basic = False
        self.compress_max = False
        self.page_i = 0
        self.custom_metadata = {"creator": "PyPdfApp", "producer": "PyPdfApp", "title": None}
        self.freehand_points = [[] for i in range(len(self.doc))]
        self.redact_points = [[] for i in range(len(self.doc))]
        self.highlight_points = [[] for i in range(len(self.doc))]
        self.active_stroke = []
        self.mods_made = False

    def add_page_data(self, at_index):
        """Add a new page's data at the specified index"""
        self.freehand_points.insert(at_index, [])
        self.redact_points.insert(at_index, [])
        self.highlight_points.insert(at_index, [])

    def remove_page_data(self, at_index):
        """Remove the page's data at the specified index"""
        del self.freehand_points[at_index]
        del self.redact_points[at_index]
        del self.highlight_points[at_index]

    def __str__(self):
        return self.name

class PdfQueue():
    """ Hold and process a queue of PdfDocInstance objects. """
    def __init__(self):
        self.queue = {}

    def is_empty(self):
        """ Check whether the queue is empty. """
        return not self.queue

    def add_pdf(self, pdf_instance):
        """Add the PDF to the queue"""
        if isinstance(pdf_instance, PdfDocInstance):
            if pdf_instance.name not in self.queue.keys():
                self.queue[pdf_instance.name] = pdf_instance
                return pdf_instance.name
            else:
                duplicate_name_i = 1
                # Find the displayable name in the format of "pdf_instance.name | duplicate_name_i"
                # such that it is unique in the dictionary keys.
                while f"{pdf_instance.name} | {duplicate_name_i}" in self.queue.keys():
                    duplicate_name_i += 1
                self.queue[f"{pdf_instance.name} | {duplicate_name_i}"] = pdf_instance
                return f"{pdf_instance.name} | {duplicate_name_i}"
        else:
            raise TypeError("PdfQueue cannot add objects of type other than PdfDocInstance.")

    def remove_pdf(self, pdf_instance_key):
        """Remove PDF from the queue, process each item's key, updating duplicate names as needed"""
        removed_pdf = self.queue[pdf_instance_key]
        name_to_check = removed_pdf.name
        removed_key_parts = pdf_instance_key.split(" |")
        if len(removed_key_parts) > 1:
            removed_i = int(removed_key_parts[-1])
        else:
            removed_i = 0

        updated_queue = {}
        for instance_key, instance_pdf in self.queue.items():
            instance_key_parts = instance_key.split(" | ")
            if len(instance_key_parts) == 1: # Initial item, lacks identifying number, use 0.
                instance_key_parts.append("0")
            if instance_key_parts[0] == name_to_check:
                # The instance key needs updated  (identifying number is greater than the removed).
                if int(instance_key_parts[-1]) > removed_i:
                    if int(instance_key_parts[-1]) - 1 < 1:
                        updated_queue[f"{instance_key_parts[0]}"] = instance_pdf
                    else:
                        updated_queue[
                            f"{instance_key_parts[0]} | {int(instance_key_parts[-1]) - 1}"
                        ] = instance_pdf
                # The instance key matches exactly, don't add the item to the new queue.
                elif int(instance_key_parts[-1]) == removed_i:
                    pass
                # The instance key does not need updated (identifying number < removed).
                else:
                    updated_queue[instance_key] = instance_pdf
            # The instance does not share the duplicate name.
            else:
                updated_queue[instance_key] = instance_pdf

        self.queue = updated_queue

    def set_unsaved(self, pdf_instance_key):
        """Format to denote that the PDF's current state has not been saved"""
        self.queue[pdf_instance_key].mods_made = True

    def set_saved(self, pdf_instance_key):
        """Format to denote that the PDF's current state has been saved"""
        self.queue[pdf_instance_key].mods_made = False

    def get_keys(self):
        """Get the keys of the queue attribute as a list of strings"""
        return_keys = []
        for key, value in self.queue.items():
            if value.mods_made:
                return_keys.append(f"*{key}")
            else:
                return_keys.append(key)
        return return_keys

    def get_unsaved(self):
        """Get the keys of the queue attribute as a list of strings"""
        return_keys = []
        for key, value in self.queue.items():
            if value.mods_made:
                return_keys.append(key)
        return return_keys

    def __getitem__(self, key):
        """Allow for queue access via [...] syntax"""
        return self.queue[key]
