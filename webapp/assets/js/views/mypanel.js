/* Painel do motorista logado: a mesma página do motorista, só com os próprios dados. */
import { driverPage } from "./driver.js";

export default function myPanelView(ctx) {
  return driverPage(ctx, ctx.me.driver_id, { own: true });
}
