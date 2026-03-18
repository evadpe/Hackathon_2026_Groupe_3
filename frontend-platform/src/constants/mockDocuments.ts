/**
 * Mock Documents pour tester le composant ValidationForm
 * Utilise le type AdminDocument exact du projet
 */

import { AdminDocument } from "@/types";

// ✅ Facture Amazon AWS avec anomalies
export const mockFactureAmazon: AdminDocument = {
  id: "doc_amazon_001",
  filename: "facture_amazon_aws.pdf",
  fileUrl: "/uploads/facture_amazon_aws.pdf",
  type: "invoice",
  status: "silver", // Zone Silver = données extraites par OCR
  uploadDate: "2024-03-15T10:30:00.000Z",
  extractedData: {
    // 📝 Champs texte
    supplier: "Amazon Web Services EMEA SARL",
    invoice_number: "INV-2024-03-001",
    siren: "443966172",
    siret: "44396617200038",
    address: "38 Avenue John F. Kennedy, L-1855 Luxembourg",
    email: "aws-emea-billing@amazon.com",
    
    // 📅 Champs date (format ISO string)
    issue_date: "2024-03-01",
    due_date: "2024-03-31",
    
    // 💰 Champs numériques
    amount_ht: 850.00,
    vat: 170.00,
    amount_ttc: 1020.00,
    vat_rate: 20,
    
    // ℹ️ Informations additionnelles
    customer_reference: "CLIENT-2024-001",
    payment_method: "Bank Transfer",
    payment_terms: 30
  },
  anomalies: [
    {
      field: "vat",
      message: "TVA calculée (170€) différente de la TVA attendue (171€)",
      severity: "warning"
    },
    {
      field: "siren",
      message: "SIREN non vérifié dans la base KBIS",
      severity: "error"
    }
  ]
};

// ✅ Facture OVH propre (sans anomalies)
export const mockFactureOVH: AdminDocument = {
  id: "doc_ovh_002",
  filename: "facture_ovh.pdf",
  fileUrl: "/uploads/facture_ovh.pdf",
  type: "invoice",
  status: "silver",
  uploadDate: "2024-03-16T14:20:00.000Z",
  extractedData: {
    supplier: "OVH SAS",
    invoice_number: "FR2024001234",
    siren: "424761419",
    siret: "42476141900045",
    address: "2 rue Kellermann, 59100 Roubaix, France",
    email: "facturation@ovh.com",
    
    issue_date: "2024-03-10",
    due_date: "2024-04-10",
    
    amount_ht: 500.00,
    vat: 100.00,
    amount_ttc: 600.00,
    vat_rate: 20,
    
    customer_reference: "OVH-CLIENT-789",
    payment_method: "Direct Debit",
    payment_terms: 30
  },
  anomalies: []
};

// ✅ Facture avec beaucoup d'anomalies critiques
export const mockFactureCritique: AdminDocument = {
  id: "doc_critique_003",
  filename: "facture_problematique.pdf",
  fileUrl: "/uploads/facture_problematique.pdf",
  type: "invoice",
  status: "silver",
  uploadDate: "2024-03-17T11:00:00.000Z",
  extractedData: {
    supplier: "Fournisseur Inconnu",
    invoice_number: "",
    siren: "000000000",
    siret: "",
    address: "",
    email: "contact@invalid",
    
    issue_date: "2024-13-45", // ❌ Date invalide
    due_date: "",
    
    amount_ht: 0,
    vat: -50, // ❌ Négatif !
    amount_ttc: 1500,
    vat_rate: 0,
    
    customer_reference: "",
    payment_method: "",
    payment_terms: null
  },
  anomalies: [
    {
      field: "siren",
      message: "SIREN invalide (doit contenir 9 chiffres)",
      severity: "error"
    },
    {
      field: "issue_date",
      message: "Date d'émission invalide ou mal formatée",
      severity: "error"
    },
    {
      field: "vat",
      message: "Montant de TVA incohérent (valeur négative)",
      severity: "error"
    },
    {
      field: "invoice_number",
      message: "Numéro de facture manquant",
      severity: "error"
    },
    {
      field: "amount_ht",
      message: "Montant HT à 0€ alors que TTC = 1500€",
      severity: "warning"
    }
  ]
};

// ✅ Devis (type différent)
export const mockDevis: AdminDocument = {
  id: "doc_quote_004",
  filename: "devis_prestation.pdf",
  fileUrl: "/uploads/devis_prestation.pdf",
  type: "quote",
  status: "silver",
  uploadDate: "2024-03-18T09:00:00.000Z",
  extractedData: {
    supplier: "Acme Services",
    quote_number: "DEVIS-2024-001",
    siren: "123456789",
    
    issue_date: "2024-03-18",
    validity_date: "2024-04-18",
    
    amount_ht: 2500.00,
    vat: 500.00,
    amount_ttc: 3000.00,
    vat_rate: 20,
    
    description: "Prestation de conseil en architecture logicielle",
    duration_days: 5
  },
  anomalies: []
};

// ✅ Bon de commande
export const mockBonCommande: AdminDocument = {
  id: "doc_po_005",
  filename: "bon_commande_materiel.pdf",
  fileUrl: "/uploads/bon_commande_materiel.pdf",
  type: "purchase_order",
  status: "silver",
  uploadDate: "2024-03-18T15:00:00.000Z",
  extractedData: {
    supplier: "Tech Supplier Inc",
    order_number: "PO-2024-789",
    siren: "987654321",
    
    order_date: "2024-03-18",
    delivery_date: "2024-04-01",
    
    amount_ht: 15000.00,
    vat: 3000.00,
    amount_ttc: 18000.00,
    vat_rate: 20,
    
    item_description: "Serveurs Dell PowerEdge R750 x3",
    quantity: 3,
    unit_price: 5000.00
  },
  anomalies: [
    {
      field: "delivery_date",
      message: "Délai de livraison très court (14 jours)",
      severity: "warning"
    }
  ]
};

// ✅ Document avec valeurs null/undefined (pour tester la robustesse)
export const mockDocumentPartial: AdminDocument = {
  id: "doc_partial_006",
  filename: "facture_incomplete.pdf",
  fileUrl: "/uploads/facture_incomplete.pdf",
  type: "invoice",
  status: "silver",
  uploadDate: "2024-03-19T10:00:00.000Z",
  extractedData: {
    supplier: "Partial Data Corp",
    invoice_number: "PARTIAL-001",
    siren: null,
    siret: undefined,
    
    issue_date: "2024-03-19",
    due_date: null,
    
    amount_ht: 750,
    vat: undefined,
    amount_ttc: 900,
    vat_rate: 20,
    
    email: null,
    payment_method: undefined
  },
  anomalies: [
    {
      field: "vat",
      message: "Montant TVA non extrait par l'OCR",
      severity: "error"
    },
    {
      field: "siren",
      message: "SIREN manquant",
      severity: "error"
    }
  ]
};

// 📊 Export d'un tableau pour faciliter les tests en boucle
export const allMockDocuments: AdminDocument[] = [
  mockFactureAmazon,
  mockFactureOVH,
  mockFactureCritique,
  mockDevis,
  mockBonCommande,
  mockDocumentPartial
];

