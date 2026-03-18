"use client";
import SupplierTable from '@/components/crm/SupplierTable';
import { AdminDocument } from '@/types';
import { Plus, Download, Filter } from 'lucide-react';

const GOLD_DOCS_MOCK: AdminDocument[] = [
  {
    id: "1",
    filename: "inv_001.pdf",
    fileUrl: "#",
    type: "invoice",
    status: "gold",
    uploadDate: "2026-03-10",
    extractedData: { companyName: "Microsoft France", siren: "327733184", amountTTC: 14500.00 },
    anomalies: []
  },
  {
    id: "2",
    filename: "inv_002.pdf",
    fileUrl: "#",
    type: "invoice",
    status: "gold",
    uploadDate: "2026-03-12",
    extractedData: { companyName: "OVH Cloud", siren: "435147123", amountTTC: 890.50 },
    anomalies: []
  }
];

export default function CRMPage() {
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
        <SupplierTable documents={GOLD_DOCS_MOCK} />
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