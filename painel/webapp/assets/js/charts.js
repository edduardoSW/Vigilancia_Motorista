/* Gráficos em SVG feitos à mão. Altura e forma carregam o nível; a cor só reforça. */
import { h, s } from "./dom.js";

const LEVEL_TEXT = ["sem alerta", "atenção", "alto", "crítico"];

function describeHours(hours) {
  const strong = hours.map((level, hour) => [level, hour]).filter(([level]) => level >= 2);
  if (!strong.length) return hours.some((level) => level === 1) ? "só alertas de atenção" : "sem alertas";
  return strong.map(([level, hour]) => `${LEVEL_TEXT[level]} às ${hour}h`).join(", ");
}

/** Nível do evento (1 a 5, vindo do servidor) na escala da faixa: 1 atenção, 2 alto, 3 crítico. */
export function stripLevel(risk) {
  if (risk >= 4) return 3;
  if (risk >= 3) return 2;
  return risk >= 1 ? 1 : 0;
}

/** 24 barras: pior evento em cada hora do dia. `hours` vem do servidor com o nível do evento (0 a 5). */
export function hourStrip(hours, { now = null, label = "Pior nível de risco por hora", size = "small" } = {}) {
  const height = size === "large" ? 44 : 18;
  const levels = hours.map(stripLevel);
  const svg = s("svg", {
    viewBox: `0 0 240 ${height + 12}`, class: `hour-strip hour-strip-${size}`, role: "img",
    "aria-label": `${label}: ${describeHours(levels)}.`,
  });
  levels.forEach((level, hour) => {
    const bar = level === 0 ? 2 : Math.round(height * (0.3 + (0.7 * level) / 3));
    const rect = s("rect", {
      x: hour * 10 + 1, y: height - bar, width: 8, height: bar, rx: 1,
      class: `bar bar-${level}${hour === now ? " bar-now" : ""}`,
    });
    rect.append(s("title", null, `${String(hour).padStart(2, "0")}h — ${LEVEL_TEXT[level]}`));
    svg.append(rect);
  });
  const ticks = size === "large" ? [0, 3, 6, 9, 12, 15, 18, 21] : [0, 6, 12, 18];
  for (const tick of ticks) svg.append(s("text", { x: tick * 10 + 1, y: height + 10, class: "tick" }, `${tick}h`));
  return svg;
}

const SEGMENTS = [
  ["drowsiness", "seg-drowsy", "sonolência"],
  ["phone", "seg-phone", "celular"],
  ["other", "seg-other", "outros"],
];

/** Alertas por dia, empilhados por categoria; losango em cima do dia com alerta alto ou crítico. */
export function trendChart(days, dayLabel) {
  const width = days.length * 12;
  const height = 72;
  const max = Math.max(1, ...days.map((day) => day.drowsiness + day.phone + day.other));
  const total = days.reduce((sum, day) => sum + day.drowsiness + day.phone + day.other, 0);
  const svg = s("svg", {
    viewBox: `0 -8 ${width} ${height + 22}`, class: "trend-chart", role: "img",
    "aria-label": `Alertas por dia nos últimos ${days.length} dias: ${total} no total.`,
  });
  svg.append(s("line", { x1: 0, x2: width, y1: height + 0.5, y2: height + 0.5, class: "axis" }));
  days.forEach((day, index) => {
    const group = s("g", null);
    let top = height;
    for (const [key, className] of SEGMENTS) {
      const value = day[key];
      if (!value) continue;
      const barHeight = Math.max(2, (value / max) * (height - 8));
      top -= barHeight;
      group.append(s("rect", { x: index * 12 + 2, y: top, width: 8, height: barHeight, class: className }));
    }
    if (day.worst_risk >= 3) {
      const x = index * 12 + 6;
      group.append(s("path", { d: `M${x} ${top - 8} l3 3 -3 3 -3 -3z`, class: "seg-peak" }));
    }
    group.append(s("title", null,
      `${dayLabel(day.day)}: ${day.drowsiness} de sonolência, ${day.phone} de celular, ${day.other} outros`));
    svg.append(group);
    if (index % 7 === 0) svg.append(s("text", { x: index * 12 + 1, y: height + 12, class: "tick" }, dayLabel(day.day)));
  });
  const legend = h("ul", { class: "legend" },
    SEGMENTS.map(([, className, text]) => h("li", null, h("span", { class: `legend-swatch ${className}`, "aria-hidden": "true" }), text)),
    h("li", null, h("span", { class: "legend-peak", "aria-hidden": "true" }), "dia com alerta alto ou crítico"));
  return h("figure", { class: "trend" }, svg, legend);
}

