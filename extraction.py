import easyocr
import cv2
import json
import re
import os
import glob
from pdf2image import convert_from_path

# --- CONFIGURATION ---
INPUT_FOLDER  = "test_documents"   # dossier contenant les PDFs/images à analyser
OUTPUT_FOLDER = "resultats_json"   # dossier où on sauvegarde les JSONs extraits
POPPLER_PATH  = r"C:\Users\ilham\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"  # chemin Poppler sur Windows (à adapter)

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# EasyOCR : le moteur qui lit le texte dans les images (modèle français chargé une seule fois)
print("Initialisation d'EasyOCR...")
ocr_reader = easyocr.Reader(['fr'])


# ================================================================== #
#  POURQUOI CETTE APPROCHE ?
#
#  Les documents ont deux colonnes visuelles (gauche=fournisseur,
#  droite=client) MAIS les labels "Fournisseur" et "Client" sont
#  à la MÊME hauteur Y. Trier uniquement par Y et chercher les ancres
#  dans l'ordre ne fonctionne pas : EasyOCR peut retourner "Client"
#  avant "Fournisseur" → les blocs s'inversent.
#
#  Solution retenue :
#  1. Séparer les tokens en deux colonnes selon x_rel (< ou >= 0.45)
#  2. Reconstruire des lignes physiques dans chaque colonne
#     en regroupant les tokens proches en Y
#  3. Chercher les ancres textuelles ("Fournisseur", "Client")
#     DANS LEUR COLONNE RESPECTIVE — pas dans une liste mélangée
# ================================================================== #

# Seuil horizontal séparant les deux colonnes (en ratio de la largeur)
COL_SPLIT = 0.45

# Fraction de la hauteur image utilisée comme tolérance de regroupement
# de tokens sur la même ligne physique.
# 1.5% est assez grand pour couvrir les décalages EasyOCR entre tokens
# gauche et droite d'une même ligne (±10-15px sur images haute résolution)
# mais assez petit pour ne jamais fusionner deux lignes distinctes
# (espacées d'au moins 30pt ≈ 60px à 150dpi).
Y_TOLERANCE_FACTOR = 0.015


def reconstruct_lines(ocr_results, page_width, page_height):
    """
    EasyOCR retourne des morceaux de texte éparpillés sur la page.
    Cette fonction les regroupe en lignes lisibles, séparées en colonne gauche / droite / complète.
    """
    # Tolérance adaptée à la résolution réelle (pdf2image → 150-300dpi)
    y_tol = max(8, int(page_height * Y_TOLERANCE_FACTOR))

    left_buckets  = {}
    right_buckets = {}
    all_buckets   = {}

    for (box, text, prob) in ocr_results:
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        cx = sum(xs) / 4
        cy = sum(ys) / 4

        x_rel    = cx / page_width
        y_bucket = round(cy / y_tol) * y_tol

        entry = (cx, text)

        if x_rel < COL_SPLIT:
            left_buckets.setdefault(y_bucket, []).append(entry)
        else:
            right_buckets.setdefault(y_bucket, []).append(entry)

        all_buckets.setdefault(y_bucket, []).append(entry)

    def _assemble(buckets):
        lines = []
        for y_bucket in sorted(buckets.keys()):
            tokens = sorted(buckets[y_bucket], key=lambda t: t[0])
            line_text = " ".join(t[1] for t in tokens)
            y_rel = y_bucket / page_height
            lines.append((y_rel, line_text))
        return lines

    return {
        "left":  _assemble(left_buckets),
        "right": _assemble(right_buckets),
        "full":  _assemble(all_buckets),
    }


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def _clean_float(s):
    return float(s.replace(',', '.'))

_END_OF_ADDR = re.compile(
    # SIREN/SIRET/TVA intentionnellement exclus :
    # ils font partie du bloc fournisseur et doivent être collectés.
    # 'Commande' : label de section dans les bons de commande.
    # 'Unité'    : en-tête du tableau produits (colonne droite du BC inversé).
    # 'Détail'   : "Détail de la commande" dans certains BC.
    r'^(Produit|Article|D[eé]signation|Qté|Qte|Total|Commande|Unit[eé]|D[eé]tail)',
    re.I
)
_ID_LINE = re.compile(r'(SIREN|SIRET|TVA)', re.I)


