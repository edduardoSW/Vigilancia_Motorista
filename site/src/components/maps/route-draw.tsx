"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useRef } from "react";

gsap.registerPlugin(ScrollTrigger, useGSAP);

/**
 * A rota se desenha uma vez, presa à rolagem da seção da viagem. Sem câmera, sem zoom, sem marcador andando.
 * Com movimento reduzido, a rota já aparece inteira.
 */
export function RouteDraw({ d }: { d: string }) {
  const caminho = useRef<SVGPathElement>(null);

  useGSAP(() => {
    const el = caminho.current;
    if (!el || !d) return;
    const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduzido) return;
    const comprimento = el.getTotalLength();
    gsap.set(el, { strokeDasharray: comprimento, strokeDashoffset: comprimento });
    gsap.to(el, {
      strokeDashoffset: 0,
      ease: "none",
      scrollTrigger: {
        trigger: el.closest("section") ?? el,
        start: "top 60%",
        end: "bottom 70%",
        scrub: 0.6,
      },
    });
  }, [d]);

  return (
    <path
      ref={caminho}
      d={d}
      fill="none"
      stroke="var(--c-asfalto)"
      strokeWidth="6"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  );
}
