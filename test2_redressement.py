import easyocr
import re
import json
import os
import cv2
import numpy as np
import glob

# --- ÉTAPE 1 : REDRESSER L'IMAGE (Pour que le texte soit bien horizontal) ---
def deskew_and_save(input_path, output_path):
    image = cv2.imread(input_path) # On ouvre la photo
    if image is None: return None
    
    # On prépare l'image pour que l'ordi "voit" mieux les lignes
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) # Passage en gris
    gray_invert = cv2.bitwise_not(gray) # Inversion (texte blanc sur fond noir)
    
    # On calcule l'angle pour remettre l'image droite
    points = np.column_stack(np.where(gray_invert > 0))
    angle = cv2.minAreaRect(points)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    
    # On fait pivoter la photo
    (h, w) = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    rotated = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    cv2.imwrite(output_path, rotated) # On enregistre la version "propre"
    return output_path

# --- ÉTAPE 2 : EXTRAIRE TOUTES LES INFOS DE LA FACTURE ---
def extract_all_invoice_data(image_path, ocr_reader):
    # On range les images redressées dans un dossier à part
    processed_folder = "processed_images"
    os.makedirs(processed_folder, exist_ok=True)
    base_name = os.path.basename(image_path).split('.')[0]
    ready_path = os.path.join(processed_folder, f"{base_name}_clean.jpg")
    deskew_and_save(image_path, ready_path)

    # L'IA lit l'image et on transforme la liste de mots en une seule grande phrase
    results = ocr_reader.readtext(ready_path, detail=0)
    full_text = " ".join(results).replace('□', '').replace('|', '')

    # --- PARTIE 1 : LE VENDEUR (Celui qui envoie la facture) ---
    # On cherche le nom après le mot "VENDEUR"
    v_nom = re.search(r'VENDEUR\s*:\s*([^S]+)', full_text, re.I)
    v_siret = re.search(r'SIRET\s*:\s*(\d{14})', full_text)
    v_tva = re.search(r'TVA Intracom\s*:\s*([A-Z0-9]+)', full_text)
    # On prend tout ce qui est entre "Adresse :" et "TVA" pour l'adresse
    v_adr = re.search(r'Adresse\s*:\s*(.*?)(?=TVA)', full_text)

    # --- PARTIE 2 : LE CLIENT (Celui qui doit payer) ---
    c_nom = re.search(r'CLIENT\s*:\s*([^0-9,]+)', full_text)
    # On cherche une adresse qui finit par un code postal (5 chiffres)
    c_adr = re.search(r'CLIENT\s*:\s*.*?\d{5}.*?(?=[A-Z]{2,})', full_text)

    # --- PARTIE 3 : INFOS GÉNÉRALES ---
    f_num = re.search(r'INV[-\d]+', full_text) # Le numéro de facture
    f_date = re.search(r'Date.*?(\d{2}/\d{2}/\d{4})', full_text) # La date

    # --- PARTIE 4 : LE TABLEAU DES PRODUITS (Les lignes de la facture) ---
    lignes_produits = []
    # On cherche : [Nom du produit] [Quantité] [Prix HT] [Total HT]
    # C'est la partie la plus "magique" de la Regex !
    trouvailles = re.findall(r'([A-Za-z\s]+)\s+(\d+)\s+(\d+[\.,]?\d*)\s+(\d+[\.,]?\d*)', full_text)
    
    for t in trouvailles:
        lignes_produits.append({
            "designation": t[0].strip(),
            "quantite": int(t[1]),
            "prix_unitaire_ht": float(t[2].replace(',', '.')),
            "total_ligne_ht": float(t[3].replace(',', '.'))
        })

    # --- PARTIE 5 : LES TOTAUX FINAUX ---
    ht = re.search(r'Total HT\s*[:]*\s*(\d+[\.,]\d{2})', full_text, re.I)
    tva_infos = re.search(r'TVA \((\d+)%\)\s*[:]*\s*(\d+[\.,]\d{2})', full_text, re.I)
    ttc = re.search(r'TOTAL TTC\s*[:]*\s*(\d+[\.,]\d{2})', full_text, re.I)

    # --- ON ROULE TOUT ÇA DANS UN BEAU DICTIONNAIRE ---
    return {
        "vendeur": {
            "nom": v_nom.group(1).strip() if v_nom else "Inconnu",
            "siret": v_siret.group(1) if v_siret else "Inconnu",
            "adresse": v_adr.group(1).strip() if v_adr else "Inconnue",
            "tva_intracom": v_tva.group(1) if v_tva else "Inconnu"
        },
        "client": {
            "nom": c_nom.group(1).strip() if c_nom else "Inconnu",
            "adresse": c_adr.group(0).replace("CLIENT :", "").strip() if c_adr else "Inconnue"
        },
        "facture_infos": {
            "numero": f_num.group() if f_num else "Inconnu",
            "date": f_date.group(1) if f_date else "Inconnue"
        },
        "details_produits": lignes_produits,
        "montants_finaux": {
            "total_ht": float(ht.group(1).replace(',', '.')) if ht else 0.0,
            "taux_tva": f"{tva_infos.group(1)}%" if tva_infos else "20%",
            "montant_tva": float(tva_infos.group(2).replace(',', '.')) if tva_infos else 0.0,
            "total_ttc": float(ttc.group(1).replace(',', '.')) if ttc else 0.0
        }
    }

# --- ÉTAPE 3 : LANCER LE PROGRAMME SUR TOUTES LES IMAGES ---
print("[*] Lancement de l'IA EasyOCR...")
reader = easyocr.Reader(['fr']) # On lui dit de lire le français

dossier_images = "entree_factures"
dossier_json = "resultats_json"
os.makedirs(dossier_json, exist_ok=True)

# Pour chaque photo .jpg trouvée dans le dossier
for photo in glob.glob(os.path.join(dossier_images, "*.jpg")):
    # On fait l'extraction complète
    resultat = extract_all_invoice_data(photo, reader)
    
    # On enregistre au format JSON (propre et facile à lire)
    nom_fichier = os.path.basename(photo).split('.')[0] + ".json"
    chemin_final = os.path.join(dossier_json, nom_fichier)
    
    with open(chemin_final, 'w', encoding='utf-8') as f:
        json.dump(resultat, f, indent=4, ensure_ascii=False)
    
    print(f"[OK] Données enregistrées pour : {nom_fichier}")

print("\n[*] Travail terminé ! Tu peux aller voir tes fichiers dans 'resultats_json'.")