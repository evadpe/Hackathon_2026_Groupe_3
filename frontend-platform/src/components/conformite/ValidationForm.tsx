"use client";
import { Save, AlertTriangle, CheckCircle2, Loader2, XCircle, ShieldCheck } from "lucide-react";
import { AdminDocument } from "@/types";
import { useEffect, useState } from "react";
import { docService } from "@/services/docService";

interface Props {
  document: AdminDocument;
  onSuccess?: () => void;
}

const FIELD_LABELS: Record<string, string> = {
  numero: "Numéro",
  date: "Date d'émission",
  fournisseur: "Fournisseur",
  siret: "SIRET",
  total_ht: "Total HT (€)",
  tva_taux: "Taux TVA (%)",
  tva_montant: "Montant TVA (€)",
  total_ttc: "Total TTC (€)",
  echeance: "Date d'échéance",
  validite: "Validité jusqu'au",
  note: "Note",
  fichier: "Fichier",
};

const TYPE_LABELS: Record<string, string> = {
  invoice: "Facture",
  purchase_order: "Bon de commande",
  quote: "Devis",
};

const TYPE_COLORS: Record<string, string> = {
  invoice: "bg-violet-100 text-violet-700",
  purchase_order: "bg-blue-100 text-blue-700",
  quote: "bg-emerald-100 text-emerald-700",
};

function getInputType(key: string, value: unknown): string {
  if (key.includes("date") || key === "echeance" || key === "validite") return "text";
  if (typeof value === "number") return "number";
  return "text";
}

export default function ValidationForm({ document, onSuccess }: Props) {
  const { extractedData, anomalies, type, id } = document;
  const [formData, setFormData] = useState(extractedData);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setFormData(document.extractedData);
  }, [document]);

  const handleChange = (key: string, value: string | number) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const handleValidation = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await docService.validateDoc(id, formData);
      if (onSuccess) onSuccess();
      alert("Document validé et envoyé en Zone Gold !");
    } catch (error) {
      console.error("Erreur lors de la validation", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const errors = anomalies.filter((a) => a.severity === "error");
  const warnings = anomalies.filter((a) => a.severity !== "error");
  const fields = Object.entries(extractedData);

  return (
    <div className="flex flex-col h-full bg-white border-l shadow-xl">

      {/* Header */}
      <div className="p-5 border-b bg-gray-50">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
            <ShieldCheck size={20} className="text-blue-600" />
            Validation OCR
          </h2>
          <span className={`px-3 py-1 text-xs font-bold rounded-full uppercase tracking-wide ${TYPE_COLORS[type] || "bg-gray-100 text-gray-600"}`}>
            {TYPE_LABELS[type] || type}
          </span>
        </div>
        <p className="text-xs text-gray-400 font-mono">ID: {id}</p>
      </div>

      {/* Alertes globales */}
      {anomalies.length > 0 && (
        <div className="px-5 pt-4 space-y-2">
          {errors.length > 0 && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl">
              <p className="text-xs font-bold text-red-700 uppercase mb-1.5 flex items-center gap-1.5">
                <XCircle size={13} /> {errors.length} erreur{errors.length > 1 ? "s" : ""} critique{errors.length > 1 ? "s" : ""}
              </p>
              <ul className="space-y-0.5">
                {errors.map((a, i) => (
                  <li key={i} className="text-xs text-red-600 flex items-start gap-1.5">
                    <span className="mt-0.5">•</span> {a.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {warnings.length > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl">
              <p className="text-xs font-bold text-amber-700 uppercase mb-1.5 flex items-center gap-1.5">
                <AlertTriangle size={13} /> {warnings.length} avertissement{warnings.length > 1 ? "s" : ""}
              </p>
              <ul className="space-y-0.5">
                {warnings.map((a, i) => (
                  <li key={i} className="text-xs text-amber-700 flex items-start gap-1.5">
                    <span className="mt-0.5">•</span> {a.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Formulaire */}
      <form
        id="ocr-form"
        onSubmit={handleValidation}
        className="flex-1 overflow-y-auto px-5 py-4 space-y-4"
      >
        {fields.map(([key, value]) => {
          const anomaly = anomalies.find((a) => a.field === key);
          const label = FIELD_LABELS[key] || key.replace(/_/g, " ");
          const inputType = getInputType(key, value);

          return (
            <div key={key} className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center justify-between">
                {label}
                {anomaly && (
                  <span className={`text-[10px] font-bold flex items-center gap-1 ${anomaly.severity === "error" ? "text-red-500" : "text-amber-500"}`}>
                    {anomaly.severity === "error" ? <XCircle size={11} /> : <AlertTriangle size={11} />}
                    {anomaly.severity === "error" ? "Erreur" : "Avertissement"}
                  </span>
                )}
              </label>

              <div className="relative">
                <input
                  type={inputType}
                  name={key}
                  defaultValue={value?.toString() || ""}
                  onChange={(e) => handleChange(key, e.target.value)}
                  step={inputType === "number" ? "0.01" : undefined}
                  className={`w-full px-3 py-2.5 rounded-lg border text-sm transition-all outline-none focus:ring-2
                    ${anomaly?.severity === "error"
                      ? "border-red-300 bg-red-50 focus:ring-red-100 text-red-800"
                      : anomaly
                      ? "border-amber-300 bg-amber-50 focus:ring-amber-100 text-amber-800"
                      : "border-gray-200 bg-white focus:ring-blue-100 focus:border-blue-400 text-gray-800"
                    }`}
                />
                {!anomaly && value !== undefined && value !== null && value !== "" && (
                  <CheckCircle2 className="absolute right-3 top-3 text-green-500" size={15} />
                )}
              </div>

              {anomaly && (
                <p className={`text-xs font-medium ${anomaly.severity === "error" ? "text-red-600" : "text-amber-600"}`}>
                  {anomaly.message}
                </p>
              )}
            </div>
          );
        })}
      </form>

      {/* Footer */}
      <div className="p-5 border-t bg-gray-50 flex gap-3">
        <button
          type="button"
          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-white text-gray-600 text-sm font-medium transition-colors"
        >
          Rejeter
        </button>
        <button
          form="ocr-form"
          type="submit"
          disabled={isSubmitting}
          className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-semibold flex items-center justify-center gap-2 shadow-md shadow-blue-200 transition-all disabled:opacity-60"
        >
          {isSubmitting ? (
            <Loader2 className="animate-spin" size={16} />
          ) : (
            <Save size={16} />
          )}
          Valider (Gold)
        </button>
      </div>
    </div>
  );
}