def _extract_section_from_col(col_lines, anchor_re):
    """
    Dans une liste de lignes (y_rel, texte) triées par Y,
    repère le label ancre (ex. "Fournisseur") et collecte
    les lignes qui suivent jusqu'à la fin du bloc.
    """
    in_section = False
    section = []
    for y_rel, text in col_lines:
        first_word = text.strip().split()[0] if text.strip() else ""
        if anchor_re.match(first_word):
            in_section = True
            continue
        if in_section:
            if _END_OF_ADDR.match(first_word):
                break
            section.append(text.strip())
    return section


# ------------------------------------------------------------------ #
#  Parsing du bloc fournisseur
# ------------------------------------------------------------------ #

_VENDOR_ANCHOR = re.compile(r'^(Fournisseur|Vendeur|Emetteur|[EÉ]metteur)$', re.I)

# Ancre spéciale pour les bons de commande émis par StepAhead :
# "Acheteur" ou "Émetteur" apparaît dans la colonne gauche
_BUYER_ANCHOR = re.compile(r'^(Acheteur|[EÉ]metteur)$', re.I)


def detect_layout(left_lines, right_lines):
    """
    Détecte si le document est une facture/devis classique (fournisseur à gauche)
    ou un bon de commande inversé (notre société à gauche, fournisseur à droite).
    """
    left_first_words  = {t.strip().split()[0].upper() for _, t in left_lines  if t.strip()}
    right_first_words = {t.strip().split()[0].upper() for _, t in right_lines if t.strip()}

    has_buyer_left   = any(_BUYER_ANCHOR.match(w) for w in left_first_words)
    has_vendor_right = any(w in ("FOURNISSEUR", "VENDEUR") for w in right_first_words)
    has_vendor_left  = any(w in ("FOURNISSEUR", "VENDEUR") for w in left_first_words)

    if has_buyer_left and has_vendor_right and not has_vendor_left:
        return "bc_inv"
    return "normal"

def parse_vendor(col_lines):
    vendor = {
        "name":  "Inconnu", "address": "Inconnu",
        "siren": "Inconnu", "siret":   "Inconnu", "tva": "Inconnu"
    }

    section = _extract_section_from_col(col_lines, _VENDOR_ANCHOR)
    if not section:
        return vendor

    full_text = "\n".join(section)

    # Lignes civiles : on exclut
    #   - les lignes contenant un label SIREN/SIRET/TVA  (ex. "SIREN : 779218330")
    #   - les lignes qui SONT une valeur d'identifiant sans label
    #     (EasyOCR peut séparer "TVA" et "FR89779218330" en deux tokens distincts
    #      → "FR89779218330" seul passerait le filtre _ID_LINE sinon)
    _ID_VALUE = re.compile(r'^(FR\d{11}|\d{9}|\d{14})$')
    civil_lines = [
        l for l in section
        if not _ID_LINE.search(l) and not _ID_VALUE.match(l.strip())
    ]

    if civil_lines:
        vendor["name"] = civil_lines[0]

    addr_parts = [l for l in civil_lines[1:4] if l]
    if addr_parts:
        vendor["address"] = ", ".join(addr_parts)

    # Identifiants légaux
    m = re.search(r'SIREN\s*[:\s]*(\d{7,9})\b',  full_text, re.I)
    if m: vendor["siren"] = m.group(1)

    m = re.search(r'SIRET\s*[:\s]*(\d{9,14})\b', full_text, re.I)
    if m: vendor["siret"] = m.group(1)

    m = re.search(r'(?:N[°o]\.?\s*)?TVA\s*[:\s]*(FR\s?\d{11})', full_text, re.I)
    if m: vendor["tva"] = m.group(1).replace(" ", "")

    # Fallback SIRET depuis SIREN
    if vendor["siret"] == "Inconnu" and vendor["siren"] != "Inconnu":
        siren = vendor["siren"]
        m = re.search(rf'({re.escape(siren)}\d{{1,5}})', full_text)
        if m: vendor["siret"] = m.group(1)

    return vendor


# ------------------------------------------------------------------ #
#  Parsing du bloc client
# ------------------------------------------------------------------ #

