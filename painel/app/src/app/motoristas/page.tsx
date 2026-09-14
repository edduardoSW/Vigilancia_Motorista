import type { Metadata } from "next";
import { DriversScreen } from "@/components/drivers/drivers-screen";

export const metadata: Metadata = { title: "Motoristas · RotaGuard" };

// Motoristas (spec 015): a tela conversa com o Python pela `bridge`, por isso fica num componente de cliente.
export default function DriversPage() {
  return <DriversScreen />;
}
