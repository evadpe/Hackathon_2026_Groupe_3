import easyocr
import re
import json
import os

# On définit la fonction avec un nom de variable générique : 'chemin_fichier'
def extraire_donnees(chemin_fichier):
    # Vérification : est-ce que le fichier existe vraiment ?
    if not os.path.exists(chemin_fichier):
        return {"erreur": f"Le fichier {chemin_fichier} n'a pas été trouvé."}

    # 1. Lecture OCR (EasyOCR gère les .jfif, .jpg, .png directement)
    # Note : on ne fait pas la partie PDF ici pour rester simple sur ton image
    print(f"Analyse de {chemin_fichier} en cours...")
    
    reader = easyocr.Reader(['fr'])
    resultat = reader.readtext(chemin_fichier, detail=0)
    texte_complet = " ".join(resultat)

    # 2. Extraction par "RegEx" améliorée
    
   # 1. Extraction du SIRET (toujours 14 chiffres)
    siret = re.search(r'\d{14}', texte_complet)
    
    # 2. Extraction de la DATE (JJ separator MM separator AAAA)
    date = re.search(r'\d{2}[/.,*]\d{2}[/.,*]\d{4}', texte_complet)
    
    # 3. Extraction du MONTANT (plus robuste)
    # On cherche le mot "TOTAL" ou "PAYER", puis on prend les chiffres qui suivent
    match_montant = re.search(r'(?:TOTAL|PAYER|TTC)[:\s]+(\d+[.,]\d{2,3})', texte_complet, re.IGNORECASE)
    
    if match_montant:
        montant_final = match_montant.group(1)
    else:
        # Si on ne trouve pas le mot "TOTAL", on cherche par défaut un gros chiffre à la fin
        tous_les_montants = re.findall(r'\d+[.,]\d{2,3}', texte_complet)
        montant_final = tous_les_montants[-1] if tous_les_montants else "Non détecté"

    # 4. Structuration JSON
    donnees = {
        "siret": siret.group() if siret else "Non détecté",
        "montant_ttc": montant_final,
        "date": date.group() if date else "Non détectée",
        "texte_brut": texte_complet
    }
    
    return donnees

# Test réel sur un fichier image
# Assure-toi que ton image 'téléchargement.jfif' est bien dans le même dossier que ce script !
fichier_a_tester = 'ma_facture_fake2.jpg' 

resultat_final = extraire_donnees(fichier_a_tester)

# Affichage propre
print("\n--- RESULTATS DE L'EXTRACTION ---")
print(json.dumps(resultat_final, indent=4, ensure_ascii=False))
# Nettoyage pour Hamza
date_propre = resultat_final["date"].replace(',', '/').replace('*', '/')
montant_propre = resultat_final["montant_ttc"].replace(',', '.')

print(f"Données prêtes pour le CRM :")
print(f"- Date corrigée : {date_propre}")
print(f"- Montant corrigé : {float(montant_propre):.2f} €")