import os
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("AIPIPE_TOKEN"),
    base_url="https://aipipe.org/openai/v1",
)

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
  "invoice_no": null,
  "date": null,
  "vendor": null,
  "amount": null,
  "tax": null,
  "currency": null
}}

Rules:

- amount = subtotal BEFORE tax.
- tax = ONLY the tax amount.
- date must be YYYY-MM-DD.
- currency must be ISO code like INR, USD, EUR, GBP, JPY.
- If a field cannot be found, use null.
- Return ONLY valid JSON.
- Do not wrap the JSON in markdown.

Invoice:

{req.invoice_text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You extract structured data from invoices.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    text = response.choices[0].message.content.strip()

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
                    .replace("€", "")
                    .replace("£", "")
                    .strip()
                )

            data[field] = float(value)

        except Exception:
            data[field] = None

    # Normalize currency
    if isinstance(data.get("currency"), str):
        c = data["currency"].strip().upper()

        mapping = {
            "RS": "INR",
            "RUPEE": "INR",
            "RUPEES": "INR",
            "₹": "INR",
            "$": "USD",
            "US$": "USD",
            "EURO": "EUR",
            "EUROS": "EUR",
            "£": "GBP",
            "POUNDS STERLING": "GBP",
            "YEN": "JPY",
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
