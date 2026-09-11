/* Dispositivos: conexão, câmera, fila de envio e vínculo com veículo e motorista. */
import { query } from "../api.js";
import { chip, deviceKind, h, severityMark } from "../dom.js";
import { relative } from "../format.js";
import { PENDING_FORMS, listPage } from "./list.js";

export default function devicesView(ctx) {
  return listPage(ctx, {
    title: "Dispositivos",
    lead: "Equipamentos instalados nos veículos. Aparecem offline depois de 3 minutos sem sinal.",
    endpoint: `/api/devices${query({ company_id: ctx.scopeId })}`,
    columns: [
      ["Agora", (device) => severityMark(deviceKind(device))],
      ["Dispositivo", (device) => h("span", null, h("span", { class: "row-main" }, device.name), h("span", { class: "row-sub mono" }, `${device.token_prefix}…`))],
      ["Veículo", (device) => (device.vehicle ? h("span", { class: "plate" }, device.vehicle.name) : "—")],
      ["Motorista", (device) => device.driver?.name || "—"],
      ctx.role === "admin" ? ["Empresa", (device) => device.company?.name || "—"] : null,
      ["Conexão", (device) => (device.revoked ? chip("revogado", "red") : device.online ? chip("online", "amber") : chip(device.last_seen_at ? `offline · ${relative(device.last_seen_at)}` : "nunca conectou"))],
      ["Câmera", (device) => (device.camera_ok === false ? chip("com problema", "red") : device.camera_ok ? "ok" : "—")],
      ["Versão", (device) => h("span", { class: "mono" }, device.software_version || "—")],
    ].filter(Boolean),
    empty: ["Nenhum dispositivo", "Os equipamentos cadastrados aparecem aqui."],
    note: PENDING_FORMS,
  });
}
