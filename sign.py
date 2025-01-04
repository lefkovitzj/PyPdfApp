import os
import urllib.request
import urllib.parse
import requests

from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS

def store_bins(file_name, bin1, bin2):
    with open(file_name, 'wb') as f: # Write the two chunks of binary data to the file.
        f.write(bin1)
        f.write(bin2)
    f.close()
def read_bins(file_name):
    with open(file_name, 'rb') as f: # Split the file, returning the two 64-byte chunks.
        bin1 = f.read(64)
        bin2 = f.read(64)
    return bin1, bin2

def is_url(url):
    """ Return whether or not the argument is a url. """
    return (urllib.parse.urlparse(url).scheme in ['http', 'https'])

def load_resource(resource_location):
    """ Load the resource data from the passed location. """
    if is_url(resource_location):
        with urllib.request.urlopen(resource_location) as file_obj: # Load from a file hosted at the URL.
            resource_bytes = file_obj.read()
    else:
        with open(resource_location, "rb") as file_obj: # Load from a file hosted on at the file_path
            resource_bytes = file_obj.read()
    return resource_bytes # Return the file as a bytes object.

def post_resource(resource_location, data):
    """ Post the resource data to the passed location. """
    if is_url(resource_location): # Post the resource to the URL
        status = (requests.post(resource_location, data).status_code == requests.codes.ok)
    else: # Post the resource to a file on the device.
        with open(resource_location, "wb") as file_obj:
            file_obj.write(data)
        status = True
    return "Uploaded successfully." if status else "Upload failed."

def gen_signature_keys(new_pubkey_path, uname, pwd):
    """ Generate the public and private keys for the account with credentials uname and pwd. """
    mykey = ECC.generate(curve='p256')
    with open(f"{uname.replace(' ','_')}_private_key.pem", "wb") as f: # Export the privkey to a .pem file.
        data = mykey.export_key(format='DER',
                                    passphrase=pwd,
                                    protection='PBKDF2WithHMAC-SHA512AndAES256-CBC',
                                    prot_params={'iteration_count':131072})
        f.write(data)
    data = mykey.public_key().export_key(format="DER") # Export the pubkey to a file.
    post_resource(new_pubkey_path, data)
    return (new_pubkey_path, f"{uname.replace(' ','_')}_private_key.pem") # Return the locations of both files.

def sign_pdf(signature_path, pdf_path, uname, pwd, privkey_path):
    """ Sign pdf_path with the account credentials uname and pwd. """
    with open(pdf_path, "rb") as pdf_file: # Load the file data from the PDF path.
        pdf_data = pdf_file.read()
    data_hash = SHA256.new(pdf_data) # Hash both values.
    name_hash = SHA256.new(uname.encode("utf-8"))

    key = ECC.import_key(open(f'{privkey_path}', "rb").read(), passphrase=pwd.encode("utf-8")) # Import the privkey.
    data_signer = DSS.new(key, 'fips-186-3')
    name_signer = DSS.new(key, 'fips-186-3')
    data_signature = data_signer.sign(data_hash) # Sign both values and return them.
    name_signature = name_signer.sign(name_hash)
    store_bins(signature_path, data_signature, name_signature)
    return f"PDF signature by {uname} was stored in file \"{signature_path}\" successfully."

def verify_pdf_signature(signature_path, pdf_path, pubkey_path, name):
    """ Verify the signature of pdf_path by uname's private key. """
    if (os.path.getsize(signature_path) != 128): # Sanity check to ensure that the file has two 64-byte signatures (no more, no less).
        return "Warning: Signature file has been tampered with."
    with open(pdf_path, "rb") as pdf_file: # Load the PDF from a file on the device.
        pdf_data = pdf_file.read()
    data_signature, name_signature = read_bins(signature_path)
    key = ECC.import_key(load_resource(pubkey_path)) # Load the pubkey from online or a file.
    data_hash = SHA256.new(pdf_data) # Compute new hashes of the data and name that should match the signed values.
    name_hash = SHA256.new(name.encode("utf-8"))
    verifier = DSS.new(key, 'fips-186-3') # Create a verifier for the values using the pubkey.
    verification_errors = []
    try:
        verifier.verify(name_hash, name_signature) # Check the hashed name matches the one for the pubkey.
        try:
            verifier.verify(data_hash, data_signature) # Check that the PDF file matches the signed data.
            return "PDF signature is valid." # The signature passes as both verifications succeeded.
        except ValueError:
            verification_errors.append("WARNING: Data hash invalid - PDF file does not match or signature has been tampered with!")
    except ValueError:
        verification_errors.append("WARNING: Signer hash invalid - Signature has been tampered with or signer name is incorrect in the filename!")
    return verification_errors # One or more verifications failed, warn the user.