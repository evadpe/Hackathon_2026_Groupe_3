from faker import Faker
from PIL import Image, ImageDraw, ImageFont
import random
import os

fake = Faker('fr_FR')

def create_legal_invoice(filename, rotate=False):
    # Création du fond A4 (800x1100)
    img = Image.new('RGB', (800, 1100), color=(255, 255, 255))
    canvas = ImageDraw.Draw(img)
    
    # 1. DONNÉES MÉTIER (Mentions Obligatoires)
    vendor_name = fake.company().upper()
    vendor_siret = "".join([str(random.randint(0, 9)) for _ in range(14)])
    vendor_address = fake.address().replace('\n', ', ')
    client_name = fake.name()
    client_address = fake.address().replace('\n', ', ')
    
    inv_number = f"INV-{fake.year()}-{random.randint(1000, 9999)}"
    inv_date = fake.date_this_year().strftime("%d/%m/%Y")
    
    # Calculs financiers
    price_ht = random.randint(100, 2000)
    tva_rate = 0.20
    tva_amount = price_ht * tva_rate
    price_ttc = price_ht + tva_amount

    # 2. DESSIN SUR LA FACTURE
    # En-tête Vendeur
    canvas.text((50, 50), f"VENDEUR : {vendor_name}", fill=(0, 0, 0))
    canvas.text((50, 70), f"SIRET : {vendor_siret}", fill=(0, 0, 0))
    canvas.text((50, 90), f"Adresse : {vendor_address}", fill=(0, 0, 0))
    canvas.text((50, 110), f"TVA Intracom : FR{random.randint(10, 99)}{vendor_siret[:9]}", fill=(0, 0, 0))

    # Bloc Client
    canvas.text((450, 180), "CLIENT :", fill=(0, 0, 0))
    canvas.text((450, 200), client_name, fill=(0, 0, 0))
    canvas.text((450, 220), client_address, fill=(0, 0, 0))

    # Infos Facture
    canvas.text((50, 300), f"FACTURE N° : {inv_number}", fill=(0, 0, 0))
    canvas.text((50, 320), f"Date d'émission : {inv_date}", fill=(0, 0, 0))

    # Détail (Tableau simplifié)
    canvas.text((50, 400), "Désignation                     Qté    P.U. HT    Total HT", fill=(0, 0, 0))
    canvas.text((50, 415), "-"*85, fill=(0, 0, 0))
    canvas.text((50, 435), f"Prestation de service informatique  1      {price_ht}€       {price_ht}€", fill=(0, 0, 0))

    # Totaux
    canvas.text((500, 600), f"Total HT : {price_ht:.2f} €", fill=(0, 0, 0))
    canvas.text((500, 620), f"TVA (20%) : {tva_amount:.2f} €", fill=(0, 0, 0))
    canvas.text((500, 640), f"TOTAL TTC : {price_ttc:.2f} €", fill=(0, 0, 0))

    # Mentions Légales Pied de page
    canvas.text((50, 900), f"Conditions de paiement : Paiement à réception. Date limite : {inv_date}", fill=(0, 0, 0))
    canvas.text((50, 920), "Pénalités de retard : 3x taux légal | Indemnité forfaitaire de recouvrement : 40€", fill=(0, 0, 0))

    # 3. DÉGRADATION (Rotation)
    if rotate:
        img = img.rotate(random.randint(3, 7), expand=True, fillcolor=(255, 255, 255))

    img.save(filename)
    print(f"Facture générée : {filename}")

# Génération des tests
os.makedirs("entree_factures", exist_ok=True)
create_legal_invoice("entree_factures/facture_droite.jpg", rotate=False)
create_legal_invoice("entree_factures/facture_penchee.jpg", rotate=True)