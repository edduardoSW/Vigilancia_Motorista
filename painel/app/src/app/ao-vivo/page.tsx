import type { Metadata } from "next";
import { LiveScreen } from "@/components/live/live-screen";

export const metadata: Metadata = { title: "Teste neste computador · RotaGuard" };

// Spec 018: o script da caixa rodando neste computador aparece aqui sozinho, com os eventos que ele registrar.
export default function LivePage() {
  return <LiveScreen />;
}
