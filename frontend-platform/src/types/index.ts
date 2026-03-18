export type DocStatus = 'bronze' | 'silver' | 'gold';
export type DocType = 'invoice' | 'quote' | 'purchase_order';

export interface Anomaly {
  field: string;
  message: string;
  severity?: 'error' | 'warning';
}

export interface AdminDocument {
  id: string;
  filename: string;
  fileUrl: string;
  type: DocType;
  status: DocStatus;
  uploadDate: string;
  extractedData: {
    [key: string]: string | number | boolean | null | undefined;
  };
  anomalies: Anomaly[];
}