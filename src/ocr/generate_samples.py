"""Generate 10 realistic Thai hospital sample documents as PNG images.

3 receipts, 3 discharge summaries, 2 lab reports, 2 prescriptions.
Drawn with Pillow on a white canvas. Run:
    .venv/bin/python -m src.ocr.generate_samples
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_docs"

W, H = 1000, 1400
MARGIN = 60
BLACK = (0, 0, 0)
GRAY = (90, 90, 90)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


F_TITLE = _load_font(34, bold=True)
F_H = _load_font(22, bold=True)
F = _load_font(20)
F_SM = _load_font(17)
F_MONO = _load_font(18)


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (W, H), "white")
        self.d = ImageDraw.Draw(self.img)
        self.y = MARGIN

    def text(self, s, font=F, color=BLACK, x=MARGIN, dy=None, indent=0):
        self.d.text((x + indent, self.y), s, fill=color, font=font)
        self.y += dy if dy is not None else (font.size + 8)

    def header(self, hospital, sub, doctitle):
        self.text(hospital, font=F_TITLE)
        self.text(sub, font=F_SM, color=GRAY)
        self.y += 6
        self.d.line([(MARGIN, self.y), (W - MARGIN, self.y)], fill=BLACK, width=2)
        self.y += 14
        self.text(doctitle, font=F_H)
        self.y += 6

    def kv(self, k, v):
        self.d.text((MARGIN, self.y), f"{k}:", fill=BLACK, font=F)
        self.d.text((MARGIN + 230, self.y), str(v), fill=BLACK, font=F)
        self.y += F.size + 8

    def hr(self):
        self.y += 4
        self.d.line([(MARGIN, self.y), (W - MARGIN, self.y)], fill=GRAY, width=1)
        self.y += 10

    def row(self, cols, widths, font=F, color=BLACK):
        x = MARGIN
        for c, w in zip(cols, widths):
            self.d.text((x, self.y), str(c), fill=color, font=font)
            x += w
        self.y += font.size + 8

    def total_row(self, label, value):
        # Label sits under the Qty/Unit columns; value aligns with the Total
        # column on the far right so it never overlaps the label text.
        self.d.text((MARGIN + 300, self.y), label, fill=BLACK, font=F_H)
        self.d.text((MARGIN + 680, self.y), value, fill=BLACK, font=F_H)
        self.y += F_H.size + 8

    def save(self, name):
        p = OUT_DIR / name
        self.img.save(p)
        return p


# ---------- Receipts ----------

def receipt_1():
    c = Canvas()
    c.header("Bangkok Hospital", "2 Soi Soonvijai 7, New Petchaburi Rd, Bangkok 10310  Tax ID 0107537000123",
             "OFFICIAL RECEIPT / TAX INVOICE")
    c.kv("Receipt No", "RC-2024-008812")
    c.kv("Date", "15/03/2024")
    c.kv("Patient Name", "Mr. Somchai Jaidee")
    c.kv("HN", "00-24-115588")
    c.hr()
    c.row(["Description", "Qty", "Unit Price", "Total"], [430, 110, 200, 160], font=F_H)
    c.hr()
    items = [
        ("Consultation - Internal Medicine", 1, 1200.00, 1200.00),
        ("Complete Blood Count (CBC)", 1, 850.00, 850.00),
        ("Chest X-Ray PA", 1, 1500.00, 1500.00),
        ("Amoxicillin 500mg (cap)", 21, 18.00, 378.00),
        ("Room - General Ward (1 night)", 1, 3200.00, 3200.00),
    ]
    for desc, q, up, t in items:
        c.row([desc, q, f"{up:,.2f}", f"{t:,.2f}"], [430, 110, 200, 160], font=F_SM)
    c.hr()
    c.total_row("GRAND TOTAL (THB)", "7,128.00")
    c.y += 20
    c.kv("Payment Method", "Credit Card (Visa ****4412)")
    c.kv("Cashier", "Ratri P.")
    return c.save("receipt_1_bangkok.png")


def receipt_2():
    c = Canvas()
    c.header("Samitivej Sukhumvit Hospital", "133 Sukhumvit 49, Klongtan Nua, Wattana, Bangkok 10110",
             "RECEIPT")
    c.kv("Receipt No", "SMV-66-009921")
    c.kv("Date", "02/11/2023")
    c.kv("Patient Name", "Ms. Naphat Wongsa")
    c.kv("HN", "SMV-7781200")
    c.hr()
    c.row(["Description", "Qty", "Unit Price", "Total"], [430, 110, 200, 160], font=F_H)
    c.hr()
    items = [
        ("ER Visit Fee", 1, 2000.00, 2000.00),
        ("CT Scan - Brain (non-contrast)", 1, 6500.00, 6500.00),
        ("IV Normal Saline 1000ml", 2, 120.00, 240.00),
        ("Paracetamol Inj 1g", 3, 45.00, 135.00),
        ("Nursing Care", 1, 800.00, 800.00),
    ]
    for desc, q, up, t in items:
        c.row([desc, q, f"{up:,.2f}", f"{t:,.2f}"], [430, 110, 200, 160], font=F_SM)
    c.hr()
    c.total_row("GRAND TOTAL (THB)", "9,675.00")
    c.y += 20
    c.kv("Payment Method", "Cash")
    return c.save("receipt_2_samitivej.png")


def receipt_3_mismatch():
    """Intentional grand_total mismatch: items sum to 4,560 but printed 5,900."""
    c = Canvas()
    c.header("Bumrungrad International Hospital", "33 Sukhumvit Soi 3, Wattana, Bangkok 10110",
             "OFFICIAL RECEIPT / TAX INVOICE")
    c.kv("Receipt No", "BIH-2024-44120")
    c.kv("Date", "28/06/2024")
    c.kv("Patient Name", "Mr. Krit Thavorn")
    c.kv("HN", "BIH-9920031")
    c.hr()
    c.row(["Description", "Qty", "Unit Price", "Total"], [430, 110, 200, 160], font=F_H)
    c.hr()
    items = [
        ("Dermatology Consultation", 1, 1800.00, 1800.00),
        ("Skin Biopsy", 1, 2200.00, 2200.00),
        ("Topical Steroid Cream 15g", 2, 280.00, 560.00),
    ]
    for desc, q, up, t in items:
        c.row([desc, q, f"{up:,.2f}", f"{t:,.2f}"], [430, 110, 200, 160], font=F_SM)
    c.hr()
    # Items sum to 4,560 but we print 5,900 on purpose
    c.total_row("GRAND TOTAL (THB)", "5,900.00")
    c.y += 20
    c.kv("Payment Method", "Insurance (AIA)")
    return c.save("receipt_3_mismatch.png")


# ---------- Discharge summaries ----------

def discharge_1():
    c = Canvas()
    c.header("Bangkok Hospital", "2 Soi Soonvijai 7, New Petchaburi Rd, Bangkok 10310",
             "DISCHARGE SUMMARY")
    c.kv("Patient Name", "Mr. Anan Srisai")
    c.kv("HN", "00-24-330912")
    c.kv("Admission Date", "10/04/2024")
    c.kv("Discharge Date", "14/04/2024")
    c.hr()
    c.text("Primary Diagnosis:", font=F_H)
    c.text("Acute appendicitis (ICD-10 K35.80)", indent=20)
    c.text("Secondary Diagnosis:", font=F_H)
    c.text("Hypertension, essential (ICD-10 I10)", indent=20)
    c.hr()
    c.text("Procedures Performed:", font=F_H)
    c.text("Laparoscopic appendectomy (CPT 44970) on 10/04/2024", indent=20)
    c.hr()
    c.text("Attending Physician:", font=F_H)
    c.text("Dr. Pornchai Chaiyasit, MD (General Surgery)", indent=20)
    c.hr()
    c.text("Discharge Instructions:", font=F_H)
    c.text("Keep wound clean and dry. Avoid heavy lifting for 2 weeks.", indent=20, font=F_SM)
    c.text("Take Cefdinir 300mg twice daily for 7 days. Follow-up in", indent=20, font=F_SM)
    c.text("surgery clinic on 21/04/2024.", indent=20, font=F_SM)
    return c.save("discharge_1_bangkok.png")


def discharge_2():
    c = Canvas()
    c.header("Siriraj Hospital", "2 Wanglang Rd, Bangkok Noi, Bangkok 10700",
             "DISCHARGE SUMMARY")
    c.kv("Patient Name", "Mrs. Wilai Phakdee")
    c.kv("HN", "SIR-118822")
    c.kv("Admission Date", "21/01/2024")
    c.kv("Discharge Date", "27/01/2024")
    c.hr()
    c.text("Primary Diagnosis:", font=F_H)
    c.text("Community-acquired pneumonia (ICD-10 J18.9)", indent=20)
    c.text("Secondary Diagnosis:", font=F_H)
    c.text("Type 2 diabetes mellitus (ICD-10 E11.9)", indent=20)
    c.hr()
    c.text("Procedures Performed:", font=F_H)
    c.text("Chest CT with contrast (CPT 71260)", indent=20)
    c.text("Bronchoscopy (CPT 31622)", indent=20)
    c.hr()
    c.text("Attending Physician:", font=F_H)
    c.text("Dr. Suteera Boonmee, MD (Pulmonology)", indent=20)
    c.hr()
    c.text("Discharge Instructions:", font=F_H)
    c.text("Complete oral antibiotics (Levofloxacin 500mg daily x 5 days).", indent=20, font=F_SM)
    c.text("Monitor blood glucose. Pulmonary follow-up in 2 weeks.", indent=20, font=F_SM)
    return c.save("discharge_2_siriraj.png")


def discharge_3():
    c = Canvas()
    c.header("Samitivej Srinakarin Hospital", "488 Srinagarindra Rd, Suan Luang, Bangkok 10250",
             "DISCHARGE SUMMARY")
    c.kv("Patient Name", "Mr. Teerapat Noi")
    c.kv("HN", "SMV-SR-44120")
    c.kv("Admission Date", "05/05/2024")
    c.kv("Discharge Date", "05/05/2024")
    c.hr()
    c.text("Primary Diagnosis:", font=F_H)
    c.text("Closed fracture of distal radius, left (ICD-10 S52.501A)", indent=20)
    c.text("Secondary Diagnosis:", font=F_H)
    c.text("None", indent=20)
    c.hr()
    c.text("Procedures Performed:", font=F_H)
    c.text("Closed reduction with cast application (CPT 25605)", indent=20)
    c.hr()
    c.text("Attending Physician:", font=F_H)
    c.text("Dr. Nattawut Sang, MD (Orthopedics)", indent=20)
    c.hr()
    c.text("Discharge Instructions:", font=F_H)
    c.text("Keep cast dry. Elevate arm. Ibuprofen 400mg as needed for pain.", indent=20, font=F_SM)
    c.text("Orthopedic follow-up with X-ray in 1 week (12/05/2024).", indent=20, font=F_SM)
    return c.save("discharge_3_samitivej.png")


# ---------- Lab reports ----------

def lab_1():
    c = Canvas()
    c.header("Bangkok Hospital Laboratory", "Dept. of Clinical Pathology, Bangkok 10310",
             "LABORATORY REPORT")
    c.kv("Patient Name", "Mr. Somchai Jaidee")
    c.kv("HN", "00-24-115588")
    c.kv("Collection Date", "15/03/2024")
    c.hr()
    c.row(["Test", "Result", "Unit", "Reference", "Flag"], [300, 130, 110, 200, 100], font=F_H)
    c.hr()
    tests = [
        ("Hemoglobin", "11.2", "g/dL", "13.0 - 17.0", "L"),
        ("WBC", "12.8", "10^3/uL", "4.0 - 10.0", "H"),
        ("Platelets", "250", "10^3/uL", "150 - 400", ""),
        ("Glucose (Fasting)", "142", "mg/dL", "70 - 100", "H"),
        ("Creatinine", "0.9", "mg/dL", "0.6 - 1.2", ""),
    ]
    for t in tests:
        c.row(list(t), [300, 130, 110, 200, 100], font=F_SM)
    c.hr()
    c.text("L = Low, H = High. Verified by Dr. Apinya Lab MD.", font=F_SM, color=GRAY)
    return c.save("lab_1_bangkok.png")


def lab_2():
    c = Canvas()
    c.header("N Health Laboratory", "BDMS Wellness, Bangkok 10330",
             "LABORATORY REPORT")
    c.kv("Patient Name", "Ms. Naphat Wongsa")
    c.kv("HN", "SMV-7781200")
    c.kv("Collection Date", "02/11/2023")
    c.hr()
    c.row(["Test", "Result", "Unit", "Reference", "Flag"], [300, 130, 110, 200, 100], font=F_H)
    c.hr()
    tests = [
        ("Total Cholesterol", "245", "mg/dL", "< 200", "H"),
        ("LDL Cholesterol", "168", "mg/dL", "< 130", "H"),
        ("HDL Cholesterol", "42", "mg/dL", "> 40", ""),
        ("Triglycerides", "210", "mg/dL", "< 150", "H"),
        ("TSH", "2.1", "mIU/L", "0.4 - 4.0", ""),
    ]
    for t in tests:
        c.row(list(t), [300, 130, 110, 200, 100], font=F_SM)
    c.hr()
    c.text("Reviewed by Dr. Chaiwat Path MD.", font=F_SM, color=GRAY)
    return c.save("lab_2_nhealth.png")


# ---------- Prescriptions ----------

def prescription_1():
    c = Canvas()
    c.header("Bangkok Hospital", "Outpatient Pharmacy, Bangkok 10310",
             "PRESCRIPTION")
    c.kv("Doctor", "Dr. Pornchai Chaiyasit, MD")
    c.kv("Patient Name", "Mr. Anan Srisai")
    c.kv("Date", "14/04/2024")
    c.hr()
    c.row(["Medication", "Dosage", "Frequency", "Duration", "Qty"], [280, 140, 200, 150, 80], font=F_H)
    c.hr()
    meds = [
        ("Cefdinir", "300mg", "Twice daily", "7 days", "14"),
        ("Paracetamol", "500mg", "Every 6h prn", "5 days", "20"),
        ("Omeprazole", "20mg", "Once daily", "14 days", "14"),
    ]
    for m in meds:
        c.row(list(m), [280, 140, 200, 150, 80], font=F_SM)
    c.hr()
    c.text("Take with food. Complete full antibiotic course.", font=F_SM, color=GRAY)
    return c.save("prescription_1_bangkok.png")


def prescription_2():
    c = Canvas()
    c.header("Siriraj Hospital", "Pharmacy Dept, Bangkok 10700",
             "PRESCRIPTION")
    c.kv("Doctor", "Dr. Suteera Boonmee, MD")
    c.kv("Patient Name", "Mrs. Wilai Phakdee")
    c.kv("Date", "27/01/2024")
    c.hr()
    c.row(["Medication", "Dosage", "Frequency", "Duration", "Qty"], [280, 140, 200, 150, 80], font=F_H)
    c.hr()
    meds = [
        ("Levofloxacin", "500mg", "Once daily", "5 days", "5"),
        ("Metformin", "850mg", "Twice daily", "30 days", "60"),
        ("Salbutamol Inhaler", "100mcg", "2 puffs prn", "1 inhaler", "1"),
    ]
    for m in meds:
        c.row(list(m), [280, 140, 200, 150, 80], font=F_SM)
    c.hr()
    c.text("Monitor blood glucose daily.", font=F_SM, color=GRAY)
    return c.save("prescription_2_siriraj.png")


GENERATORS = [
    receipt_1, receipt_2, receipt_3_mismatch,
    discharge_1, discharge_2, discharge_3,
    lab_1, lab_2,
    prescription_1, prescription_2,
]


def generate_all() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [g() for g in GENERATORS]
    return paths


if __name__ == "__main__":
    for p in generate_all():
        print("wrote", p)
