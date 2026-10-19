import type { Metadata } from "next";
import { Suspense } from "react";
import { SettingsScreen } from "@/components/settings/settings-screen";

export const metadata: Metadata = { title: "Configurações · RotaGuard" };

// A seção abre por ?secao= (o Início leva direto à seção certa); no export estático, useSearchParams precisa de Suspense.
export default function SettingsPage() {
  return (
    <Suspense fallback={<section className="px-14 pt-[34px] font-titulo text-[30px] font-semibold">Configurações</section>}>
      <SettingsScreen />
    </Suspense>
  );
}
