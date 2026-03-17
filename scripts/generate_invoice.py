from pathlib import Path
from datetime import datetime, timedelta
import random

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).resolve().parent.parent
SUPPLIERS_FILE = BASE_DIR / "data" / "raw" / "suppliers" / "suppliers.csv"
DOCUMENTS_DIR = BASE_DIR / "data" / "raw" / "documents"


def generate_invoice_number() -> str:
    year = datetime.now().year
    number = random.randint(1, 9999)
    return f"FAC-{year}-{number:04d}"


def generate_invoice_data(supplier: pd.Series) -> dict:
    issue_date = datetime.now().date()
    due_date = issue_date + timedelta(days=30)

    quantity = random.randint(50, 500)
    unit = random.choice(["m²", "paire", "unité", "mètre"])
    unit_price = round(random.uniform(2.0, 25.0), 2)
    amount_ht = round(quantity * unit_price, 2)
    amount_tva = round(amount_ht * 0.20, 2)
    amount_ttc = round(amount_ht + amount_tva, 2)

    return {
        "invoice_number": generate_invoice_number(),
        "issue_date": issue_date.strftime("%d/%m/%Y"),
        "due_date": due_date.strftime("%d/%m/%Y"),
        "company_name": supplier["company_name"],
        "address": supplier["address"],
        "postal_code": supplier["postal_code"],
        "city": supplier["city"],
        "siren": supplier["siren"],
        "siret": supplier["siret"],
        "vat_number": supplier["vat_number"],
        "product_name": supplier["material_specialty"],
        "quantity": quantity,
        "unit": unit,
        "unit_price": unit_price,
        "amount_ht": amount_ht,
        "amount_tva": amount_tva,
        "amount_ttc": amount_ttc,
        "currency": "EUR",
    }


def create_invoice_pdf(invoice_data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    # Titre
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "FACTURE")

    # Numéro et dates
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 90, f"Numéro de facture : {invoice_data['invoice_number']}")
    c.drawString(50, height - 110, f"Date d'émission : {invoice_data['issue_date']}")
    c.drawString(50, height - 130, f"Date d'échéance : {invoice_data['due_date']}")

    # Informations fournisseur
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 170, "Fournisseur")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 190, invoice_data["company_name"])
    c.drawString(50, height - 210, invoice_data["address"])
    c.drawString(50, height - 230, f"{invoice_data['postal_code']} {invoice_data['city']}")
    c.drawString(50, height - 250, f"SIREN : {invoice_data['siren']}")
    c.drawString(50, height - 270, f"SIRET : {invoice_data['siret']}")
    c.drawString(50, height - 290, f"TVA : {invoice_data['vat_number']}")

    # Client fictif
    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 170, "Client")
    c.setFont("Helvetica", 11)
    c.drawString(320, height - 190, "StepAhead Industries")
    c.drawString(320, height - 210, "18 rue de l'Industrie")
    c.drawString(320, height - 230, "69000 Lyon")

    # Tableau produit
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 340, "Produit")
    c.drawString(260, height - 340, "Qté")
    c.drawString(310, height - 340, "Unité")
    c.drawString(380, height - 340, "P.U. HT")
    c.drawString(460, height - 340, "Total HT")

    c.line(50, height - 345, 540, height - 345)

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 370, str(invoice_data["product_name"])[:30])
    c.drawString(260, height - 370, str(invoice_data["quantity"]))
    c.drawString(310, height - 370, str(invoice_data["unit"]))
    c.drawString(380, height - 370, f"{invoice_data['unit_price']:.2f} EUR")
    c.drawString(460, height - 370, f"{invoice_data['amount_ht']:.2f} EUR")

    # Totaux
    c.line(300, height - 430, 540, height - 430)

    c.setFont("Helvetica", 11)
    c.drawString(320, height - 455, f"Total HT : {invoice_data['amount_ht']:.2f} EUR")
    c.drawString(320, height - 475, f"TVA 20% : {invoice_data['amount_tva']:.2f} EUR")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 500, f"Total TTC : {invoice_data['amount_ttc']:.2f} EUR")

    # Pied de page
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 50, "")

    c.save()


def main() -> None:
    if not SUPPLIERS_FILE.exists():
        raise FileNotFoundError(
            f"Le fichier suppliers.csv est introuvable : {SUPPLIERS_FILE}"
        )

    df = pd.read_csv(SUPPLIERS_FILE)

    if df.empty:
        raise ValueError("Le fichier suppliers.csv est vide.")

    supplier = df.iloc[0]
    supplier_id = supplier["supplier_id"]

    invoice_data = generate_invoice_data(supplier)

    output_path = DOCUMENTS_DIR / supplier_id / "invoice.pdf"
    create_invoice_pdf(invoice_data, output_path)

    print("Facture générée avec succès :")
    print(output_path)


if __name__ == "__main__":
    main()