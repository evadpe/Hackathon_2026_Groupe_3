import cv2
import numpy as np

def redresser_image(chemin_entree, chemin_sortie):
    # 1. Charger l'image
    image = cv2.imread(chemin_entree)
    if image is None:
        return None

    # 2. Conversion en gris pour mieux détecter les formes
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 3. Inverser les couleurs pour avoir le texte en blanc sur fond noir
    # Cela aide l'algorithme à trouver l'orientation du bloc de texte
    gray = cv2.bitwise_not(gray)
    
    # 4. Trouver tous les pixels qui ne sont pas noirs (donc le texte)
    coords = np.column_stack(np.where(gray > 0))
    
    # 5. Calculer l'angle de la boîte qui contient tout le texte
    angle = cv2.minAreaRect(coords)[-1]
    
    # Correction de l'angle selon la façon dont OpenCV le calcule
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    # 6. Effectuer la rotation inverse pour remettre l'image droite
    (h, w) = image.shape[:2]
    centre = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(centre, angle, 1.0)
    redressee = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # 7. Sauvegarder l'image "propre"
    cv2.imwrite(chemin_sortie, redressee)
    print(f"Image redressée avec succès : {chemin_sortie} (Angle : {angle:.2f}°)")
    return chemin_sortie