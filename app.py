from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvoiceRequest(BaseModel):
    invoice_text: str


def find(patterns, text):
    for p in patterns:
        m = re.search(p, text, re.I | re.M)
        if m:
            return m.group(1).strip()
    return None


def money(x):
    if not x:
        return None
    x = x.replace(",", "").strip()
    try:
        return float(x)
    except:
        return None


@app.post("/extract")
def extract(req: InvoiceRequest):

    txt = req.invoice_text

    invoice_no = None

    patterns = [
        r'(?im)^\s*invoice\s*(?:no\.?|number|#|id)?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-\/]*)',
        r'(?im)^\s*inv\s*(?:no\.?|#)?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-\/]*)',
        r'(?im)^\s*(?:document|bill)\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-\/]*)',
    ]
    for p in patterns:
        m = re.search(p, txt)
        if m:
            invoice_no = m.group(1).strip()
            break

    vendor = find([
        r"Vendor\s*:\s*(.+)",
        r"Seller\s*:\s*(.+)"
    ], txt)

    date_str = find([
        r"Date\s*:\s*(.+)"
    ], txt)

    date = None
    if date_str:
        try:
            date = parser.parse(date_str).strftime("%Y-%m-%d")
        except:
            pass

    def parse_amount(value):
        if value is None:
            return None
    
        value = value.replace(",", "")
        value = re.sub(r"[₹$€£]|Rs\.?|INR|USD|EUR|GBP", "", value, flags=re.I)
        value = value.strip()
    
        try:
            return float(value)
        except:
            return None
    
    
    amount = None
    
    amount_patterns = [
        r"Subtotal\s*[:\-]?\s*([₹$€£A-Za-z.\s0-9,]+)",
        r"Sub\s*Total\s*[:\-]?\s*([₹$€£A-Za-z.\s0-9,]+)",
        r"Net\s*Amount\s*[:\-]?\s*([₹$€£A-Za-z.\s0-9,]+)",
        r"Taxable\s*Value\s*[:\-]?\s*([₹$€£A-Za-z.\s0-9,]+)",
        r"Amount\s*[:\-]?\s*([₹$€£A-Za-z.\s0-9,]+)",
    ]
    
    for p in amount_patterns:
        m = re.search(p, txt, re.I)
        if m:
            amount = parse_amount(m.group(1))
            break

    tax = money(find([
        r"(?:GST|VAT|Tax).*?([0-9,]+\.[0-9]{2})"
    ], txt))

    currency = find([
        r"Currency\s*:\s*([A-Z]{3})",
        r"\b(INR|USD|EUR|GBP)\b",
        r"\bRs\.?\b"
    ], txt)

    if currency == "Rs":
        currency = "INR"

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": currency
    }
