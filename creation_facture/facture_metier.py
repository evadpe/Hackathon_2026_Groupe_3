from PIL import Image, ImageDraw
import random
import os

def generer_document_chaussure(type_doc, nom_fichier, grain_de_folie=True):
    # 1. Création d'une image blanche format A4 (800x1100)
    img = Image.new('RGB', (800, 1100), color=(255, 255, 255))
    canvas = ImageDraw.Draw(img)
    
    # 2. Données fixes pour le TP
    vendeur_nom = "MANUFACTURE DU CUIR FRANCAIS"
    vendeur_siret = "12345678901234"
    client_nom = "STEP-AHEAD INDUSTRIES"
    
    # 3. Données variables (les articles de chaussure)
    articles = [
        {"sku": "CUIR-001", "desc": "Peaux de Veau", "couleur": "Noir", "unite": "m2", "qte": 20, "pu": 45.0},
        {"sku": "SEM-42-G", "desc": "Semelles Gomme", "couleur": "Brun", "unite": "paires", "qte": 50, "pu": 8.5}
    ]
    
    # 4. Dessin de l'en-tête (Obligatoire)
    canvas.text((320, 20), f"*** {type_doc.upper()} ***", fill=(0, 0, 0))
    canvas.text((50, 50), f"Vendeur : {vendeur_nom}", fill=(0, 0, 0))
    canvas.text((50, 70), f"SIRET : {vendeur_siret}", fill=(0, 0, 0))
    canvas.text((450, 120), f"Client : {client_nom}", fill=(0, 0, 0))
    
    # 5. Infos spécifiques au document
    prefixe = "DEV" if type_doc == "Devis" else "BC" if type_doc == "Bon de Commande" else "INV"
    num_doc = f"{prefixe}-2026-{random.randint(1000, 9999)}"
    canvas.text((50, 180), f"Numéro : {num_doc}", fill=(0, 0, 0))
    canvas.text((50, 200), f"Date : 17/03/2026", fill=(0, 0, 0))
    
    # 6. Tableau des produits (Spécificités Chaussure)
    y = 300
    header = "SKU | Désignation | Couleur | Qté | Unité | P.U HT | Total HT"
    canvas.text((50, y), header, fill=(0, 0, 0))
    canvas.line((50, y+15, 750, y+15), fill=(0, 0, 0))
    
    total_ht_global = 0
    y += 30
    for art in articles:
        total_ligne = art["qte"] * art["pu"]
        total_ht_global += total_ligne
        ligne = f"{art['sku']} | {art['desc']} | {art['couleur']} | {art['qte']} | {art['unite']} | {art['pu']} | {total_ligne}"
        canvas.text((50, y), ligne, fill=(0, 0, 0))
        y += 25
    
    # 7. Totaux financiers
    tva = total_ht_global * 0.20
    ttc = total_ht_global + tva
    canvas.text((500, y+50), f"Total HT : {total_ht_global:.2f} EUR", fill=(0, 0, 0))
    canvas.text((500, y+75), f"TVA (20%) : {tva:.2f} EUR", fill=(0, 0, 0))
    canvas.text((500, y+100), f"TOTAL TTC : {ttc:.2f} EUR", fill=(0, 0, 0))

    # 8. Simulation de "dégradation" (Légère rotation)
    if grain_de_folie:
        img = img.rotate(random.uniform(-2.0, 2.0), expand=True, fillcolor=(255, 255, 255))
    
    img.save(nom_fichier)
    print(f"Généré : {nom_fichier}")

# Création des dossiers et des fichiers de test
os.makedirs("test_documents", exist_ok=True)
generer_document_chaussure("Devis", "test_documents/devis_chaussure.jpg")
generer_document_chaussure("Bon de Commande", "test_documents/bc_chaussure.jpg")
generer_document_chaussure("Facture", "test_documents/facture_chaussure.jpg")