_CUSTOMER_ANCHOR = re.compile(r'^(Client|Destinataire)$', re.I)
# Dans le layout bc_inv, le "client" au sens métier est l'Acheteur/Émetteur (gauche)
_BUYER_CUSTOMER_ANCHOR = re.compile(r'^(Acheteur|[EÉ]metteur)$', re.I)

# Tokens caractéristiques des colonnes tableau qui débordent à droite
_TABLE_NOISE = re.compile(
    r'(Unité|Qté|P\.U\.|EUR|\d+[\.,]\d{2}|Total|HT\b|TTC)',
    re.I
)

def parse_customer(col_lines):
    customer = {"name": "Inconnu", "address": "Inconnu", "is_valid": False}

    section = _extract_section_from_col(col_lines, _CUSTOMER_ANCHOR)
    if not section:
        return customer

    # Retirer les lignes parasites du tableau produits
    clean = [l for l in section if not _TABLE_NOISE.search(l)]

    if clean:
        customer["name"] = clean[0]
    if len(clean) > 1:
        customer["address"] = ", ".join(clean[1:3])

    customer["is_valid"] = "STEPAHEAD" in customer["name"].upper()
    return customer


# ------------------------------------------------------------------ #
#  Parsing des lignes articles
# ------------------------------------------------------------------ #

# Regex principal : description | qté | unité | PU HT | [total HT optionnel]
# Le total_ht est rendu OPTIONNEL car en production EasyOCR peut placer
# la quantité (ex. "143") juste sous le seuil COL_SPLIT et le total
# (ex. "1165.45 EUR") dans la colonne droite. Si leurs buckets Y diffèrent
# légèrement, ils se retrouvent sur deux lignes séparées → total manquant.
# Dans ce cas on le calcule par qty * pu_ht.
_ITEM_RX = re.compile(
    r'(.+?)\s+'
    r'(\d+)\s+'
    r'(m[²2?]|m[eè.][tT]?res?|m\.|paires?|unit[eé]s?|pcs?|kg|h(?:eure)?s?)\s+'
    r'(\d+[\.,]\d{2})\s*(?:EUR|€)?'
    r'(?:\s+(\d+[\.,]\d{2}))?',   # total_ht optionnel
    re.I
)

def parse_items(full_lines, items_start_y):
    """
    Extrait les lignes de produits du tableau (description, quantité, prix unitaire, total).
    """
    line_items = []
    _FINANCIAL_RE = re.compile(r'Total\s*(HT|TTC)|TVA|À\s*PAYER', re.I)

    for y_rel, text in full_lines:
        if y_rel < items_start_y:   # < strict : on ne skippe pas les lignes au même niveau
            continue
        if _FINANCIAL_RE.search(text):
            continue
        m = _ITEM_RX.search(text)
        if not m:
            continue
        desc = m.group(1).strip()
        if any(kw in desc.upper() for kw in ("TOTAL", "SOUS-TOTAL", "REMISE")):
            continue
        qty   = int(m.group(2))
        pu_ht = _clean_float(m.group(4))
        # total_ht : groupe 5 optionnel — calculé si absent
        total_ht = _clean_float(m.group(5)) if m.group(5) else round(qty * pu_ht, 2)
        line_items.append({
            "description": desc,
            "qty":         qty,
            "unit":        m.group(3),
            "pu_ht":       pu_ht,
            "total_ht":    total_ht,
        })
    return line_items


# ------------------------------------------------------------------ #
#  Parsing des montants financiers
# ------------------------------------------------------------------ #

def parse_financials(right_lines, full_text_fallback):
    fin = {"total_ht": 0.0, "tva_rate": "0%", "tva_amount": 0.0, "total_ttc": 0.0}

    right_text = "\n".join(t for _, t in right_lines)
    text = right_text if right_text.strip() else full_text_fallback

    m = re.search(r'(?:Sous[- ]total|Total)\s*HT\s*[:\s]*(\d+[\.,]\d{2})', text, re.I)
    if m: fin["total_ht"] = _clean_float(m.group(1))

    m = re.search(r'TVA\s*(\d+\s*%)\s*[:\s]*(\d+[\.,]\d{2})', text, re.I)
    if m:
        fin["tva_rate"]   = m.group(1).replace(" ", "")
        fin["tva_amount"] = _clean_float(m.group(2))

    m = re.search(r'Total\s*(?:TTC|À\s*PAYER|NET)\s*[:\s]*(\d+[\.,]\d{2})', text, re.I)
    if m: fin["total_ttc"] = _clean_float(m.group(1))

    return fin


