from faker import Faker
from PIL import Image, ImageDraw, ImageFont
import random

fake = Faker('fr_FR')

def creer_image_facture(nom_fichier):
    # 1. Créer une image blanche (format A4 environ : 800x1000)
    img = Image.new('RGB', (800, 1000), color=(255, 255, 255))
    canvas = ImageDraw.Draw(img)
    
    # 2. Préparer les données Faker
    entreprise = fake.company()
    siret = "".join([str(random.randint(0, 9)) for _ in range(14)])
    adresse = fake.address()
    date = fake.date_this_year().strftime("%d/%m/%Y")
    ttc = f"{random.randint(100, 5000)},00 €"
    
    # 3. Écrire sur l'image
    # Note : Si tu as une erreur de police, enlève l'argument font ou télécharge un fichier .ttf
    canvas.text((50, 50), f"FOURNISSEUR : {entreprise}", fill=(0, 0, 0))
    canvas.text((50, 70), f"SIRET : {siret}", fill=(0, 0, 0))
    canvas.text((50, 90), adresse, fill=(0, 0, 0))
    
    canvas.text((50, 200), f"FACTURE N° {random.randint(100, 999)}", fill=(0, 0, 0))
    canvas.text((50, 220), f"Date : {date}", fill=(0, 0, 0))
    
    canvas.text((50, 400), "-----------------------------------------", fill=(0, 0, 0))
    canvas.text((50, 430), f"TOTAL TTC À PAYER : {ttc}", fill=(0, 0, 0))
    canvas.text((50, 450), "-----------------------------------------", fill=(0, 0, 0))
    
    # Juste avant img.save(nom_fichier)
# On tourne l'image de 5 degrés (ce qui est beaucoup pour un OCR)
    img = img.rotate(5, expand=True, fillcolor=(255, 255, 255))
    img.save(nom_fichier)
    # 4. Sauvegarder l'image
    img.save(nom_fichier)
    print(f"Facture générée : {nom_fichier}")

# Tester la génération
creer_image_facture("ma_facture_fake2.jpg")