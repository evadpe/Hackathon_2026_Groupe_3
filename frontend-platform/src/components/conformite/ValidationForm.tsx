"use client";
import { Save, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { AdminDocument } from "@/types";
import { getFieldType } from "@/lib/utils"; // La fonction d'inférence vue juste avant
import { useEffect, useState } from "react";
import { docService } from "@/services/docService";

interface Props {
  document: AdminDocument;
  onSuccess?: () => void; // Pour rafraîchir la liste après validation
}

export default function ValidationForm({ document , onSuccess }: Props) {
  const { extractedData, anomalies, type, id } = document;

  const [formData, setFormData] = useState(extractedData);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset le formulaire si on change de document dans la liste
  useEffect(() => {
    setFormData(document.extractedData);
  }, [document]);

  const handleChange = (key: string, value: string | number) => {
    setFormData((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleValidation = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // 2. Envoi des données corrigées vers la Zone Gold via le service
      await docService.validateDoc(document.id, formData);

      if (onSuccess) onSuccess();
      alert("Document validé et envoyé en Zone Gold !");
    } catch (error) {
      console.error("Erreur lors de la validation", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // On transforme l'objet en tableau pour le mapping dynamique
  const fields = Object.entries(extractedData);

  return (
    <div className="flex flex-col h-full bg-white border-l shadow-xl">
      {/* 1. Header Dynamique (Conservé) */}
      <div className="p-6 border-b bg-gray-50">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-800">Validation OCR</h2>
          <span className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full uppercase tracking-widest">
            {type}
          </span>
        </div>
        <p className="text-sm text-gray-500 mt-2">ID: {id}</p>
      </div>

      {/* 2. Formulaire avec Inférence de Type (Refactorisé proprement) */}
      <form
        id="ocr-form"
        onSubmit={handleValidation}
        className="flex-1 overflow-y-auto p-6 space-y-5"
      >
        {fields.map(([key, value]) => {
          const inputType = getFieldType(key, value); // Nouvelle fonctionnalité
          const anomaly = anomalies.find((a) => a.field === key);

          return (
            <div key={key} className="space-y-1.5">
              <label className="text-sm font-semibold text-gray-700 flex justify-between">
                {key.replace(/_/g, " ").toUpperCase()}
                {anomaly && (
                  <span className="text-[10px] text-red-500 font-bold flex items-center gap-1 uppercase">
                    <AlertCircle size={12} /> Anomalie
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
                  className={`w-full p-2.5 rounded-lg border text-sm transition-all outline-none
                    ${
                      anomaly
                        ? "border-red-300 bg-red-50 focus:ring-red-100"
                        : "border-gray-200 focus:ring-blue-100 focus:border-blue-400"
                    }`}
                />
                {!anomaly && value && (
                  <CheckCircle2
                    className="absolute right-3 top-3 text-green-500"
                    size={16}
                  />
                )}
              </div>

              {anomaly && (
                <p className="text-xs text-red-600 font-medium">
                  {anomaly.message}
                </p>
              )}
            </div>
          );
        })}

        {/* 3. Alerte Globale (Conservé) */}
        {anomalies.length > 0 && (
          <div className="mt-6 p-4 bg-red-50 border border-red-100 rounded-xl">
            <h4 className="text-xs font-bold text-red-800 uppercase mb-2 text-center">
              Incohérences critiques détectées
            </h4>
            <ul className="text-xs text-red-700 space-y-1">
              {anomalies.map((a, i) => (
                <li key={i} className="flex items-center gap-2">
                  • {a.message}
                </li>
              ))}
            </ul>
          </div>
        )}
      </form>

      {/* 4. Footer Actions (Conservé) */}
      <div className="p-6 border-t bg-gray-50 grid grid-cols-2 gap-3">
        <button
          type="button"
          className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-white text-gray-700 font-medium transition-colors"
        >
          Rejeter
        </button>
        <button
          form="ocr-form"
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium flex items-center justify-center gap-2 shadow-lg shadow-blue-200 transition-all"
        >
          {isSubmitting ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
          <Save size={18} /> Valider (Gold)
        </button>
      </div>
    </div>
  );
}
