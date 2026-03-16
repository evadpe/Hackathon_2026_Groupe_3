import easyocr
import re
import json
import os
import cv2
import numpy as np
import glob

# --- ÉTAPE 1 : REDRESSEMENT DE L'IMAGE ---
def deskew_and_save(input_path, output_path):
    image = cv2.imread(input_path)
    if image is None: return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) 
    gray_invert = cv2.bitwise_not(gray)
    points = np.column_stack(np.where(gray_invert > 0))
    angle = cv2.minAreaRect(points)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    (h, w) = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    rotated = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    cv2.imwrite(output_path, rotated)
    return output_path

# --- ÉTAPE 2 : EXTRACTION AMÉLIORÉE ---
def extract_all_invoice_data(image_path, ocr_reader):
    processed_folder = "processed_images"
    os.makedirs(processed_folder, exist_ok=True)
    base_name = os.path.basename(image_path).split('.')[0]
    ready_path = os.path.join(processed_folder, f"{base_name}_clean.jpg")
    deskew_and_save(image_path, ready_path)

    # Lecture avec coordonnées pour le zonage
    results = ocr_reader.readtext(ready_path, detail=1)
    img = cv2.imread(ready_path)
    h_img, w_img = img.shape[:2]

    vendeur_bloc = []
    client_bloc = []
    tous_les_mots = []

    for (box, text, prob) in results:
        x_center = (box[0][0] + box[1][0]) / 2
        y_center = (box[0][1] + box[2][1]) / 2
        
        # Nettoyage des caractères spéciaux qui bloquent les Regex
        clean_word = text.replace('□', '').replace('|', '').replace(':', '').strip()
        tous_les_mots.append(clean_word)

        # ZONE VENDEUR (Haut Gauche)
        if y_center < (h_img * 0.25) and x_center < (w_img * 0.5):
            if not any(key in clean_word.upper() for key in ["VENDEUR", "SIRET", "ADRESSE", "TVA"]):
                vendeur_bloc.append(clean_word)
        
        # ZONE CLIENT (Milieu-Haut Droite)
        if (h_img * 0.15) < y_center < (h_img * 0.40) and x_center > (w_img * 0.5):
            if "CLIENT" not in clean_word.upper():
                client_bloc.append(clean_word)

    full_text = " ".join(tous_les_mots)

    # --- EXTRACTIONS PAR REGEX ---
    siret = re.search(r'\d{14}', full_text)
    tva_intra = re.search(r'FR\d{11}', full_text)
    inv_num = re.search(r'INV[-\d]+', full_text)
    date_f = re.search(r'(\d{2}/\d{2}/\d{4})', full_text)

    # Extraction des produits
    items = []
    # Motif: Désignation + Qté + PU + Total HT
    lignes = re.findall(r'([A-Za-z\s]+)\s+(\d+)\s+(\d+[\.,]?\d*)\s+(\d+[\.,]?\d*)', full_text)
    for l in lignes:
        nom_prod = l[0].strip()
        if not any(x in nom_prod.upper() for x in ["TOTAL", "TVA", "FACTURE"]):
            items.append({
                "designation": nom_prod,
                "quantite": int(l[1]),
                "prix_unitaire_ht": float(l[2].replace(',', '.')),
                "total_ligne_ht": float(l[3].replace(',', '.'))
            })

    # Totaux
    ht_val = re.search(r'Total HT\s*(\d+[\.,]\d{2})', full_text, re.I)
    tva_taux = re.search(r'TVA\s*\((\d+)%\)', full_text)
    tva_mnt = re.search(r'TVA\s*\(.*?\)\s*(\d+[\.,]\d{2})', full_text, re.I)
    ttc_val = re.search(r'TOTAL TTC\s*(\d+[\.,]\d{2})', full_text, re.I)

    return {
        "vendeur": {
            "nom": vendeur_bloc[0] if vendeur_bloc else "Inconnu",
            "adresse": ", ".join(vendeur_bloc[1:]) if len(vendeur_bloc) > 1 else "Inconnue",
            "siret": siret.group() if siret else "Inconnu",
            "tva_intra": tva_intra.group() if tva_intra else "Inconnu"
        },
        "client": {
            "nom": client_bloc[0] if client_bloc else "Inconnu",
            "adresse": ", ".join(client_bloc[1:]) if len(client_bloc) > 1 else "Inconnue"
        },
        "facture": {
            "numero": inv_num.group() if inv_num else "Inconnu",
            "date": date_f.group(1) if date_f else "Inconnue"
        },
        "produits": items,
        "totaux": {
            "ht": float(ht_val.group(1).replace(',', '.')) if ht_val else 0.0,
            "taux_tva": f"{tva_taux.group(1)}%" if tva_taux else "20%",
            "montant_tva": float(tva_mnt.group(1).replace(',', '.')) if tva_mnt else 0.0,
            "ttc": float(ttc_val.group(1).replace(',', '.')) if ttc_val else 0.0
        }
    }

# --- ÉTAPE 3 : TRAITEMENT ---
reader = easyocr.Reader(['fr'])
for photo in glob.glob("entree_factures/*.jpg"):
    data = extract_all_invoice_data(photo, reader)
    nom_json = os.path.basename(photo).split('.')[0] + ".json"
    with open(f"resultats_json/{nom_json}", 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Extraction réussie : {nom_json}")