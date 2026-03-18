"use client";
import { AdminDocument } from '@/types';
import { FileText, AlertCircle, XCircle, CheckCircle2 } from 'lucide-react';

interface Props {
  documents: AdminDocument[];
  selectedId?: string;
  onSelect: (doc: AdminDocument) => void;
}

function getConformite(doc: AdminDocument): {
  label: string;
  color: string;
  icon: React.ReactNode;
  bg: string;
} {
  const errors   = doc.anomalies.filter(a => a.severity === 'error');
  const warnings = doc.anomalies.filter(a => a.severity !== 'error');

  if (errors.length > 0) return {
    label: 'Non conforme',
    color: 'text-red-600',
    bg:    'bg-red-50 border-r-red-400',
    icon:  <XCircle size={11} className="text-red-500" />,
  };
  if (warnings.length > 0) return {
    label: 'À vérifier',
    color: 'text-amber-600',
    bg:    'bg-amber-50 border-r-amber-400',
    icon:  <AlertCircle size={11} className="text-amber-500" />,
  };
  return {
    label: 'Conforme',
    color: 'text-green-600',
    bg:    'bg-white border-r-transparent',
    icon:  <CheckCircle2 size={11} className="text-green-500" />,
  };
}

export default function DocumentList({ documents, selectedId, onSelect }: Props) {
  return (
    <div className="w-64 border-r bg-white flex flex-col h-full">
      <div className="p-4 border-b font-semibold text-sm text-gray-500 uppercase">
        File d&apos;attente ({documents.length})
      </div>
      <div className="flex-1 overflow-y-auto">
        {documents.map((doc) => {
          const conformite = getConformite(doc);
          const isSelected = selectedId === doc.id;
          return (
            <button
              key={doc.id}
              onClick={() => onSelect(doc)}
              className={`w-full p-4 flex items-start gap-3 border-b border-r-4 text-left transition-colors
                ${isSelected
                  ? 'bg-blue-50 border-r-blue-500'
                  : `hover:bg-gray-50 ${conformite.bg}`
                }`}
            >
              <div className={`mt-0.5 ${conformite.color}`}>
                <FileText size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{doc.filename}</p>
                <p className="text-[10px] text-gray-400 truncate mt-0.5">{doc.type}</p>
                <div className={`flex items-center gap-1 mt-1.5 font-semibold text-[11px] ${conformite.color}`}>
                  {conformite.icon}
                  {conformite.label}
                  {doc.anomalies.length > 0 && (
                    <span className="text-gray-400 font-normal">
                      ({doc.anomalies.length})
                    </span>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}