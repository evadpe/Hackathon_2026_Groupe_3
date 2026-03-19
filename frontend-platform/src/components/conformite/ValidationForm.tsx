

"use client";
import { Save, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { AdminDocument } from "@/types";
import { getFieldType } from "@/lib/utils";
import { useEffect, useState } from "react";
import { docService } from "@/services/docService";

interface Props {
  document: AdminDocument;
  onSuccess?: () => void;
}

/**
 * Formate les valeurs selon le type d'input HTML
 * - Date: Convertit en format ISO (YYYY-MM-DD)
 * - Number: S'assure d'avoir une valeur numérique
 * - Text: Conversion simple en string
 */
function formatValueForInput(value: any, inputType: string): string {
  if (value === null || value === undefined) return "";
  
  // Pour les dates, convertir en format ISO (YYYY-MM-DD)
  if (inputType === "date") {
    try {
      const date = new Date(value);
      if (!isNaN(date.getTime())) {
        return date.toISOString().split("T")[0];
      }
    } catch {
      return "";
    }
  }
  
  // Pour les nombres, s'assurer d'avoir une valeur numérique
  if (inputType === "number") {
    const num = Number(value);
    return isNaN(num) ? "" : num.toString();
  }
  
  // Pour le texte, conversion simple en string
  return String(value);
}

/**
 * Badge de statut avec couleurs appropriées
 */
function StatusBadge({ status }: { status: AdminDocument['status'] }) {
  const colors = {
    bronze: "bg-orange-100 text-orange-700",
    silver: "bg-gray-100 text-gray-700",
    gold: "bg-yellow-100 text-yellow-700"
  };
  
  return (
    <span className={`px-3 py-1 text-xs font-bold rounded-full uppercase tracking-widest ${colors[status]}`}>
      {status}
    </span>
  );
}

/**
 * Badge de type de document
 */
function TypeBadge({ type }: { type: AdminDocument['type'] }) {
  const labels = {
    invoice: "Facture",
    quote: "Devis",
    purchase_order: "Bon de commande"
  };
  
  return (
    <span className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full uppercase tracking-widest">
      {labels[type]}
    </span>
  );
}

export default function ValidationForm({ document, onSuccess }: Props) {
  const { extractedData, anomalies, type, id, filename, status } = document;

  const [formData, setFormData] = useState<Record<string, any>>(extractedData || {});
  const [isSubmitting, setIsSubmitting] = useState(false);


  // Reset le formulaire si on change de document
  useEffect(() => {
    setFormData(document.extractedData || {});
  }, [document.extractedData, document.id]);

  /**
   * Gère les changements d'input avec conversion de types
   */
  const handleChange = (key: string, value: string, inputType: string) => {
    setFormData((prev) => {
      let processedValue: any = value;
      
      // Conversion selon le type
      if (inputType === "number") {
        processedValue = value === "" ? null : Number(value);
      } else if (inputType === "date") {
        processedValue = value; // Garder le format ISO
      }
      
      return {
        ...prev,
        [key]: processedValue,
      };
    });
  
  };

  const handleValidation = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await docService.validateDoc(document.id, formData);
      if (onSuccess) onSuccess();
      alert("Document validé et envoyé en Zone Gold !");
    } catch (error) {
      console.error("Erreur lors de la validation", error);
      alert("Erreur lors de la validation");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    const reason = prompt("Raison du rejet (optionnel) :");
    if (reason === null) return; // annulé
    setIsSubmitting(true);
    try {
      await docService.rejectDoc(document.id, reason || undefined);
      if (onSuccess) onSuccess();
    } catch (error) {
      console.error("Erreur lors du rejet", error);
      alert("Erreur lors du rejet");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Transformation de l'objet en tableau pour le mapping
  const fields = Object.entries(extractedData || {});
  
  // Compteur d'anomalies par sévérité
  const errorCount = anomalies.filter(a => a.severity === "error").length;
  const warningCount = anomalies.filter(a => a.severity === "warning").length;

  return (
    <div className="flex flex-col h-full bg-white border-l shadow-xl">
      {/* ============================================
          1. HEADER - Informations du document
          ============================================ */}
      <div className="p-6 border-b bg-gradient-to-r from-gray-50 to-white">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-bold text-gray-800">Validation OCR</h2>
          <div className="flex gap-2">
            <TypeBadge type={type} />
            <StatusBadge status={status} />
          </div>
        </div>
        
        <div className="space-y-1 text-sm text-gray-600">
          <p className="font-medium">{filename}</p>
          <p className="text-xs">ID: {id}</p>
        </div>
        
        {/* Indicateur d'anomalies dans le header */}
        {anomalies.length > 0 && (
          <div className="mt-3 flex gap-2 text-xs">
            {errorCount > 0 && (
              <span className="px-2 py-1 bg-red-100 text-red-700 rounded font-medium">
                {errorCount} erreur{errorCount > 1 ? 's' : ''}
              </span>
            )}
            {warningCount > 0 && (
              <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded font-medium">
                {warningCount} avertissement{warningCount > 1 ? 's' : ''}
              </span>
            )}
          </div>
        )}
      </div>

      {/* ============================================
          2. FORMULAIRE - Champs extraits avec validation
          ============================================ */}
      <form
        id="ocr-form"
        onSubmit={handleValidation}
        className="flex-1 overflow-y-auto px-5 py-4 space-y-4"
      >
        {fields.map(([key, value]) => {
          const inputType = getFieldType(key, value);
          const anomaly = anomalies?.find((a) => a.field === key);
          
          // Récupération de la valeur actuelle depuis formData
          const currentValue = formData[key];
          const formattedValue = formatValueForInput(currentValue, inputType);

          // Style selon la sévérité de l'anomalie
          const inputClass = anomaly 
            ? anomaly.severity === "error"
              ? "border-red-300 bg-red-50 focus:ring-2 focus:ring-red-200"
              : "border-orange-300 bg-orange-50 focus:ring-2 focus:ring-orange-200"
            : "border-gray-200 focus:ring-2 focus:ring-blue-100 focus:border-blue-400";

          return (
            <div key={key} className="space-y-1.5">
              {/* Label du champ */}
              <label className="text-sm font-semibold text-gray-700 flex justify-between items-center">
                <span>{key.replace(/_/g, " ").toUpperCase()}</span>
                {anomaly && (
                  <span 
                    className={`text-[10px] font-bold flex items-center gap-1 uppercase ${
                      anomaly.severity === "error" ? "text-red-500" : "text-orange-500"
                    }`}
                  >
                    <AlertCircle size={12} />
                    {anomaly.severity === "error" ? "Erreur" : "Attention"}
                  </span>
                )}
              </label>

              {/* Input avec icône de validation */}
              <div className="relative">
                <input
                  type={inputType}
                  name={key}
                  value={formattedValue}
                  onChange={(e) => handleChange(key, e.target.value, inputType)}
                  step={inputType === "number" ? "0.01" : undefined}
                  className={`w-full p-2.5 rounded-lg border text-sm transition-all outline-none ${inputClass}`}
                  placeholder={
                    inputType === "date" 
                      ? "YYYY-MM-DD" 
                      : inputType === "number" 
                      ? "0.00" 
                      : ""
                  }
                />
                
                {/* Icône de validation (seulement si pas d'anomalie et valeur présente) */}
                {!anomaly && currentValue !== null && currentValue !== undefined && currentValue !== "" && (
                  <CheckCircle2
                    className="absolute right-3 top-3 text-green-500"
                    size={16}
                  />
                )}
              </div>

              {/* Message d'erreur/warning */}
              {anomaly && (
                <p className={`text-xs font-medium ${
                  anomaly.severity === "error" ? "text-red-600" : "text-orange-600"
                }`}>
                  {anomaly.message}
                </p>
              )}
            </div>
          );
        })}

        {/* ============================================
            3. ALERTE GLOBALE - Résumé des anomalies
            ============================================ */}
        {anomalies.length > 0 && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl">
            <h4 className="text-xs font-bold text-red-800 uppercase mb-3 flex items-center gap-2">
              <AlertCircle size={14} />
              Incohérences détectées ({anomalies.length})
            </h4>
            <ul className="text-xs text-red-700 space-y-2">
              {anomalies.map((a, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className={`mt-0.5 ${
                    a.severity === "error" ? "text-red-500" : "text-orange-500"
                  }`}>
                    {a.severity === "error" ? "•" : "-"}
                  </span>
                  <span>
                    <strong className="font-semibold">{a.field}:</strong> {a.message}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </form>

      {/* ============================================
          4. FOOTER - Actions de validation
          ============================================ */}
      <div className="p-6 border-t bg-gray-50 grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={handleReject}
          disabled={isSubmitting}
          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-white text-gray-600 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Rejeter
        </button>
        <button
          form="ocr-form"
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium flex items-center justify-center gap-2 shadow-lg shadow-blue-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <Loader2 className="animate-spin" size={18} />
          ) : (
            <Save size={18} />
          )}
          Valider (Gold)
        </button>
      </div>
    </div>
  );
}