# ================================================================== #
#  Fonction principale d'extraction
# ================================================================== #

def process_document_extraction(image_path):
    """
    Fonction principale : prend une image de document et retourne un JSON structuré
    avec le fournisseur, le client, les articles et les montants.
    """
    raw_img = cv2.imread(image_path)
    if raw_img is None:
        return None

    height, width, _ = raw_img.shape

    # Lance EasyOCR sur l'image pour obtenir tous les blocs de texte détectés
    results = ocr_reader.readtext(raw_img, detail=1)

    # 1. Regroupe les blocs de texte en lignes lisibles par colonne
    lines       = reconstruct_lines(results, width, height)
    left_lines  = lines["left"]
    right_lines = lines["right"]
    full_lines  = lines["full"]
    full_text   = "\n".join(t for _, t in full_lines)

    # 2. Détecte si c'est un document normal ou un BC inversé, pour lire les bons blocs
    layout = detect_layout(left_lines, right_lines)

    if layout == "bc_inv":
        # Fournisseur (destinataire du BC) est dans la colonne DROITE
        vendor_lines   = right_lines
        # L'acheteur/émetteur (notre société) est dans la colonne GAUCHE
        # On réutilise parse_customer avec l'ancre Acheteur/Émetteur
        customer_col   = left_lines
        customer_anchor = _BUYER_CUSTOMER_ANCHOR
    else:
        vendor_lines    = left_lines
        customer_col    = right_lines
        customer_anchor = _CUSTOMER_ANCHOR

    # 3. Cherche à quelle hauteur commence le tableau de produits
    items_start_y = 1.0
    for y_rel, text in left_lines:
        if re.match(r'^Produit', text.strip(), re.I):
            items_start_y = y_rel
            break
    # Fallback : si non trouvé dans left_lines (layout inhabituel), cherche full_lines
    if items_start_y == 1.0:
        for y_rel, text in full_lines:
            if re.match(r'^Produit', text.strip(), re.I):
                items_start_y = y_rel
                break

    # 4. Assemble toutes les données extraites dans un dict structuré
    def _parse_customer_with_anchor(col_lines, anchor_re):
        customer = {"name": "Inconnu", "address": "Inconnu", "is_valid": False}
        section = _extract_section_from_col(col_lines, anchor_re)
        if not section:
            return customer
        clean = [l for l in section if not _TABLE_NOISE.search(l)]
        if clean:
            customer["name"] = clean[0]
        if len(clean) > 1:
            customer["address"] = ", ".join(clean[1:3])
        customer["is_valid"] = "STEPAHEAD" in customer["name"].upper()
        return customer

    line_items = parse_items(full_lines, items_start_y)
    financials = parse_financials(right_lines, full_text)

    # Si l'OCR n'a pas trouvé le total HT, on le recalcule depuis les lignes articles
    if financials["total_ht"] == 0.0 and line_items:
        financials["total_ht"] = round(sum(item["total_ht"] for item in line_items), 2)

    # Si le TTC est absent, on le recalcule depuis le HT + TVA
    if financials["total_ttc"] == 0.0 and financials["total_ht"] > 0:
        financials["total_ttc"] = round(
            financials["total_ht"] + financials["tva_amount"], 2
        )

    data = {
        "metadata":   {"type": "Inconnu", "file": os.path.basename(image_path)},
        "vendor":     parse_vendor(vendor_lines),
        "customer":   _parse_customer_with_anchor(customer_col, customer_anchor),
        "doc_info":   {"number": "Inconnu", "date": "Inconnue", "due_date": "Inconnue"},
        "line_items": line_items,
        "financials": financials,
    }

    # 5. Détecte le type de document (Facture / Devis / Bon de Commande) depuis l'en-tête
    header_text = " ".join(t for _, t in left_lines[:6]).upper()
    if   "FACTURE"  in header_text: data["metadata"]["type"] = "Facture"
    elif "DEVIS"    in header_text: data["metadata"]["type"] = "Devis"
    elif "COMMANDE" in header_text: data["metadata"]["type"] = "Bon de Commande"

    # 6. Extrait le numéro de document (BC-2024-0001, FAC-..., etc.)
    for pattern in [
        r'(BC-\d{4}-\d{4})',
        r'(DEV-\d{4}-\d{4})',
        r'(FAC-\d{4}-\d{4})',
        r'Num[ée]ro(?:\s+de\s+\w+)?\s*[:\s]+([A-Z0-9\-]+)',
    ]:
        m = re.search(pattern, full_text, re.I)
        if m:
            data["doc_info"]["number"] = m.group(1)
            break

    # 7. Extrait la date d'émission et la date d'échéance
    m_emit = re.search(
        r"Date\s+d'[eé]mission\s*[:\s]+(\d{2}/\d{2}/\d{4})", full_text, re.I
    )
    if not m_emit:
        # "Date : 17/03/2026" (bon de commande)
        m_emit = re.search(r'Date\s*:\s*(\d{2}/\d{2}/\d{4})', full_text, re.I)

    m_ech = re.search(
        r"Date\s+d'[eé]ch[eé]ance\s*[:\s]+(\d{2}/\d{2}/\d{4})", full_text, re.I
    )

    all_dates = re.findall(r'(\d{2}/\d{2}/\d{4})', full_text)

    data["doc_info"]["date"] = (
        m_emit.group(1) if m_emit else (all_dates[0] if all_dates else "Inconnue")
    )
    data["doc_info"]["due_date"] = (
        m_ech.group(1) if m_ech else (all_dates[1] if len(all_dates) >= 2 else "Inconnue")
    )

    return data


