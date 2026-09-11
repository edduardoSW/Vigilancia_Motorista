// Marca provisória: o nome em Sofia Sans Extra Condensed com uma barra de escala gráfica (a convenção dos mapas),
// que é o recurso estrutural do site. Trocar quando houver símbolo definitivo.
export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className ?? ""}`}>
      <svg viewBox="0 0 30 8" className="h-[0.42em] w-auto" aria-hidden="true" focusable="false">
        <rect x="0.5" y="0.5" width="29" height="7" fill="none" stroke="currentColor" />
        <rect x="0.5" y="0.5" width="7.25" height="7" fill="currentColor" />
        <rect x="15" y="0.5" width="7.25" height="7" fill="currentColor" />
      </svg>
      <span className="font-titulo text-[1.7em] leading-none font-extrabold tracking-[-0.01em]">RotaGuard</span>
    </span>
  );
}
