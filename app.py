import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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


@app.post("/extract")
def extract(req: InvoiceRequest):

    prompt = f"""
You are an invoice information extraction engine.

Extract these fields from the invoice.

Return ONLY valid JSON.

Schema:

{{
  "invoice_no": string|null,
  "date": string|null,
  "vendor": string|null,
  "amount": number|null,
  "tax": number|null,
  "currency": string|null
}}

Rules:

- amount = subtotal BEFORE tax.
- tax = ONLY the tax amount.
- date must be YYYY-MM-DD.
- currency must be ISO code like INR, USD, EUR, GBP.
- If a field cannot be found, use null.
- Return JSON only.

Invoice:

{req.invoice_text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    text = response.text.strip()

    # Remove markdown fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.startswith("```")]
        text = "\n".join(lines)

    data = json.loads(text)

    # Normalize date
    if data.get("date"):
        try:
            data["date"] = parser.parse(data["date"]).strftime("%Y-%m-%d")
        except Exception:
            data["date"] = None

    # Normalize numeric values
    for field in ("amount", "tax"):
        value = data.get(field)
        if value is None:
            continue
        try:
            if isinstance(value, str):
                value = (
                    value.replace(",", "")
                    .replace("₹", "")
                    .replace("Rs.", "")
                    .replace("Rs", "")
                    .replace("$", "")
                    .strip()
                )
            data[field] = float(value)
        except Exception:
            data[field] = None

    # Normalize currency
    if isinstance(data.get("currency"), str):
        c = data["currency"].upper()
        mapping = {
            "RS": "INR",
            "RUPEES": "INR",
            "RUPEE": "INR",
            "₹": "INR"
        }
        data["currency"] = mapping.get(c, c)

    return {
        "invoice_no": data.get("invoice_no"),
        "date": data.get("date"),
        "vendor": data.get("vendor"),
        "amount": data.get("amount"),
        "tax": data.get("tax"),
        "currency": data.get("currency"),
    }