# ================================================================== #
#  Point d'entrée
# ================================================================== #

def main():
    # Recherche récursive de tous les fichiers dans INPUT_FOLDER et ses sous-dossiers.
    # glob.glob(...) sans ** ne remonte pas les sous-dossiers → on utilise os.walk.
    extensions = ('.pdf', '.jpg', '.jpeg', '.png')
    files = []
    for root, dirs, filenames in os.walk(INPUT_FOLDER):
        # Trier pour un affichage cohérent
        dirs.sort()
        for filename in sorted(filenames):
            if filename.lower().endswith(extensions):
                files.append(os.path.join(root, filename))

    if not files:
        print(f"Aucun fichier trouvé dans '{INPUT_FOLDER}' (ni ses sous-dossiers)")
        return

    print(f"{len(files)} fichier(s) trouvé(s)\n")

    ok_count  = 0
    err_count = 0

    for file_path in files:
        # Chemin relatif du fichier par rapport à INPUT_FOLDER
        # ex. "document client 2/invoice.pdf"
        rel_path = os.path.relpath(file_path, INPUT_FOLDER)
        print(f"Traitement : {rel_path}")

        # ── Conversion PDF → image temporaire ────────────────────────
        if file_path.lower().endswith('.pdf'):
            try:
                pages = convert_from_path(file_path, poppler_path=POPPLER_PATH)
                temp_image_path = "temp_page.jpg"
                pages[0].save(temp_image_path, "JPEG")
                result = process_document_extraction(temp_image_path)
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
            except Exception as e:
                print(f"  ✗ Erreur PDF : {e}\n")
                err_count += 1
                continue
        else:
            result = process_document_extraction(file_path)

        if not result:
            print(f"  ✗ Extraction échouée (image illisible ?)\n")
            err_count += 1
            continue

        # ── Calcul du chemin de sortie en miroir de l'entrée ─────────
        # Structure d'entrée  : test_documents/document client 2/invoice.pdf
        # Structure de sortie : resultats_json/document client 2/invoice.pdf.json
        rel_dir     = os.path.dirname(rel_path)          # "document client 2"
        output_dir  = os.path.join(OUTPUT_FOLDER, rel_dir)
        os.makedirs(output_dir, exist_ok=True)

        output_name = os.path.basename(file_path) + ".json"  # "invoice.pdf.json"
        output_path = os.path.join(output_dir, output_name)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)

        print(f"  ✓ → {output_path}\n")
        ok_count += 1

    print(f"─── Terminé : {ok_count} succès, {err_count} erreur(s) ───")


if __name__ == "__main__":
    main()