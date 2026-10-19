import type { Metadata } from "next";
import { RemoteScreen } from "@/components/remote/remote-screen";

export const metadata: Metadata = { title: "Testes à distância · RotaGuard" };

// Testes à distância (spec 026): sessões, eventos e trechos que o RotaGuard Teste de outros computadores mandou para a
// central e este painel já baixou. A tela conversa com o Python pela `bridge`.
export default function RemotosPage() {
  return <RemoteScreen />;
}
