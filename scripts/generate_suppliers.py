from pathlib import Path
import random
import pandas as pd
from faker import Faker

fake = Faker("fr_FR")

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "suppliers"
OUTPUT_FILE = OUTPUT_DIR / "suppliers.csv"


def generate_siren() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(9))


def generate_siret(siren: str) -> str:
    nic = "".join(str(random.randint(0, 9)) for _ in range(5))
    return siren + nic


def generate_vat_number(siren: str) -> str:
    key = str(random.randint(10, 99))
    return f"FR{key}{siren}"


def generate_iban() -> str:
    bank_code = "".join(str(random.randint(0, 9)) for _ in range(5))
    branch_code = "".join(str(random.randint(0, 9)) for _ in range(5))
    account_number = "".join(str(random.randint(0, 9)) for _ in range(11))
    rib_key = "".join(str(random.randint(0, 9)) for _ in range(2))
    return f"FR76 {bank_code} {branch_code} {account_number} {rib_key}"


def generate_bic() -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    bank = "".join(random.choice(letters) for _ in range(4))
    country = "FR"
    location = "".join(random.choice(letters + "0123456789") for _ in range(2))
    branch = "".join(random.choice(letters + "0123456789") for _ in range(3))
    return f"{bank}{country}{location}{branch}"


def generate_supplier(index: int) -> dict:
    siren = generate_siren()
    siret = generate_siret(siren)

    supplier_categories = [
        "Fournisseur de cuir",
        "Fournisseur de textile",
        "Fournisseur de semelles",
        "Fournisseur de talons",
        "Fournisseur de lacets",
        "Fournisseur d'œillets",
        "Fournisseur de colle",
        "Fournisseur de fil de couture",
    ]

    material_specialties = [
        "Cuir noir pleine fleur",
        "Cuir marron nubuck",
        "Textile technique respirant",
        "Semelles gomme",
        "Talons bois",
        "Lacets coton noir",
        "Œillets métalliques",
        "Colle industrielle cuir/caoutchouc",
        "Fil de couture renforcé",
    ]

    return {
        "supplier_id": f"supplier_{index:03d}",
        "company_name": fake.company(),
        "legal_form": random.choice(["SAS", "SARL", "EURL", "SA", "SASU"]),
        "supplier_category": random.choice(supplier_categories),
        "material_specialty": random.choice(material_specialties),
        "address": fake.street_address(),
        "postal_code": fake.postcode(),
        "city": fake.city(),
        "country": "France",
        "siren": siren,
        "siret": siret,
        "vat_number": generate_vat_number(siren),
        "iban": generate_iban(),
        "bic": generate_bic(),
        "bank_name": random.choice(
            [
                "BNP Paribas",
                "Crédit Agricole",
                "Société Générale",
                "La Banque Postale",
                "Crédit Mutuel",
            ]
        ),
    }

def main(n_suppliers: int = 30) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    suppliers = [generate_supplier(i) for i in range(1, n_suppliers + 1)]
    df = pd.DataFrame(suppliers)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"{len(df)} fournisseurs générés dans : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()