"use client";
import { AdminDocument } from '@/types';
import {  ExternalLink, CheckCircle2, AlertTriangle, FileText } from 'lucide-react';

interface Props {
  documents: AdminDocument[];
}

export default function SupplierTable({ documents }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <table className="w-full text-left border-collapse">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Fournisseur</th>
            <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Type</th>
            <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">SIREN</th>
            <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Montant TTC</th>
            <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Statut</th>
            <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {documents.map((doc) => (
            <tr key={doc.id} className="hover:bg-gray-50 transition-colors group">
              <td className="px-6 py-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                    <FileText size={18} />
                  </div>
                  <span className="font-medium text-gray-900">{doc.extractedData.companyName || "Inconnu"}</span>
                </div>
              </td>
              <td className="px-6 py-4">
                <span className="text-sm text-gray-600 capitalize">{doc.type}</span>
              </td>
              <td className="px-6 py-4">
                <code className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-700">
                  {doc.extractedData.siren}
                </code>
              </td>
              <td className="px-6 py-4 font-semibold text-gray-900">
                {doc.extractedData.amountTTC?.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
              </td>
              <td className="px-6 py-4">
                <StatusBadge status={doc.status} />
              </td>
              <td className="px-6 py-4">
                <button className="p-2 hover:bg-white border border-transparent hover:border-gray-200 rounded-lg transition-all text-gray-400 hover:text-blue-600">
                  <ExternalLink size={18} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'gold') {
    return (
      <span className="inline-flex items-center gap-1.5 py-1 px-2.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
        <CheckCircle2 size={12} /> Validé Gold
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 py-1 px-2.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
      <AlertTriangle size={12} /> En cours
    </span>
  );
}