"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { bridge, type EventoScript, type ScriptEstado } from "@/lib/bridge";

// Spec 018: situação a cada 3 s e eventos novos a cada 2 s, só enquanto a tela está aberta.
export const ESTADO_MS = 3000;
export const EVENTOS_MS = 2000;

export interface ScriptLocalAoVivo {
  estado: ScriptEstado | null;
  erro: string | null;
  /** Mais novos primeiro. */
  eventos: EventoScript[];
  /** Ids que chegaram depois da primeira leitura (entram com animação). */
  novos: ReadonlySet<number>;
}

export function useScriptLocal(): ScriptLocalAoVivo {
  const [estado, setEstado] = useState<ScriptEstado | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [lista, setLista] = useState<EventoScript[]>([]);
  const [novos, setNovos] = useState<ReadonlySet<number>>(new Set());
  const ultimoId = useRef(0);
  const primeiraLeitura = useRef(true);

  useEffect(() => {
    let ativo = true;
    const lerEstado = async () => {
      const resposta = await bridge.script_estado();
      if (!ativo) return;
      if (resposta.ok) {
        setEstado(resposta.dados);
        setErro(null);
      } else {
        setErro(resposta.erro);
      }
    };
    void lerEstado();
    const relogio = window.setInterval(lerEstado, ESTADO_MS);
    return () => {
      ativo = false;
      window.clearInterval(relogio);
    };
  }, []);

  useEffect(() => {
    let ativo = true;
    let ocupado = false;
    const lerEventos = async () => {
      if (ocupado) return;
      ocupado = true;
      const resposta = await bridge.script_eventos(ultimoId.current);
      ocupado = false;
      if (!ativo || !resposta.ok) return;
      const chegaram = resposta.dados;
      const eraPrimeira = primeiraLeitura.current;
      primeiraLeitura.current = false;
      if (chegaram.length === 0) return;
      ultimoId.current = Math.max(ultimoId.current, ...chegaram.map((evento) => evento.id));
      setLista((antes) => [...antes, ...chegaram]);
      if (!eraPrimeira) setNovos((antes) => new Set([...antes, ...chegaram.map((evento) => evento.id)]));
    };
    void lerEventos();
    const relogio = window.setInterval(lerEventos, EVENTOS_MS);
    return () => {
      ativo = false;
      window.clearInterval(relogio);
    };
  }, []);

  const eventos = useMemo(
    () => [...lista].sort((a, b) => Date.parse(b.em) - Date.parse(a.em) || b.id - a.id),
    [lista],
  );

  return { estado, erro, eventos, novos };
}

/** Com o script aberto, só os eventos desta sessão; fechado, os últimos capturados. */
export function eventosVisiveis(estado: ScriptEstado | null, eventos: EventoScript[]): EventoScript[] {
  if (estado?.aberto && estado.desde) {
    const desde = Date.parse(estado.desde);
    return eventos.filter((evento) => Date.parse(evento.em) >= desde);
  }
  return eventos;
}