/** Linha da abertura dos olhos e degraus do nível de risco nos últimos N segundos (modo teste). */
export class LiveChart {
  constructor(seconds = 60) {
    this.seconds = seconds;
    this.samples = [];
    this.marks = [];
    this.openLine = s("path", { class: "line-open" });
    this.riskLine = s("path", { class: "line-risk" });
    this.markGroup = s("g", { class: "mark-lines" });
    this.svg = s("svg", {
      viewBox: "0 0 600 180", class: "live-chart", role: "img",
      "aria-label": `Abertura dos olhos e nível de risco nos últimos ${seconds} segundos`,
    },
    s("line", { x1: 0, x2: 600, y1: 40.5, y2: 40.5, class: "grid" }),
    s("line", { x1: 0, x2: 600, y1: 90.5, y2: 90.5, class: "grid grid-dash" }),
    s("line", { x1: 0, x2: 600, y1: 140.5, y2: 140.5, class: "grid" }),
    s("text", { x: 4, y: 34, class: "tick" }, "aberto"),
    s("text", { x: 4, y: 134, class: "tick" }, "fechado"),
    s("text", { x: 4, y: 162, class: "tick" }, "risco"),
    this.markGroup, this.openLine, this.riskLine);
  }

  push(t, openness, risk) {
    this.samples.push([t, openness, risk]);
    const oldest = t - this.seconds;
    while (this.samples.length && this.samples[0][0] < oldest) this.samples.shift();
    while (this.marks.length && this.marks[0] < oldest) this.marks.shift();
    this.draw(t);
  }

  mark(t) {
    this.marks.push(t);
  }

  draw(now) {
    const x = (t) => (600 - ((now - t) / this.seconds) * 600).toFixed(1);
    let open = "";
    let penDown = false;
    let risk = "";
    for (const [t, openness, level] of this.samples) {
      if (openness === null || openness === undefined) {
        penDown = false;
      } else {
        const y = (140 - Math.max(0, Math.min(1.2, openness)) * 100).toFixed(1);
        open += `${penDown ? "L" : "M"}${x(t)} ${y}`;
        penDown = true;
      }
      const riskY = 174 - Math.max(0, Math.min(3, level || 0)) * 8;
      risk += risk ? `H${x(t)}V${riskY}` : `M${x(t)} ${riskY}`;
    }
    this.openLine.setAttribute("d", open);
    this.riskLine.setAttribute("d", risk);
    this.markGroup.replaceChildren(...this.marks.map((t) => s("line", { x1: x(t), x2: x(t), y1: 30, y2: 146, class: "mark-line" })));
  }
}

/** Barra horizontal com valor e marcas de referência. Retorna o elemento com .update(valor). */
export function meter({ label, max = 1, format = (value) => String(value), marks = [] }) {
  const fill = h("span", { class: "meter-fill" });
  const valueText = h("span", { class: "meter-value" }, "—");
  const track = h("span", { class: "meter-track", role: "meter", "aria-valuemin": "0", "aria-valuemax": String(max), "aria-label": label },
    fill,
    marks.map((mark) => {
      const tick = h("span", { class: "meter-mark", title: mark.label });
      tick.style.setProperty("--at", `${Math.min(100, (mark.value / max) * 100)}%`);
      return tick;
    }));
  const root = h("div", { class: "meter" }, h("span", { class: "meter-label" }, label), valueText, track);
  root.update = (value) => {
    if (value === null || value === undefined || Number.isNaN(value)) {
      fill.style.setProperty("--value", "0%");
      valueText.textContent = "—";
      track.removeAttribute("aria-valuenow");
      return;
    }
    const ratio = Math.max(0, Math.min(1, value / max));
    fill.style.setProperty("--value", `${(ratio * 100).toFixed(1)}%`);
    valueText.textContent = format(value);
    track.setAttribute("aria-valuenow", String(value));
  };
  return root;
}

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

/** Troca um número contando até o novo valor (sem animação se o sistema pedir menos movimento). */
export function setNumber(element, value) {
  const target = Number(value) || 0;
  const from = element.dataset.value === undefined ? target : Number(element.dataset.value);
  element.dataset.value = String(target);
  if (from === target || reducedMotion.matches) {
    element.textContent = String(target);
    return;
  }
  const start = performance.now();
  const duration = 520;
  const step = (now) => {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - (1 - progress) ** 4;
    element.textContent = String(Math.round(from + (target - from) * eased));
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
  element.classList.remove("is-bumped");
  void element.offsetWidth;
  element.classList.add("is-bumped");
}
