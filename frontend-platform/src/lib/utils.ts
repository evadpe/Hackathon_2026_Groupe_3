import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}



export const getFieldType = (key: string, value: any): 'date' | 'number' | 'text' => {
  const lowerKey = key.toLowerCase();
  
  //  Détection des dates
  if (
    lowerKey.includes("date") ||
    lowerKey.includes("echeance") ||
    lowerKey.includes("emission") ||
    lowerKey.includes("due") ||
    lowerKey.includes("issue") ||
    lowerKey.includes("validity") ||
    lowerKey.includes("delivery") ||
    lowerKey.includes("order")
  ) {
    return "date";
  }
  
  //  Détection des nombres
  if (
    lowerKey.includes("amount") ||
    lowerKey.includes("montant") ||
    lowerKey.includes("price") ||
    lowerKey.includes("prix") ||
    lowerKey.includes("total") ||
    lowerKey.includes("tva") ||
    lowerKey.includes("vat") ||
    lowerKey.includes("rate") ||
    lowerKey.includes("taux") ||
    lowerKey.includes("quantity") ||
    lowerKey.includes("quantite") ||
    lowerKey.includes("terms") ||
    lowerKey.includes("duration") ||
    typeof value === "number"
  ) {
    return "number";
  }

  // 2. Détection par la valeur (fallback)
  if (typeof value === 'number') return 'number';
  
  // Test si la string ressemble à une date ISO (YYYY-MM-DD)
  const dateRegex = /^\d{4}-\d{2}-\d{2}/;
  if (typeof value === 'string' && dateRegex.test(value)) {
    return 'date';
  }

  return 'text';
};