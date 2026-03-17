"use client";
import { AdminDocument } from '@/types';
import { FileText, AlertCircle, CheckCircle } from 'lucide-react';

interface Props {
  documents: AdminDocument[];
  selectedId?: string;
  onSelect: (doc: AdminDocument) => void;
}

export default function DocumentList({ documents, selectedId, onSelect }: Props) {
  return (
    <div className="w-64 border-r bg-white flex flex-col h-full">
      <div className="p-4 border-b font-semibold text-sm text-gray-500 uppercase">
        File d&apos;attente ({documents.length})
      </div>
      <div className="flex-1 overflow-y-auto">
        {documents.map((doc) => (
          <button
            key={doc.id}
            onClick={() => onSelect(doc)}
            className={`w-full p-4 flex items-start gap-3 border-b text-left transition-colors
              ${selectedId === doc.id ? 'bg-blue-50 border-r-4 border-r-blue-500' : 'hover:bg-gray-50'}`}
          >
            <div className={`mt-1 ${doc.anomalies.length > 0 ? 'text-amber-500' : 'text-blue-500'}`}>
              <FileText size={18} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{doc.filename}</p>
              <div className="flex items-center gap-1 mt-1">
                {doc.anomalies.length > 0 ? (
                  <span className="text-[10px] text-amber-600 flex items-center gap-0.5">
                    <AlertCircle size={10} /> {doc.anomalies.length} alertes
                  </span>
                ) : (
                  <span className="text-[10px] text-green-600 flex items-center gap-0.5">
                    <CheckCircle size={10} /> Prêt
                  </span>
                )}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}