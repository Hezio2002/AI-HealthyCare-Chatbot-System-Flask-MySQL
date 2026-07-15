from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.multi_cell(0, 10, "This is a test PDF about heart disease, diabetes, and hypertension. "
                     "Doctors recommend regular checkups and healthy diets.")
pdf.output("test_medical_info.pdf")
print("PDF created successfully!")
