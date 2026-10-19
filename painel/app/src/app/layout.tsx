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
  description: "Painel da empresa: testes, motoristas, veículos e caixas.",
  robots: { index: false, follow: false },
};

// Spec 025 (CAM-11): só o próprio painel recebe conexões (connect-src 'self'), então nada sai do aparelho, nem a
// telemetria do MediaPipe. 'wasm-unsafe-eval' compila o WASM sem liberar eval de JavaScript. É a mesma política do
// Caddy no /painel da VPS, menos frame-ancestors (não vale em meta). O export estático não manda cabeçalho, por isso
// a meta vale também no painel instalado. Uma linha só: o teste confere diretiva por diretiva.
const POLITICA_DE_CONTEUDO =
  "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; worker-src 'self' blob:; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'";
// No next dev o React usa eval para mostrar a pilha dos erros (docs do Next, content-security-policy.md).
const politica =
  process.env.NODE_ENV === "development" ? POLITICA_DE_CONTEUDO.replace("'wasm-unsafe-eval'", "'wasm-unsafe-eval' 'unsafe-eval'") : POLITICA_DE_CONTEUDO;

// Janela do app (specs 013 e 014): ativar ou entrar primeiro; depois o menu à esquerda e o conteúdo à direita.
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${texto.variable} ${titulo.variable}`}>
      <head>
        <meta httpEquiv="Content-Security-Policy" content={politica} />
      </head>
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
