"use client";
import { FileText, ExternalLink, ZoomIn, ZoomOut } from 'lucide-react';
import { useState } from 'react';

interface Props {
  fileUrl?: string;
  filename?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DocumentViewer({ fileUrl, filename }: Props) {
  const [isLoading, setIsLoading] = useState(true);
  const fullUrl = fileUrl?.startsWith('/') ? `${API_BASE}${fileUrl}` : fileUrl;

  return (
    <div className="flex flex-col h-full bg-gray-100 border-r">
      {/* Barre d'outils du Viewer */}
      <div className="p-3 bg-white border-b flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-blue-50 rounded">
            <FileText size={18} className="text-blue-600" />
          </div>
          <span className="text-sm font-medium truncate max-w-50">
            {filename || "Aucun document sélectionné"}
          </span>
        </div>
        
        <div className="flex items-center gap-1">
          <button className="p-2 hover:bg-gray-100 rounded-md text-gray-500" title="Zoom In">
            <ZoomIn size={18} />
          </button>
          <button className="p-2 hover:bg-gray-100 rounded-md text-gray-500" title="Zoom Out">
            <ZoomOut size={18} />
          </button>
          <div className="w-px h-4 bg-gray-300 mx-1" />
          <a
            href={fullUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 hover:bg-gray-100 rounded-md text-gray-500"
          >
            <ExternalLink size={18} />
          </a>
        </div>
      </div>

      {/* Zone d'affichage du document */}
      <div className="flex-1 relative overflow-hidden">
        {fullUrl ? (
          <>
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-100 z-10">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-xs text-gray-500 font-medium">Chargement du document...</p>
                </div>
              </div>
            )}
            <iframe
              src={`${fullUrl}#toolbar=0`}
              className="w-full h-full border-none"
              onLoad={() => setIsLoading(false)}
              title="Afficheur de document"
            />
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
            <div className="p-6 border-2 border-dashed border-gray-300 rounded-full">
              <FileText size={48} strokeWidth={1} />
            </div>
            <p className="text-sm">Sélectionnez un document pour prévisualiser</p>
          </div>
        )}
      </div>
    </div>
  );
}