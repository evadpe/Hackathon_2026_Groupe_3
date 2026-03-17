from pathlib import Path
from datetime import datetime, timedelta
import random

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).resolve().parent.parent
SUPPLIERS_FILE = BASE_DIR / "data" / "raw" / "suppliers" / "suppliers.csv"
DOCUMENTS_DIR = BASE_DIR / "data" / "raw" / "documents"

BUYER_COMPANY = {
    "company_name": "StepAhead Industries",
    "address": "18 rue de l'Industrie",
    "postal_code": "69000",
    "city": "Lyon",
    "country": "France",
    "siren": "812345678",
    "siret": "81234567800021",
    "vat_number": "FR12812345678",
}


def generate_purchase_order_number() -> str:
    year = datetime.now().year
    number = random.randint(1, 9999)
    return f"BC-{year}-{number:04d}"


def generate_quote_number() -> str:
    year = datetime.now().year
    number = random.randint(1, 9999)
    return f"DEV-{year}-{number:04d}"


def generate_invoice_number() -> str:
    year = datetime.now().year
    number = random.randint(1, 9999)
    return f"FAC-{year}-{number:04d}"


def generate_shared_business_data(supplier: pd.Series) -> dict:
    issue_date = datetime.now().date()
    due_date = issue_date + timedelta(days=30)
    valid_until = issue_date + timedelta(days=30)

    quantity = random.randint(50, 500)
    unit = random.choice(["m²", "paire", "unité", "mètre"])
    unit_price = round(random.uniform(2.0, 25.0), 2)
    amount_ht = round(quantity * unit_price, 2)
    amount_tva = round(amount_ht * 0.20, 2)
    amount_ttc = round(amount_ht + amount_tva, 2)

    return {
        "issue_date": issue_date.strftime("%d/%m/%Y"),
        "due_date": due_date.strftime("%d/%m/%Y"),
        "valid_until": valid_until.strftime("%d/%m/%Y"),
        "product_name": supplier["material_specialty"],
        "quantity": quantity,
        "unit": unit,
        "unit_price": unit_price,
        "amount_ht": amount_ht,
        "amount_tva": amount_tva,
        "amount_ttc": amount_ttc,
        "currency": "EUR",
    }


def create_purchase_order_pdf(order_data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    _, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "BON DE COMMANDE")

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 90, f"Numéro : {order_data['purchase_order_number']}")
    c.drawString(50, height - 110, f"Date : {order_data['issue_date']}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 160, "Acheteur / Émetteur")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 180, order_data["buyer_company_name"])
    c.drawString(50, height - 198, order_data["buyer_address"])
    c.drawString(50, height - 216, f"{order_data['buyer_postal_code']} {order_data['buyer_city']}")
    c.drawString(50, height - 234, f"SIREN : {order_data['buyer_siren']}")
    c.drawString(50, height - 252, f"SIRET : {order_data['buyer_siret']}")
    c.drawString(50, height - 270, f"TVA : {order_data['buyer_vat_number']}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 160, "Fournisseur")
    c.setFont("Helvetica", 10)
    c.drawString(320, height - 180, order_data["supplier_company_name"])
    c.drawString(320, height - 198, order_data["supplier_address"])
    c.drawString(320, height - 216, f"{order_data['supplier_postal_code']} {order_data['supplier_city']}")
    c.drawString(320, height - 234, f"SIREN : {order_data['supplier_siren']}")
    c.drawString(320, height - 252, f"SIRET : {order_data['supplier_siret']}")
    c.drawString(320, height - 270, f"TVA : {order_data['supplier_vat_number']}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 320, "Détail de la commande")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 350, "Produit")
    c.drawString(260, height - 350, "Qté")
    c.drawString(310, height - 350, "Unité")
    c.drawString(380, height - 350, "P.U. prévu")
    c.drawString(470, height - 350, "Total HT")

    c.line(50, height - 355, 545, height - 355)

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 380, str(order_data["product_name"])[:30])
    c.drawString(260, height - 380, str(order_data["quantity"]))
    c.drawString(310, height - 380, str(order_data["unit"]))
    c.drawString(380, height - 380, f"{order_data['unit_price']:.2f} EUR")
    c.drawString(470, height - 380, f"{order_data['amount_ht']:.2f} EUR")

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 70, "Bon de commande synthétique généré automatiquement pour le projet étudiant.")
    c.drawString(50, 50, "Document servant de base au rapprochement avec le devis et la facture.")

    c.save()


def create_quote_pdf(quote_data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    _, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "DEVIS")

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 90, f"Numéro de devis : {quote_data['quote_number']}")
    c.drawString(50, height - 110, f"Date d'émission : {quote_data['issue_date']}")
    c.drawString(50, height - 130, f"Valable jusqu'au : {quote_data['valid_until']}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 170, "Fournisseur")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 190, quote_data["supplier_company_name"])
    c.drawString(50, height - 210, quote_data["supplier_address"])
    c.drawString(50, height - 230, f"{quote_data['supplier_postal_code']} {quote_data['supplier_city']}")
    c.drawString(50, height - 250, f"SIREN : {quote_data['supplier_siren']}")
    c.drawString(50, height - 270, f"SIRET : {quote_data['supplier_siret']}")
    c.drawString(50, height - 290, f"TVA : {quote_data['supplier_vat_number']}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 170, "Client")
    c.setFont("Helvetica", 11)
    c.drawString(320, height - 190, quote_data["buyer_company_name"])
    c.drawString(320, height - 210, quote_data["buyer_address"])
    c.drawString(320, height - 230, f"{quote_data['buyer_postal_code']} {quote_data['buyer_city']}")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 340, "Produit")
    c.drawString(260, height - 340, "Qté")
    c.drawString(310, height - 340, "Unité")
    c.drawString(380, height - 340, "P.U. HT")
    c.drawString(460, height - 340, "Total HT")

    c.line(50, height - 345, 540, height - 345)

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 370, str(quote_data["product_name"])[:30])
    c.drawString(260, height - 370, str(quote_data["quantity"]))
    c.drawString(310, height - 370, str(quote_data["unit"]))
    c.drawString(380, height - 370, f"{quote_data['unit_price']:.2f} EUR")
    c.drawString(460, height - 370, f"{quote_data['amount_ht']:.2f} EUR")

    c.line(300, height - 430, 540, height - 430)

    c.setFont("Helvetica", 11)
    c.drawString(320, height - 455, f"Total HT : {quote_data['amount_ht']:.2f} EUR")
    c.drawString(320, height - 475, f"TVA 20% : {quote_data['amount_tva']:.2f} EUR")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 500, f"Total TTC : {quote_data['amount_ttc']:.2f} EUR")

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 70, "Ce devis est valable 30 jours à compter de sa date d'émission.")
    c.drawString(50, 50, "Document synthétique généré automatiquement pour le projet étudiant.")

    c.save()


