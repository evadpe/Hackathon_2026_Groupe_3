import api from '@/lib/axios';
import { AdminDocument } from '@/types';


export const docService = {
  // 1. Upload vers Zone Bronze
  uploadDocs: async (files: File[]): Promise<AdminDocument[]> => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    const { data } = await api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
  },

  // 2. Récupérer les docs pour la Conformité (Zone Silver)
  getPendingDocs: async (): Promise<AdminDocument[]> => {
    const { data } = await api.get('/documents/pending');
    return data;
  },

  // 3. Valider un doc (Passage en Zone Gold)
  validateDoc: async (id: string, finalData: any): Promise<void> => {
    await api.post(`/documents/${id}/validate`, finalData);
  },

  // 4. Récupérer l'Espace Métier (Zone Gold)
  getGoldDocs: async (): Promise<AdminDocument[]> => {
    const { data } = await api.get('/documents/gold');
    return data;
  }
};