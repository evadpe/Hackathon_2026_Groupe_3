"use client";
import { docService } from "@/services/docService";
import { AdminDocument } from "@/types";
import { UploadCloud, X, FileText, Send, Loader2 } from "lucide-react";
import { useState } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";

interface Props {
  onUploadComplete: (docs: AdminDocument[]) => void;
}

export default function UploadZone({ onUploadComplete }: Props) {
  const [stagedFiles, setStagedFiles] = useState<File[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const onDrop = (acceptedFiles: File[]) => {
    // On ajoute les nouveaux fichiers à la liste existante sans les envoyer
    setStagedFiles((prev) => [...prev, ...acceptedFiles]);
  };

  const removeFile = (fileToRemove: File) => {
    setStagedFiles((prev) => prev.filter((f) => f !== fileToRemove));
  };

  const handleStartOCR = async () => {
    if (stagedFiles.length === 0) return;

    setIsProcessing(true);
    
    const uploadPromise = docService.uploadDocs(stagedFiles);

    toast.promise(uploadPromise, {
      loading: "Analyse des documents en cours...",
      success: (data) => {
        onUploadComplete(data);
        setStagedFiles([]);
        return `${data.length} document(s) analysé(s) avec succès !`;
      },
      error: "Erreur lors de l'analyse des documents.",
    });

    try {
      await uploadPromise;
    } catch (error) {
      console.error("Erreur lors de l'upload réel", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div className="space-y-4 w-full">
      {/* Zone de Drop */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer
          ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-blue-300 bg-white"}`}
      >
        <input {...getInputProps()} />
        <UploadCloud className="mx-auto text-gray-400 mb-2" size={32} />
        <p className="text-sm font-medium text-gray-600">
          Glissez vos fichiers ou{" "}
          <span className="text-blue-600">cliquez ici</span>
        </p>
      </div>

      {/* Liste de prévisualisation (Staging) */}
      {stagedFiles.length > 0 && (
        <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
          <div className="p-3 bg-gray-50 border-b text-xs font-bold text-gray-500 uppercase flex justify-between">
            Fichiers en attente ({stagedFiles.length})
            <button
              onClick={() => setStagedFiles([])}
              className="hover:text-red-500"
            >
              Tout vider
            </button>
          </div>

          <ul className="divide-y max-h-60 overflow-y-auto">
            {stagedFiles.map((file, index) => (
              <li
                key={index}
                className="p-3 flex items-center justify-between group animate-in fade-in slide-in-from-top-1"
              >
                <div className="flex items-center gap-3">
                  <FileText className="text-blue-500" size={18} />
                  <div>
                    <p className="text-sm font-medium text-gray-700 truncate max-w-50">
                      {file.name}
                    </p>
                    <p className="text-[10px] text-gray-400">
                      {(file.size / 1024).toFixed(0)} KB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(file)}
                  className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
                >
                  <X size={16} />
                </button>
              </li>
            ))}
          </ul>

          {/* Bouton de validation final */}
          <div className="p-4 bg-gray-50 border-t">
            <button
              onClick={handleStartOCR}
              disabled={isProcessing}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-semibold flex items-center justify-center gap-2 hover:bg-blue-700 disabled:bg-gray-400 transition-all shadow-lg shadow-blue-100"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  Traitement IA en cours...
                </>
              ) : (
                <>
                  <Send size={18} />
                  Lancer l&apos;analyse automatique
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
