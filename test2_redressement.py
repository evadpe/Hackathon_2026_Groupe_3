import easyocr # lecture des textes dans les images
import re # regex
import json
import os # communication avec mon pc, gestion des dossiers 
import cv2 # deskewing (redresser l'image si inclinée)
import numpy as np # travail sur les pixels de l'image
import glob

# Ma fonction pour redresser l'image et l'enregistrer dans un dossier spécial
def deskew_and_save(input_path, output_path):
    image = cv2.imread(input_path)
    if image is None: return None
    
    # Prétraitement pour détecter l'angle
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_invert = cv2.bitwise_not(gray)
    points = np.column_stack(np.where(gray_invert > 0))
    
    # Calcul de l'angle
    angle = cv2.minAreaRect(points)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # Rotation
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated_image = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # Enregistrement de l'image redressée
    cv2.imwrite(output_path, rotated_image)
    return output_path

# Ma fonction principale pour extraire les données de la facture
def extract_data(image_path, ocr_reader):
    # Création du dossier pour les images redressées (Zone de contrôle)
    processed_folder = "processed_images"
    os.makedirs(processed_folder, exist_ok=True)
    
    # Préparation du chemin de l'image redressée
    base_name = os.path.basename(image_path).split('.')[0]
    straight_image_path = os.path.join(processed_folder, f"{base_name}_straight.jpg")

    # 1. Redressement et sauvegarde
    ready_image_path = deskew_and_save(image_path, straight_image_path)
    
    # 2. Analyse OCR
    ocr_results = ocr_reader.readtext(ready_image_path, detail=0)
    full_text = " ".join(ocr_results).replace('Q', '0').replace('u', ' ')
    
    # --- EXTRACTION REGEX ---
    # SIRET
    siret_match = re.search(r'\d{14}', full_text)
    siret_value = siret_match.group() if siret_match else "Pas trouvé"

    # DATE
    date_match = re.search(r'\d{2}[/.,*]\d{2}[/.,*]\d{4}', full_text)
    date_raw = date_match.group() if date_match else ""
    date_clean = date_raw.replace(',', '/').replace('*', '/') if date_raw else "Pas trouvée"

    # MONTANT TTC
    amount_match = re.search(r'(?:TOTAL|PAYER).*?(\d+[\s.,]?\d{0,3})', full_text, re.IGNORECASE)
    amount_temp = "0"
    if amount_match:
        candidate = amount_match.group(1).strip()
        if date_raw and candidate in date_raw:
            all_numbers = re.findall(r'\d+[\s.,]?\d{2,3}', full_text)
            amount_temp = all_numbers[-1] if all_numbers else "0"
        else:
            amount_temp = candidate

    # NETTOYAGE MONTANT
    digits_only = re.sub(r'[^\d]', '', amount_temp)
    if digits_only.endswith("000"):
        final_amount = digits_only[:-3] + ".00"
    elif len(digits_only) > 2:
        final_amount = digits_only[:-2] + "." + digits_only[-2:]
    else:
        final_amount = digits_only

    # Résultat final
    result = {
        "file_name": os.path.basename(image_path),
        "straight_image_path": straight_image_path, 
        "siret": siret_value,
        "date": date_clean,
        "total_ttc": float(final_amount) if final_amount.replace('.','').isdigit() else 0.0,
        "raw_text": full_text
    }
    return result

# --- EXECUTION DU SCRIPT ---
input_folder = "entree_factures"
output_folder = "resultats_json"

os.makedirs(output_folder, exist_ok=True)
os.makedirs(input_folder, exist_ok=True)

print("[*] Initialisation de l'IA (EasyOCR)...")
reader = easyocr.Reader(['fr'])

image_files = glob.glob(os.path.join(input_folder, "*.*"))

if not image_files:
    print("[!] Le dossier 'entree_factures' est vide !")
else:
    print(f"[*] {len(image_files)} facture(s) trouvée(s).")
    
    for photo in image_files:
        data_extracted = extract_data(photo, reader)
        
        json_filename = os.path.basename(photo).split('.')[0] + ".json"
        json_path = os.path.join(output_folder, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data_extracted, f, indent=4, ensure_ascii=False)
            
        print(f"[OK] {data_extracted['file_name']} traité | Total: {data_extracted['total_ttc']} €")

print(f"\n[*] Succès ! Les JSON sont dans '{output_folder}' et les images redressées dans 'processed_images'")