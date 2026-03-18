import api from '@/lib/axios';
import { AdminDocument } from '@/types';

export const docService = {
  // 1. Upload & Analyse (Bronze ➔ Silver)
  uploadDocs: async (files: File[]): Promise<AdminDocument[]> => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    const { data } = await api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
  },

  // 2. Récupérer les docs en attente de validation (Zone Silver)
  getPendingDocs: async (): Promise<AdminDocument[]> => {
    const { data } = await api.get('/documents/pending');
    return data;
  },

  // 3. Récupérer un document spécifique par son ID
  getDocumentById: async (id: string): Promise<AdminDocument> => {
    const { data } = await api.get(`/documents/${id}`);
    return data;
  },

  // 4. Valider un doc (Transition Silver ➔ Gold)
  // Utilisation de PUT car on met à jour l'intégralité des données extraites
  validateDoc: async (id: string, finalData: any): Promise<AdminDocument> => {
    const { data } = await api.put(`/documents/${id}/validate`, {
      extractedData: finalData
    });
    return data;
  },

  // 5. Rejeter un document (Transition Silver ➔ Rejected)
  // Utilisation de PATCH pour une modification partielle de statut
  rejectDoc: async (id: string, reason?: string): Promise<AdminDocument> => {
    const { data } = await api.patch(`/documents/${id}/reject`, { reason });
    return data;
  },

  // 6. Récupérer les données certifiées (Zone Gold)
  getGoldDocs: async (search?: string, type?: string): Promise<AdminDocument[]> => {
    const { data } = await api.get('/documents/gold', {
      params: { search, type }
    });
    return data;
  }
};