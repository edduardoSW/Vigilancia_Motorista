// Spec 025 · alerta sonoro opcional do teste no navegador, gerado na hora pelo WebAudio (sem arquivo de som).
// Olhos fechados por 1 s: dois bipes uma vez. Por 3 s ou mais: três bipes, repetidos até o olho abrir.
import type { Estagio } from "./camera-sono";

const REPETE_MS = 1100;

export class AlertaSonoro {
  private ctx: AudioContext | null = null;
  private nivelTocado = 0;
  private ultimoToque = 0;
  private ligado = false; // o suspend() do navegador é assíncrono: a trava vale na hora

  /** Precisa vir de um clique: o navegador só libera o som depois de um gesto da pessoa. */
  async ligar(): Promise<void> {
    this.ctx ??= new AudioContext();
    await this.ctx.resume();
    this.ligado = true;
    this.bipes(1, 660, 0.09);
  }

  desligar(): void {
    this.ligado = false;
    this.nivelTocado = 0;
    void this.ctx?.suspend();
  }

  fechar(): void {
    void this.ctx?.close();
    this.ctx = null;
  }

  atualizar(estagio: Estagio, agoraMs: number): void {
    if (!this.ligado || !this.ctx || this.ctx.state !== "running") return;
    const nivel = estagio === "normal" ? 0 : estagio === "microssono" ? 1 : 2;
    if (nivel === 0) {
      this.nivelTocado = 0;
      return;
    }
    const subiu = nivel > this.nivelTocado;
    if (subiu || (nivel === 2 && agoraMs - this.ultimoToque >= REPETE_MS)) {
      this.nivelTocado = nivel;
      this.ultimoToque = agoraMs;
      if (nivel === 1) this.bipes(2, 740, 0.1);
      else this.bipes(3, 988, 0.12);
    }
  }

  private bipes(quantos: number, frequencia: number, duracao: number): void {
    const ctx = this.ctx;
    if (!ctx) return;
    const inicio = ctx.currentTime + 0.01;
    for (let i = 0; i < quantos; i++) {
      const comeco = inicio + i * (duracao + 0.07);
      const oscilador = ctx.createOscillator();
      const volume = ctx.createGain();
      oscilador.type = "triangle";
      oscilador.frequency.value = frequencia;
      // Subida e descida curtas: sem estalo no começo e no fim do bipe.
      volume.gain.setValueAtTime(0, comeco);
      volume.gain.linearRampToValueAtTime(0.22, comeco + 0.012);
      volume.gain.setValueAtTime(0.22, comeco + duracao - 0.02);
      volume.gain.linearRampToValueAtTime(0, comeco + duracao);
      oscilador.connect(volume).connect(ctx.destination);
      oscilador.start(comeco);
      oscilador.stop(comeco + duracao + 0.01);
    }
  }
}
