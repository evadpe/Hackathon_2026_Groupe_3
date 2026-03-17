from pathlib import Path
from datetime import datetime
import random

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).resolve().parent.parent
SUPPLIERS_FILE = BASE_DIR / "data" / "raw" / "suppliers" / "suppliers.csv"
DOCUMENTS_DIR = BASE_DIR / "data" / "raw" / "documents"


def generate_purchase_order_number() -> str:
    year = datetime.now().year
    number = random.randint(1, 9999)
    return f"BC-{year}-{number:04d}"


def generate_purchase_order_data(supplier: pd.Series) -> dict:
    issue_date = datetime.now().date()

    quantity = random.randint(50, 500)
    unit = random.choice(["m²", "paire", "unité", "mètre"])
    expected_unit_price = round(random.uniform(2.0, 25.0), 2)
    expected_amount_ht = round(quantity * expected_unit_price, 2)

    return {
        "purchase_order_number": generate_purchase_order_number(),
        "issue_date": issue_date.strftime("%d/%m/%Y"),
        "company_name": supplier["company_name"],
        "address": supplier["address"],
        "postal_code": supplier["postal_code"],
        "city": supplier["city"],
        "siren": supplier["siren"],
        "siret": supplier["siret"],
        "product_name": supplier["material_specialty"],
        "quantity": quantity,
        "unit": unit,
        "expected_unit_price": expected_unit_price,
        "expected_amount_ht": expected_amount_ht,
    }


def create_purchase_order_pdf(order_data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "BON DE COMMANDE")

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 90, f"Numéro : {order_data['purchase_order_number']}")
    c.drawString(50, height - 110, f"Date : {order_data['issue_date']}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 150, "Fournisseur")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 170, order_data["company_name"])
    c.drawString(50, height - 190, order_data["address"])
    c.drawString(50, height - 210, f"{order_data['postal_code']} {order_data['city']}")
    c.drawString(50, height - 230, f"SIREN : {order_data['siren']}")
    c.drawString(50, height - 250, f"SIRET : {order_data['siret']}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 300, "Commande")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 330, "Produit")
    c.drawString(260, height - 330, "Qté")
    c.drawString(310, height - 330, "Unité")
    c.drawString(380, height - 330, "P.U. prévu")
    c.drawString(460, height - 330, "Total HT")

    c.line(50, height - 335, 540, height - 335)

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 360, str(order_data["product_name"])[:30])
    c.drawString(260, height - 360, str(order_data["quantity"]))
    c.drawString(310, height - 360, str(order_data["unit"]))
    c.drawString(380, height - 360, f"{order_data['expected_unit_price']:.2f} EUR")
    c.drawString(460, height - 360, f"{order_data['expected_amount_ht']:.2f} EUR")

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 50, "")

    c.save()


def main() -> None:
    if not SUPPLIERS_FILE.exists():
        raise FileNotFoundError(f"Le fichier suppliers.csv est introuvable : {SUPPLIERS_FILE}")

    df = pd.read_csv(SUPPLIERS_FILE)

    if df.empty:
        raise ValueError("Le fichier suppliers.csv est vide.")

    supplier = df.iloc[0]
    supplier_id = supplier["supplier_id"]

    order_data = generate_purchase_order_data(supplier)

    output_path = DOCUMENTS_DIR / supplier_id / "purchase_order.pdf"
    create_purchase_order_pdf(order_data, output_path)

    print("Bon de commande généré avec succès :")
    print(output_path)


if __name__ == "__main__":
    main()