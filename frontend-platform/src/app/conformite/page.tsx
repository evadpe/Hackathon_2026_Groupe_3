"use client";
import { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import UploadZone from '@/components/conformite/UploadZone';
import DocumentList from '@/components/conformite/DocumentList';
import DocumentViewer from '@/components/conformite/DocumentViewer';
import ValidationForm from '@/components/conformite/ValidationForm';
import { AdminDocument } from '@/types';
import { docService } from '@/services/docService';

export default function ConformitePage() {
  const [documents, setDocuments] = useState<AdminDocument[]>([]);

  useEffect(() => {
    docService.getPendingDocs()
      .then(setDocuments)
      .catch((err) => console.error("Erreur chargement documents", err));
  }, []);
  const [selectedDoc, setSelectedDoc] = useState<AdminDocument | null>(null);
  const [showUpload, setShowUpload] = useState(true);

  // Appelé après validation ou rejet : retire le document traité et sélectionne le suivant automatiquement
  const handleDocumentValidated = (validatedId: string) => {
    const updatedList = documents.filter(doc => doc.id !== validatedId);
    setDocuments(updatedList);

    if (updatedList.length > 0) {
      setSelectedDoc(updatedList[0]);
    } else {
      setSelectedDoc(null);
      setShowUpload(true); // Retour à l'upload si tout est fini
    }
  };

  const handleUploadSuccess = (newDocs: AdminDocument[]) => {
    setDocuments(prev => [...prev, ...newDocs]);
    // Ouvre directement le premier document du lot uploadé
    setSelectedDoc(newDocs[0]);
    setShowUpload(false);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">

      {/* 1. Sidebar de navigation des documents (Silver Zone) */}
      <aside className="w-72 flex flex-col border-r bg-white shrink-0">
        <div className="p-4 border-b flex justify-between items-center bg-gray-50/50">
          <h2 className="font-bold text-gray-700">Flux à valider ({documents.length})</h2>
          <button
            onClick={() => setShowUpload(true)}
            className="p-1.5 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors"
            title="Ajouter des documents"
          >
            <Plus size={20} />
          </button>
        </div>

        <DocumentList
          documents={documents}
          selectedId={selectedDoc?.id}
          onSelect={(doc) => {
            setSelectedDoc(doc);
            setShowUpload(false);
          }}
        />
      </aside>

      {/* 2. Zone de travail principale */}
      <main className="flex-1 flex flex-col overflow-hidden">

        {showUpload ? (
          /* ÉTAT : UPLOAD */
          <div className="flex-1 flex items-center justify-center p-12 bg-gray-100">
            <div className="max-w-3xl w-full space-y-6">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-800">Nouveau versement</h2>
                <p className="text-gray-500">Ajoutez les pièces comptables pour analyse OCR et détection de fraude.</p>
              </div>
              <UploadZone onUploadComplete={handleUploadSuccess} />
              {documents.length > 0 && (
                <button
                  onClick={() => setShowUpload(false)}
                  className="w-full text-sm text-blue-600 font-medium hover:underline mt-4"
                >
                  Retour à la liste ({documents.length} documents en attente)
                </button>
              )}
            </div>
          </div>
        ) : selectedDoc ? (
          /* ÉTAT : SPLIT-SCREEN (VIEWER + FORM) */
          <div className="flex-1 flex overflow-hidden">
            <div className="flex-1">
              <DocumentViewer
                fileUrl={selectedDoc.fileUrl}
                filename={selectedDoc.filename}
              />
            </div>
            <div className="w-112.5 shrink-0">
              {/* On ajoute onSuccess ici */}
              <ValidationForm
                key={selectedDoc.id} // Indispensable pour reset l'état interne du form
                document={selectedDoc}
                onSuccess={() => handleDocumentValidated(selectedDoc.id)}
              />
            </div>
          </div>
        ) : (
          /* ÉTAT : VIDE */
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 gap-4">
            <div className="p-8 bg-white rounded-full shadow-sm border">
              <Plus size={40} className="text-gray-300" />
            </div>
            <p className="text-lg">Aucun document à valider</p>
            <button
              onClick={() => setShowUpload(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium"
            >
              Importer des fichiers
            </button>
          </div>
        )}
      </main>
    </div>
  );
}