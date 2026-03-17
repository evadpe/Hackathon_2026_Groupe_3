import { AdminDocument } from '@/types';

export const MOCK_DOCUMENTS: AdminDocument[] = [
  {
    id: "INV-2026-001",
    filename: "facture_amazon_aws.pdf",
    fileUrl: "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    type: "invoice",
    status: "silver",
    uploadDate: "2026-03-17T10:00:00Z",
    extractedData: {
      company_name: "Amazon Web Services",
      siren: "833123456",
      invoice_number: "AWS-99821",
      date_emission: "2026-03-01",
      amount_ht: 450.50,
      total_ttc: 540.60,
      tva_rate: "20%"
    },
    anomalies: [
      { field: "total_ttc", message: "Le calcul TTC (450.50 + 20%) devrait être 540.60, vérifiez l'arrondi." }
    ]
  },
  {
    id: "QUO-882",
    filename: "devis_renovation_peinture.pdf",
    fileUrl: "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    type: "quote",
    status: "silver",
    uploadDate: "2026-03-17T11:30:00Z",
    extractedData: {
      prestataire: "Peinture & Co",
      siren_pro: "123456789",
      validity_limit: "2026-06-30",
      total_estimate: 2300.00,
      deposit_required: "30%",
      reference_chantier: "LILLE-2026-A"
    },
    anomalies: []
  },
  {
    id: "PO-4456",
    filename: "bc_materiel_informatique.pdf",
    fileUrl: "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    type: "purchase_order",
    status: "silver",
    uploadDate: "2026-03-17T12:00:00Z",
    extractedData: {
      client_name: "IPSSI School",
      po_number: "BC-2026-009",
      delivery_expected: "2026-04-15",
      global_amount: 12500.80,
      contact_email: "achat@ipssi-school.com"
    },
    anomalies: [
      { field: "global_amount", message: "Dépassement du budget autorisé pour ce département." }
    ]
  }
];