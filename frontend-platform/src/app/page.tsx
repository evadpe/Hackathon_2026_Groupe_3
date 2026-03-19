"use client";
import { useEffect, useState } from "react";
import { docService } from "@/services/docService";
import {
  ShieldCheck,
  Clock,
  FileCheck,
  ArrowUpRight,
  PlusCircle,
  Database,
  BarChart3,
  TrendingUp,
  Receipt,
  ClipboardCheck,
} from "lucide-react";
import Link from "next/link";

// Carte de statistique affichée sur le tableau de bord
function StatCard({
  title,
  value,
  icon: Icon,
  color,
  description,
}: {
  title: string;
  value: number | string;
  icon: any;
  color: string;
  description: string;
}) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all group">
      <div className="flex justify-between items-start mb-4">
        <div className={`p-3 rounded-xl ${color} bg-opacity-10 text-opacity-90`}>
          <Icon className={color.replace("bg-", "text-")} size={24} />
        </div>
        <span className="text-xs font-bold text-green-500 bg-green-50 px-2 py-1 rounded-full flex items-center gap-1">
          <TrendingUp size={12} /> +12%
        </span>
      </div>
      <h3 className="text-gray-500 text-sm font-medium mb-1">{title}</h3>
      <div className="text-2xl font-bold text-gray-900 mb-1">{value}</div>
      <p className="text-xs text-gray-400">{description}</p>
    </div>
  );
}

export default function Home() {
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    validated: 0,
    loading: true,
  });

  useEffect(() => {
    async function loadStats() {
      try {
        const [pending, gold] = await Promise.all([
          docService.getPendingDocs(),
          docService.getGoldDocs(),
        ]);

        setStats({
          total: pending.length + gold.length,
          pending: pending.length,
          validated: gold.length,
          loading: false,
        });
      } catch (error) {
        console.error("Erreur stats dashboard:", error);
        setStats((prev) => ({ ...prev, loading: false }));
      }
    }
    loadStats();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* En-tête de la page */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-10">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
            Tableau de Bord
          </h1>
          <p className="text-gray-500 mt-1">
            Bienvenue sur votre plateforme d&apos;analyse documentaire IA.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/conformite"
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-semibold transition-all shadow-lg shadow-blue-100"
          >
            <PlusCircle size={18} />
            Nouvelle Analyse
          </Link>
        </div>
      </div>

      {/* Grille de statistiques */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <StatCard
          title="Documents Totaux"
          value={stats.loading ? "..." : stats.total}
          icon={Database}
          color="bg-blue-500"
          description="Fichiers traités ce mois-ci"
        />
        <StatCard
          title="En Attente (Silver)"
          value={stats.loading ? "..." : stats.pending}
          icon={Clock}
          color="bg-orange-500"
          description="Analyses à valider manuellement"
        />
        <StatCard
          title="Validés (Gold)"
          value={stats.loading ? "..." : stats.validated}
          icon={FileCheck}
          color="bg-green-500"
          description="Données certifiées prêtes pour CRM"
        />
      </div>

      {/* Zone principale : accès rapide et état du système */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Lien vers l'espace métier */}
        <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-3xl p-8 text-white shadow-xl flex flex-col justify-between">
          <div>
            <div className="bg-white/20 w-fit p-3 rounded-2xl mb-6 backdrop-blur-md">
              <BarChart3 size={32} />
            </div>
            <h2 className="text-2xl font-bold mb-3">
              Prêt pour l&apos;importation ?
            </h2>
            <p className="text-blue-100 mb-8 max-w-sm">
              Tous vos documents validés en zone Gold peuvent être consultés
              dans l&apos;espace métier pour un interfaçage CRM immédiat.
            </p>
          </div>
          <Link
            href="/crm"
            className="group bg-white text-blue-700 font-bold px-6 py-3 rounded-xl flex items-center justify-between hover:bg-blue-50 transition-all"
          >
            Aller vers l&apos;Espace Métier
            <ArrowUpRight className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
          </Link>
        </div>

        {/* État des moteurs IA et conformité */}
        <div className="bg-white border border-gray-100 rounded-3xl p-8 shadow-sm">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-purple-50 text-purple-600 rounded-2xl">
              <ShieldCheck size={28} />
            </div>
            <div>
              <h2 className="font-bold text-xl text-gray-900">
                IA &amp; Conformité
              </h2>
              <div className="flex items-center gap-2 text-green-500 text-xs font-bold uppercase tracking-wider">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                Moteurs OCR Actifs
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-sm text-blue-500">
                  <Receipt size={20} />
                </div>
                <span className="font-medium text-gray-700">
                  Extractions Factures
                </span>
              </div>
              <span className="text-sm font-bold text-blue-600">
                Précision 98%
              </span>
            </div>
            <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-sm text-purple-500">
                  <ClipboardCheck size={20} />
                </div>
                <span className="font-medium text-gray-700">
                  Analyse de Conformité
                </span>
              </div>
              <span className="text-sm font-bold text-blue-600">
                Règles Actives
              </span>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-gray-50">
            <Link
              href="/conformite"
              className="text-blue-600 font-bold text-sm hover:underline flex items-center gap-1 w-fit"
            >
              Voir le centre de conformité <ArrowUpRight size={14} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
