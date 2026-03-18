from pathlib import Path
from datetime import datetime
import random

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).resolve().parent.parent
SUPPLIERS_FILE = BASE_DIR / "data" / "raw" / "suppliers" / "suppliers.csv"
DOCUMENTS_DIR = BASE_DIR / "data" / "raw" / "documents"

# Notre entreprise = l'émetteur du bon de commande
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


def generate_purchase_order_data(supplier: pd.Series) -> dict:
    issue_date = datetime.now().date()

    quantity = random.randint(50, 500)
    unit = random.choice(["m²", "paire", "unité", "mètre"])
    expected_unit_price = round(random.uniform(2.0, 25.0), 2)

    amount_ht = round(quantity * expected_unit_price, 2)
    amount_tva = round(amount_ht * 0.20, 2)
    amount_ttc = round(amount_ht + amount_tva, 2)

    return {
        "purchase_order_number": generate_purchase_order_number(),
        "issue_date": issue_date.strftime("%d/%m/%Y"),

        # Acheteur = nous
        "buyer_company_name": BUYER_COMPANY["company_name"],
        "buyer_address": BUYER_COMPANY["address"],
        "buyer_postal_code": BUYER_COMPANY["postal_code"],
        "buyer_city": BUYER_COMPANY["city"],
        "buyer_country": BUYER_COMPANY["country"],
        "buyer_siren": BUYER_COMPANY["siren"],
        "buyer_siret": BUYER_COMPANY["siret"],
        "buyer_vat_number": BUYER_COMPANY["vat_number"],

        # Fournisseur
        "supplier_company_name": supplier["company_name"],
        "supplier_address": supplier["address"],
        "supplier_postal_code": supplier["postal_code"],
        "supplier_city": supplier["city"],
        "supplier_country": supplier["country"],
        "supplier_siren": supplier["siren"],
        "supplier_siret": supplier["siret"],
        "supplier_vat_number": supplier["vat_number"],

        # Produit
        "product_name": supplier["material_specialty"],
        "quantity": quantity,
        "unit": unit,
        "expected_unit_price": expected_unit_price,
        "amount_ht": amount_ht,
        "amount_tva": amount_tva,
        "amount_ttc": amount_ttc,
        "currency": "EUR",
    }


def create_purchase_order_pdf(order_data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=A4)
    _, height = A4

    # Titre
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "BON DE COMMANDE")

    # Numéro et date
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 90, f"Numéro : {order_data['purchase_order_number']}")
    c.drawString(50, height - 110, f"Date : {order_data['issue_date']}")

    # Acheteur / Émetteur
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 160, "Acheteur / Émetteur")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 180, order_data["buyer_company_name"])
    c.drawString(50, height - 198, order_data["buyer_address"])
    c.drawString(50, height - 216, f"{order_data['buyer_postal_code']} {order_data['buyer_city']}")
    c.drawString(50, height - 234, f"SIREN : {order_data['buyer_siren']}")
    c.drawString(50, height - 252, f"SIRET : {order_data['buyer_siret']}")
    c.drawString(50, height - 270, f"TVA : {order_data['buyer_vat_number']}")

    # Fournisseur
    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 160, "Fournisseur")
    c.setFont("Helvetica", 10)
    c.drawString(320, height - 180, order_data["supplier_company_name"])
    c.drawString(320, height - 198, order_data["supplier_address"])
    c.drawString(320, height - 216, f"{order_data['supplier_postal_code']} {order_data['supplier_city']}")
    c.drawString(320, height - 234, f"SIREN : {order_data['supplier_siren']}")
    c.drawString(320, height - 252, f"SIRET : {order_data['supplier_siret']}")
    c.drawString(320, height - 270, f"TVA : {order_data['supplier_vat_number']}")

    # Bloc commande
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
    c.drawString(380, height - 380, f"{order_data['expected_unit_price']:.2f} EUR")
    c.drawString(470, height - 380, f"{order_data['amount_ht']:.2f} EUR")

    # Totaux
    c.line(300, height - 430, 545, height - 430)

    c.setFont("Helvetica", 11)
    c.drawString(320, height - 455, f"Total HT : {order_data['amount_ht']:.2f} EUR")
    c.drawString(320, height - 475, f"TVA 20% : {order_data['amount_tva']:.2f} EUR")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 500, f"Total TTC : {order_data['amount_ttc']:.2f} EUR")

    # Pied
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 70, "")
    c.drawString(50, 50, "")

    c.save()


def main() -> None:
    if not SUPPLIERS_FILE.exists():
        raise FileNotFoundError(f"Le fichier suppliers.csv est introuvable : {SUPPLIERS_FILE}")

    df = pd.read_csv(SUPPLIERS_FILE)

    if df.empty:
        raise ValueError("Le fichier suppliers.csv est vide.")

    # Générer pour chaque fournisseur
    for _, supplier in df.iterrows():
        order_data = generate_purchase_order_data(supplier)

        # Créer le bon de commande et le sauvegarder dans un dossier unique
        output_path = DOCUMENTS_DIR / str(supplier["supplier_id"]) / "purchase_order.pdf"
        create_purchase_order_pdf(order_data, output_path)

        print(f"Bon de commande généré pour {supplier['company_name']} :")
        print(output_path)


if __name__ == "__main__":
    main()