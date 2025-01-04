import fitz

doc = fitz.open("C:/Users/lefko/OneDrive/Documents/Python Stuff/PyPdfApp/Sample PDFs/demo.pdf")

for page in doc:
    for page_link in page.get_links():
        print(page_link)

