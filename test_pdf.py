import pdfplumber

def check_pdf_content():
    try:
        with pdfplumber.open("test_medical_info.pdf") as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    print(text)
                else:
                    print("No text found on this page.")
    except Exception as e:
        print(f"Error: {e}")

check_pdf_content()

