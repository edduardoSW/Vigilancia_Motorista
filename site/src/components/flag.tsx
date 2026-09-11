import type { FlagCode } from "@/content/idiomas";

// Bandeiras em SVG (o Windows não desenha bandeira em emoji). Proporção 3:2, simplificadas para 20–28 px.
function starPath(cx: number, cy: number, r: number, rotation = -90): string {
  const points: string[] = [];
  for (let i = 0; i < 10; i++) {
    const radius = i % 2 === 0 ? r : r * 0.382;
    const angle = ((rotation + i * 36) * Math.PI) / 180;
    points.push(`${(cx + radius * Math.cos(angle)).toFixed(2)},${(cy + radius * Math.sin(angle)).toFixed(2)}`);
  }
  return `M${points.join("L")}Z`;
}

function Brasil() {
  return (
    <>
      <rect width="30" height="20" fill="#009b3a" />
      <path d="M15 2.6 27.2 10 15 17.4 2.8 10Z" fill="#fedf00" />
      <circle cx="15" cy="10" r="4.6" fill="#002776" />
      <path d="M10.6 9.1c2.9-.5 6.3.1 8.8 1.8" stroke="#fff" strokeWidth="0.9" fill="none" />
    </>
  );
}

function EstadosUnidos() {
  const stripes = Array.from({ length: 13 }, (_, i) => i);
  const stars: [number, number][] = [];
  for (let row = 0; row < 4; row++) {
    for (let col = 0; col < 5; col++) stars.push([1.4 + col * 2.4 + (row % 2) * 1.2, 1.4 + row * 2.4]);
  }
  return (
    <>
      {stripes.map((i) => (
        <rect key={i} y={(i * 20) / 13} width="30" height={20 / 13 + 0.02} fill={i % 2 === 0 ? "#b22234" : "#fff"} />
      ))}
      <rect width="12" height={(20 / 13) * 7} fill="#3c3b6e" />
      {stars.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="0.45" fill="#fff" />
      ))}
    </>
  );
}

function Espanha() {
  return (
    <>
      <rect width="30" height="20" fill="#aa151b" />
      <rect y="5" width="30" height="10" fill="#f1bf00" />
    </>
  );
}

function Franca() {
  return (
    <>
      <rect width="10" height="20" fill="#002654" />
      <rect x="10" width="10" height="20" fill="#fff" />
      <rect x="20" width="10" height="20" fill="#ce1126" />
    </>
  );
}

function China() {
  return (
    <>
      <rect width="30" height="20" fill="#ee1c25" />
      <path d={starPath(5, 5, 3)} fill="#ffde00" />
      <path d={starPath(10, 2, 1, -52)} fill="#ffde00" />
      <path d={starPath(12, 4, 1, -30)} fill="#ffde00" />
      <path d={starPath(12, 7, 1, -90)} fill="#ffde00" />
      <path d={starPath(10, 9, 1, -52)} fill="#ffde00" />
    </>
  );
}

const flags: Record<FlagCode, () => React.ReactElement> = {
  br: Brasil,
  us: EstadosUnidos,
  es: Espanha,
  fr: Franca,
  cn: China,
};

export function Flag({ code, className }: { code: FlagCode; className?: string }) {
  const Desenho = flags[code];
  return (
    <svg viewBox="0 0 30 20" aria-hidden="true" focusable="false" className={className}>
      <Desenho />
      <rect width="30" height="20" fill="none" stroke="rgb(0 0 0 / 0.18)" strokeWidth="0.6" />
    </svg>
  );
}
