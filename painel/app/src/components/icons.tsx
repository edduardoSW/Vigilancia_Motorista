// Ícones de traço fino, feitos à mão no mesmo desenho dos ícones do site (site/src/components/icons.tsx).
const paths = {
  box: "M4 7.5 12 3l8 4.5v9L12 21l-8-4.5v-9Zm0 0 8 4.5m0 0 8-4.5M12 12v9",
  check: "m5 12.5 4.2 4.2L19 7",
  bus: "M5 3h14v15H5V3Zm0 10h14M8 6h8M8 16h.01M16 16h.01M7 18v3m10-3v3",
  truck: "M2 5h12v13H2V5Zm12 5h4l4 5v3h-8M6 21a2 2 0 1 0 0-4 2 2 0 0 0 0 4m12 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4",
  print: "M6 9V3h12v6M6 17H4v-7h16v7h-2M7 14h10v7H7v-7Z",
} as const;

export type IconName = keyof typeof paths;

export function Icon({ name, size = 18, stroke = 1.6, className = "" }: { name: IconName; size?: number; stroke?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d={paths[name]} stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Marca do site (site/src/components/wordmark.tsx): escudo com a letra A e o nome em duas espessuras.
export function Wordmark() {
  return (
    <span className="inline-flex items-center gap-2.5 font-titulo text-[20px] font-semibold tracking-[-0.01em]">
      <svg width="22" height="24" viewBox="0 0 34 37" fill="none" aria-hidden="true">
        <path d="M17 2 31 8v12c0 7-14 15-14 15S3 27 3 20V8L17 2Z" stroke="currentColor" strokeWidth="2.4" />
        <path d="m10 25 5-14h5l4 14M12 20h10" stroke="currentColor" strokeWidth="2.8" strokeLinejoin="round" />
      </svg>
      <span>
        rota<span className="font-normal opacity-70">guard</span>
      </span>
    </span>
  );
}
