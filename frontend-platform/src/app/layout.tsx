import './globals.css';
import { LayoutDashboard, ShieldCheck, FileText } from 'lucide-react';
import Link from 'next/link';
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});


export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={cn("font-sans", geist.variable)}>
      <body className="flex h-screen bg-gray-50 text-gray-900">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r flex flex-col">
          <div className="p-6 font-bold text-xl text-blue-600 flex items-center gap-2">
            <ShieldCheck size={28} /> AI-Audit
          </div>
          <nav className="flex-1 px-4 space-y-2">
            <Link href="/" className="flex items-center gap-3 p-3 hover:bg-blue-50 rounded-lg transition-colors">
              <LayoutDashboard size={20} /> Dashboard
            </Link>
            <Link href="/conformite" className="flex items-center gap-3 p-3 hover:bg-blue-50 rounded-lg transition-colors">
              <ShieldCheck size={20} /> Conformité
            </Link>
            <Link href="/crm" className="flex items-center gap-3 p-3 hover:bg-blue-50 rounded-lg transition-colors">
              <FileText size={20} /> Espace Métier
            </Link>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </body>
    </html>
  );
}