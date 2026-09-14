import type { Metadata } from "next";
import { Manrope, Space_Grotesk } from "next/font/google";
import { AuthGate } from "@/components/auth-gate";
import { DecisionsProvider } from "@/components/decisions-provider";
import { SessionProvider } from "@/components/session-provider";
import { ToastProvider } from "@/components/ui/toast";
import "./globals.css";

// Mesma tipografia do site: Space Grotesk nos títulos e Manrope no texto.
const texto = Manrope({ subsets: ["latin"], variable: "--fonte-texto", display: "swap" });
const titulo = Space_Grotesk({ subsets: ["latin"], variable: "--fonte-titulo", display: "swap" });

export const metadata: Metadata = {
  title: "RotaGuard",
  description: "Painel da empresa (prévia com dados fictícios).",
  robots: { index: false, follow: false },
};

// Janela do app (specs 013 e 014): ativar ou entrar primeiro; depois o menu à esquerda e o conteúdo à direita.
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${texto.variable} ${titulo.variable}`}>
      <body>
        <SessionProvider>
          <ToastProvider>
            <DecisionsProvider>
              <AuthGate>{children}</AuthGate>
            </DecisionsProvider>
          </ToastProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
