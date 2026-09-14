// Ícones de traço fino do painel parte 2, no mesmo desenho de components/icons.tsx. Usados com moderação: menu, busca e
// ações; nada de ícone em toda linha de tabela.
const paths = {
  home: "M4 11 12 4.5l8 6.5v9h-5.5v-5.5h-5V20H4v-9Z",
  trips: "M8 4v16M16 4v3m0 4.5v1m0 4.5v3",
  driver: "M12 11.5a3.8 3.8 0 1 0 0-7.6 3.8 3.8 0 0 0 0 7.6ZM5 20c.9-3.3 3.6-5 7-5s6.1 1.7 7 5",
  vehicle: "M6 3.5h12V18H6V3.5Zm0 9.5h12M9.5 15.8h.01m4.99 0h.01M8 18v2.5m8-2.5v2.5M9 6.5h6",
  team: "M9 11a3.3 3.3 0 1 0 0-6.6A3.3 3.3 0 0 0 9 11Zm-6 8.5c.7-2.9 3-4.4 6-4.4s5.3 1.5 6 4.4M15.5 4.6a3.3 3.3 0 0 1 0 6.3m2.4 4.5c1.6.6 2.7 1.9 3.1 4.1",
  settings: "M4 7h9m4 0h3M4 17h3m4 0h9M15 4.5v5M9 14.5v5",
  book: "M5 5a2 2 0 0 1 2-2h12v15H7a2 2 0 0 0-2 2V5Zm0 15a2 2 0 0 0 2 2h12v-4",
  search: "M10.5 17.5a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm5-2 4.5 4.5",
  lock: "M6 10.5h12V20H6v-9.5Zm2.5 0V8a3.5 3.5 0 0 1 7 0v2.5",
  close: "M6.5 6.5l11 11m0-11-11 11",
  file: "M6.5 3h7.5l4 4v14H6.5V3Zm7.5 0v4h4",
  arrow: "M5 12h14m-5-5 5 5-5 5",
  check: "m5 12.5 4.2 4.2L19 7",
  live: "M12 12h.01M8.6 8.6a4.8 4.8 0 0 0 0 6.8m6.8-6.8a4.8 4.8 0 0 1 0 6.8M5.8 5.8a8.8 8.8 0 0 0 0 12.4m12.4-12.4a8.8 8.8 0 0 1 0 12.4",
  box: "M4 7.5 12 3l8 4.5v9L12 21l-8-4.5v-9Zm0 0 8 4.5m0 0 8-4.5M12 12v9",
  exit: "M14 4h5v16h-5M10 8l-4 4 4 4m-4-4h10",
} as const;

export type GlyphName = keyof typeof paths;

export function Glyph({ name, size = 18, stroke = 1.6, className = "" }: { name: GlyphName; size?: number; stroke?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d={paths[name]} stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
