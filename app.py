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

    invoice_no = find([
        r"Invoice\s*(?:No|#|Number)?\s*[:#]?\s*([A-Za-z0-9\-\/]+)"
    ], txt)

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

    amount = money(find([
        r"Subtotal.*?([0-9,]+\.[0-9]{2})"
    ], txt))

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
