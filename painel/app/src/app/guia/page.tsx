import type { Metadata } from "next";
import { Suspense } from "react";
import { GuideScreen } from "@/components/guide/guide-screen";

export const metadata: Metadata = { title: "Guia de uso · RotaGuard" };

// O capítulo vem de ?capitulo=; no export estático, useSearchParams precisa de Suspense em volta.
export default function GuidePage() {
  return (
    <Suspense fallback={<section className="px-14 pt-[34px] font-titulo text-[34px] font-semibold">Guia de uso</section>}>
      <GuideScreen />
    </Suspense>
  );
}
