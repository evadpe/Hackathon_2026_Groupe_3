import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}



export const getFieldType = (key: string, value: any): 'date' | 'number' | 'text' => {
  const lowercaseKey = key.toLowerCase();
  
  // 1. Détection par la clé (le plus fiable pour le métier)
  if (lowercaseKey.includes('date') || lowercaseKey.includes('validity') || lowercaseKey.includes('echeance')) {
    return 'date';
  }
  
  if (lowercaseKey.includes('amount') || lowercaseKey.includes('total') || lowercaseKey.includes('ht') || lowercaseKey.includes('ttc') || lowercaseKey.includes('tva')) {
    return 'number';
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