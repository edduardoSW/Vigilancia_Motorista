/* Tempo real: um WebSocket por aba, com reconexão. O servidor só manda o que o perfil logado pode ver.
   No modo local não há WebSocket: os avisos vêm de local/bus.js (esta aba e as outras do mesmo navegador). */
import { IS_LOCAL } from "./config.js";

const MAX_RETRY_S = 30;
const PING_EVERY_MS = 25000;

class LiveConnection {
  constructor() {
    this.handlers = new Map();
    this.status = "desligado";
    this.socket = null;
    this.attempt = 0;
    this.stopped = true;
    this.retryTimer = null;
    this.pingTimer = null;
    window.addEventListener("online", () => this.reconnectNow());
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") this.reconnectNow();
    });
  }

  start() {
    this.stopped = false;
    if (IS_LOCAL) {
      this.startLocal();
      return;
    }
    if (!this.socket) this.open();
  }

  async startLocal() {
    if (this.unsubscribe) return;
    const { subscribe } = await import("./local/bus.js");
    if (this.stopped || this.unsubscribe) return;
    this.unsubscribe = subscribe((message) => this.emit(message.type, message.data));
    this.setStatus("local");
  }

  stop() {
    this.stopped = true;
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
    clearTimeout(this.retryTimer);
    clearInterval(this.pingTimer);
    if (this.socket) {
      this.socket.onclose = null;
      this.socket.close();
      this.socket = null;
    }
    this.setStatus("desligado");
  }

  reconnectNow() {
    if (IS_LOCAL || this.stopped || this.socket) return;
    clearTimeout(this.retryTimer);
    this.open();
  }

  open() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${location.host}/ws`);
    this.socket = socket;
    this.setStatus(this.attempt ? "reconectando" : "conectando");
    socket.onopen = () => {
      this.attempt = 0;
      this.setStatus("ao_vivo");
      clearInterval(this.pingTimer);
      this.pingTimer = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) socket.send("ping");
      }, PING_EVERY_MS);
    };
    socket.onmessage = (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }
      if (message && typeof message.type === "string") this.emit(message.type, message.data);
    };
    socket.onerror = () => {
      // o onclose cuida da reconexão
    };
    socket.onclose = () => {
      clearInterval(this.pingTimer);
      this.socket = null;
      if (this.stopped) return;
      this.setStatus("reconectando");
      const base = Math.min(MAX_RETRY_S, 2 ** Math.min(this.attempt, 5));
      const delay = base * 1000 * (0.75 + Math.random() * 0.5);
      this.attempt += 1;
      this.retryTimer = setTimeout(() => this.open(), delay);
    };
  }

  setStatus(status) {
    this.status = status;
    this.emit("status", status);
  }

  on(type, handler) {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set());
    this.handlers.get(type).add(handler);
    return () => this.handlers.get(type)?.delete(handler);
  }

  emit(type, data) {
    for (const handler of this.handlers.get(type) || []) {
      try {
        handler(data);
      } catch (error) {
        console.error(error);
      }
    }
  }
}

export const live = new LiveConnection();