def create_invoice_pdf(invoice_data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    _, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "FACTURE")

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 90, f"Numéro de facture : {invoice_data['invoice_number']}")
    c.drawString(50, height - 110, f"Date d'émission : {invoice_data['issue_date']}")
    c.drawString(50, height - 130, f"Date d'échéance : {invoice_data['due_date']}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 170, "Fournisseur")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 190, invoice_data["supplier_company_name"])
    c.drawString(50, height - 210, invoice_data["supplier_address"])
    c.drawString(50, height - 230, f"{invoice_data['supplier_postal_code']} {invoice_data['supplier_city']}")
    c.drawString(50, height - 250, f"SIREN : {invoice_data['supplier_siren']}")
    c.drawString(50, height - 270, f"SIRET : {invoice_data['supplier_siret']}")
    c.drawString(50, height - 290, f"TVA : {invoice_data['supplier_vat_number']}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 170, "Client")
    c.setFont("Helvetica", 11)
    c.drawString(320, height - 190, invoice_data["buyer_company_name"])
    c.drawString(320, height - 210, invoice_data["buyer_address"])
    c.drawString(320, height - 230, f"{invoice_data['buyer_postal_code']} {invoice_data['buyer_city']}")

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

    c.line(300, height - 430, 540, height - 430)

    c.setFont("Helvetica", 11)
    c.drawString(320, height - 455, f"Total HT : {invoice_data['amount_ht']:.2f} EUR")
    c.drawString(320, height - 475, f"TVA 20% : {invoice_data['amount_tva']:.2f} EUR")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 500, f"Total TTC : {invoice_data['amount_ttc']:.2f} EUR")

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 50, "Document synthétique généré automatiquement pour le projet étudiant.")

    c.save()


def generate_bundle_for_supplier(supplier: pd.Series) -> None:
    supplier_id = supplier["supplier_id"]

    shared_data = generate_shared_business_data(supplier)

    common_part = {
        "buyer_company_name": BUYER_COMPANY["company_name"],
        "buyer_address": BUYER_COMPANY["address"],
        "buyer_postal_code": BUYER_COMPANY["postal_code"],
        "buyer_city": BUYER_COMPANY["city"],
        "buyer_country": BUYER_COMPANY["country"],
        "buyer_siren": BUYER_COMPANY["siren"],
        "buyer_siret": BUYER_COMPANY["siret"],
        "buyer_vat_number": BUYER_COMPANY["vat_number"],
        "supplier_company_name": supplier["company_name"],
        "supplier_address": supplier["address"],
        "supplier_postal_code": supplier["postal_code"],
        "supplier_city": supplier["city"],
        "supplier_country": supplier["country"],
        "supplier_siren": supplier["siren"],
        "supplier_siret": supplier["siret"],
        "supplier_vat_number": supplier["vat_number"],
        **shared_data,
    }

    purchase_order_data = {
        "purchase_order_number": generate_purchase_order_number(),
        **common_part,
    }

    quote_data = {
        "quote_number": generate_quote_number(),
        **common_part,
    }

    invoice_data = {
        "invoice_number": generate_invoice_number(),
        **common_part,
    }

    output_dir = DOCUMENTS_DIR / supplier_id
    create_purchase_order_pdf(purchase_order_data, output_dir / "purchase_order.pdf")
    create_quote_pdf(quote_data, output_dir / "quote.pdf")
    create_invoice_pdf(invoice_data, output_dir / "invoice.pdf")


def main(n_bundles: int = 10) -> None:
    if not SUPPLIERS_FILE.exists():
        raise FileNotFoundError(f"Le fichier suppliers.csv est introuvable : {SUPPLIERS_FILE}")

    df = pd.read_csv(SUPPLIERS_FILE)

    if df.empty:
        raise ValueError("Le fichier suppliers.csv est vide.")

    n_bundles = min(n_bundles, len(df))
    selected_suppliers = df.iloc[:n_bundles]

    for _, supplier in selected_suppliers.iterrows():
        generate_bundle_for_supplier(supplier)

    print(f"{n_bundles} bundles cohérents ont été générés dans :")
    print(DOCUMENTS_DIR)


if __name__ == "__main__":
    main()