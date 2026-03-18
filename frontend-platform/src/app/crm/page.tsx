"use client";
import { useState, useEffect } from 'react';
import SupplierTable from '@/components/crm/SupplierTable';
import { AdminDocument } from '@/types';
import { Plus, Download, Filter } from 'lucide-react';
import { docService } from '@/services/docService';

export default function CRMPage() {
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    docService.getGoldDocs()
      .then(setDocuments)
      .catch((err) => console.error("Erreur chargement Zone Gold", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Espace Métier</h1>
          <p className="text-gray-500">Consultez les documents validés et conformes (Zone Gold).</p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium">
            <Download size={18} /> Exporter CSV
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium">
            <Plus size={18} /> Nouveau Document
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard title="Documents Validés" value="128" change="+12% ce mois" />
        <StatCard title="Volume de Paiements" value="45 230 €" change="+5% ce mois" />
        <StatCard title="Taux de Conformité" value="98.2%" change="Stable" />
      </div>

      {/* Table Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Dernières Pièces Comptables</h2>
          <button className="text-gray-500 hover:text-gray-700">
            <Filter size={20} />
          </button>
        </div>
        {loading ? (
          <p className="text-sm text-gray-400 py-8 text-center">Chargement...</p>
        ) : (
          <SupplierTable documents={documents} />
        )}
      </div>
    </div>
  );
}

function StatCard({ title, value, change }: { title: string, value: string, change: string }) {
  return (
    <div className="p-6 bg-white border border-gray-200 rounded-xl shadow-sm">
      <p className="text-sm text-gray-500 font-medium">{title}</p>
      <p className="text-2xl font-bold mt-1 text-gray-900">{value}</p>
      <p className="text-xs text-green-600 mt-2 font-medium">{change}</p>
    </div>
  );
}