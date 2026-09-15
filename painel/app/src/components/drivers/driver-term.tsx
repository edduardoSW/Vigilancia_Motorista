"use client";

import Image from "next/image";
import { useEffect, useState, type FormEvent } from "react";
import { Field } from "@/components/ui/field";
import { Glyph } from "@/components/ui/glyph";
import { useToast } from "@/components/ui/toast";
import { bridge, type Motorista, type TermoRegistro } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import {
  conteudoBase64,
  fraseDoTermo,
  hojeIso,
  registroDoTermo,
  tamanhoArquivo,
  TERMO_ACEITA,
  validarArquivoTermo,
  validarDataTermo,
} from "@/lib/validators";
import { dadosDoMotorista } from "./driver-data";

// Termo de ciência dentro dos dados do motorista (spec 019, decisão 5). A situação vem em frase; quem pode cadastrar
// importa o termo assinado, vê o arquivo, abre o histórico e registra a revogação, tudo em trechos desta mesma janela
// (nada de janela dentro de janela). Nada é apagado: trocar o arquivo e revogar criam registro novo (TER-03).

type Trecho = "importar" | "ver" | "historico" | "revogar";

export function DriverTerm({
  motorista,
  podeCadastrar,
  destacar,
  onChanged,
}: {
  motorista: Motorista;
  podeCadastrar: boolean;
  /** Logo depois do cadastro novo: o botão de importar recebe o foco. */
  destacar: boolean;
  onChanged: (motorista: Motorista) => void;
}) {
  const { toast } = useToast();
  const [trecho, setTrecho] = useState<Trecho | null>(null);
  const [foto, setFoto] = useState<{ nome: string; conteudo: string } | null>(null);
  const [abrindo, setAbrindo] = useState(false);
  const { termo } = motorista;
  const frase = fraseDoTermo(termo);
  const temArquivo = termo.assinado && termo.arquivo !== null;
  const alternar = (qual: Trecho) => setTrecho((atual) => (atual === qual ? null : qual));

  // Foto aparece aqui dentro; PDF abre no leitor do computador (o Python abre e avisa); erro vira aviso com a frase da ponte.
  async function verTermo() {
    if (trecho === "ver") {
      setTrecho(null);
      return;
    }
    setAbrindo(true);
    const resposta = await bridge.termo_ver(motorista.id);
    setAbrindo(false);
    if (!resposta.ok) {
      toast({ text: resposta.erro });
      return;
    }
    if (resposta.dados.tipo === "pdf") {
      toast({ text: `O termo de ${motorista.nome_curto} abriu no leitor de PDF do computador.` });
      return;
    }
    setFoto({ nome: resposta.dados.nome, conteudo: resposta.dados.conteudo });
    setTrecho("ver");
  }

  function aoImportar(salvo: Motorista) {
    setTrecho(null);
    onChanged(salvo);
    toast({ text: `Termo de ${salvo.nome_curto} importado` });
  }

  function aoRevogar(salvo: Motorista) {
    setTrecho(null);
    onChanged(salvo);
    toast({ text: `Revogação registrada. Os vídeos de ${salvo.nome_curto} ficam trancados.` });
  }

  return (
    <div>
      <p className={cn("break-words text-[14px]", frase.alarme && "font-semibold text-alarme")}>{frase.texto}</p>

      {podeCadastrar && (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={cn("btn btn-small", !termo.assinado && "btn-primary")}
              aria-expanded={trecho === "importar"}
              autoFocus={destacar}
              onClick={() => alternar("importar")}
            >
              <Glyph name="upload" size={16} />
              {temArquivo ? "Trocar arquivo" : "Importar termo assinado"}
            </button>
            {temArquivo && (
              <button type="button" className="btn btn-small" aria-expanded={trecho === "ver"} disabled={abrindo} onClick={verTermo}>
                {abrindo ? "Abrindo…" : "Ver termo"}
              </button>
            )}
            <button type="button" className="btn btn-small" aria-expanded={trecho === "historico"} onClick={() => alternar("historico")}>
              Histórico do termo
            </button>
            {termo.assinado && (
              <button
                type="button"
                className="btn btn-small btn-quiet ml-auto text-grafite hover:text-tinta"
                aria-expanded={trecho === "revogar"}
                onClick={() => alternar("revogar")}
              >
                Registrar que revogou
              </button>
            )}
          </div>

          {trecho === "importar" && <TermImport motorista={motorista} onCancel={() => setTrecho(null)} onImported={aoImportar} />}

          {trecho === "ver" && foto && (
            <figure className="anim-enter mt-4">
              <div className="relative h-[420px] overflow-hidden rounded-[10px] border border-fio bg-superficie">
                <Image src={foto.conteudo} alt={`Termo assinado de ${motorista.nome}`} fill unoptimized sizes="560px" className="object-contain" />
              </div>
              <figcaption className="mt-1.5 break-words text-[13px] text-grafite">{foto.nome}</figcaption>
            </figure>
          )}

          {trecho === "historico" && <TermHistory motoristaId={motorista.id} />}

          {trecho === "revogar" && <TermRevoke motorista={motorista} onCancel={() => setTrecho(null)} onRevoked={aoRevogar} />}
        </>
      )}
    </div>
  );
}

function lerComoDataUrl(arquivo: File) {
  return new Promise<string>((resolve, reject) => {
    const leitor = new FileReader();
    leitor.onload = () => resolve(typeof leitor.result === "string" ? leitor.result : "");
    leitor.onerror = () => reject(leitor.error);
    leitor.readAsDataURL(arquivo);
  });
}

type ErrosImportar = { arquivo?: string; data?: string; geral?: string };

/** Trecho "Importar termo assinado": arquivo, data da assinatura e versão, na própria janela do motorista. */
function TermImport({ motorista, onCancel, onImported }: { motorista: Motorista; onCancel: () => void; onImported: (motorista: Motorista) => void }) {
  const { termo } = motorista;
  const [arquivo, setArquivo] = useState<File | null>(null);
  // Trocar o arquivo de um termo já registrado começa com a mesma data e versão.
  const [data, setData] = useState(termo.assinado ? (termo.data ?? "") : "");
  const [versao, setVersao] = useState(termo.versao ?? "1");
  const [erros, setErros] = useState<ErrosImportar>({});
  const [enviando, setEnviando] = useState(false);
  const hoje = hojeIso();
  const id = (campo: "arquivo" | "data" | "versao") => `termo-${motorista.id}-${campo}`;

  const intro = !termo.assinado
    ? `Com o termo importado, os vídeos das viagens de ${motorista.nome_curto} deixam de ficar trancados.`
    : termo.arquivo
      ? "O arquivo de agora continua guardado no histórico do termo."
      : "O arquivo fica guardado como comprovante do termo já registrado.";

  async function importar(evento: FormEvent) {
    evento.preventDefault();
    const erroArquivo = validarArquivoTermo(arquivo ? { nome: arquivo.name, bytes: arquivo.size } : null) ?? undefined;
    const erroData = validarDataTermo(data, hoje) ?? undefined;
    if (!arquivo || erroArquivo || erroData) {
      setErros({ arquivo: erroArquivo, data: erroData });
      document.getElementById(id(erroArquivo ? "arquivo" : "data"))?.focus();
      return;
    }
    setErros({});
    setEnviando(true);
    let conteudo: string;
    try {
      conteudo = conteudoBase64(await lerComoDataUrl(arquivo));
    } catch {
      setEnviando(false);
      setErros({ arquivo: "Não deu para ler o arquivo. Escolha de novo." });
      return;
    }
    const resposta = await bridge.termo_importar(motorista.id, { nome: arquivo.name, conteudo_base64: conteudo }, { data, versao: versao.trim() || null });
    setEnviando(false);
    if (!resposta.ok) {
      // O erro volta no campo certo; nada foi gravado, então a lista fica como está.
      if (resposta.campo === "arquivo") setErros({ arquivo: resposta.erro });
      else if (resposta.campo === "data") setErros({ data: resposta.erro });
      else setErros({ geral: resposta.erro });
      if (resposta.campo === "arquivo" || resposta.campo === "data") document.getElementById(id(resposta.campo))?.focus();
      return;
    }
    onImported(resposta.dados);
  }

  return (
    <form onSubmit={importar} noValidate aria-label="Importar termo assinado" className="anim-enter mt-4 rounded-[10px] border border-fio bg-superficie p-4">
      <p className="mb-4 text-[13.5px] text-grafite">{intro}</p>

      <Field label="Arquivo do termo" htmlFor={id("arquivo")} hint="PDF ou foto (PNG ou JPEG), até 10 MB." error={erros.arquivo}>
        <div className="flex min-w-0 items-center gap-3">
          <input
            id={id("arquivo")}
            type="file"
            accept={TERMO_ACEITA}
            autoFocus
            aria-invalid={Boolean(erros.arquivo)}
            className="peer sr-only"
            onChange={(evento) => {
              setArquivo(evento.target.files?.[0] ?? null);
              setErros((atual) => ({ ...atual, arquivo: undefined, geral: undefined }));
            }}
          />
          <label
            htmlFor={id("arquivo")}
            className="btn btn-small shrink-0 cursor-pointer peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-verde"
          >
            Escolher arquivo
          </label>
          <span className={cn("min-w-0 truncate text-[13.5px]", !arquivo && "text-grafite")}>
            {arquivo ? `${arquivo.name} (${tamanhoArquivo(arquivo.size)})` : "Nenhum arquivo escolhido"}
          </span>
        </div>
      </Field>

      <div className="grid grid-cols-2 gap-x-4">
        <Field label="Assinado em" htmlFor={id("data")} error={erros.data}>
          <input
            id={id("data")}
            type="date"
            className="input"
            value={data}
            max={hoje}
            aria-invalid={Boolean(erros.data)}
            onChange={(evento) => {
              setData(evento.target.value);
              setErros((atual) => ({ ...atual, data: undefined, geral: undefined }));
            }}
          />
        </Field>
        <Field label="Versão do termo" htmlFor={id("versao")} hint="Se não souber, deixe 1.">
          <input id={id("versao")} className="input" value={versao} maxLength={20} autoComplete="off" onChange={(evento) => setVersao(evento.target.value)} />
        </Field>
      </div>

      {erros.geral && (
        <p role="alert" className="mb-3 text-[13.5px] font-semibold text-alarme">
          {erros.geral}
        </p>
      )}

      <div className="flex gap-2">
        <button type="submit" className="btn btn-small btn-primary" disabled={enviando}>
          {enviando ? "Importando…" : "Importar"}
        </button>
        <button type="button" className="btn btn-small" disabled={enviando} onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

/** Trecho "Histórico do termo": todos os registros, do mais novo para o mais antigo. Sem apagar. */
function TermHistory({ motoristaId }: { motoristaId: number }) {
  const [registros, setRegistros] = useState<TermoRegistro[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    bridge.motorista_termos(motoristaId).then((resposta) => {
      if (!vivo) return;
      if (resposta.ok) setRegistros(resposta.dados);
      else setErro(resposta.erro);
    });
    return () => {
      vivo = false;
    };
  }, [motoristaId]);

  return (
    <div className="anim-enter mt-4 rounded-[10px] border border-fio bg-superficie">
      {erro ? (
        <p role="alert" className="px-4 py-3 text-[14px] text-alarme">
          {erro}
        </p>
      ) : registros === null ? (
        <p className="px-4 py-3 text-[14px] text-grafite">Carregando o histórico…</p>
      ) : registros.length === 0 ? (
        <p className="px-4 py-3 text-[14px] text-grafite">Nenhum termo registrado ainda.</p>
      ) : (
        <>
          <p className="px-4 pt-3 text-[13px] text-grafite">Do mais novo para o mais antigo. Nada é apagado.</p>
          <ol aria-label="Histórico do termo" className="divide-y divide-fio">
            {registros.map((registro) => {
              const linha = registroDoTermo(registro);
              return (
                <li key={registro.id} className="anim-row px-4 py-3 text-[14px]">
                  <b className="block font-semibold">{linha.titulo}</b>
                  <span className={cn("block break-words", !registro.arquivo && "text-grafite")}>{linha.arquivo}</span>
                  <span className="block text-[13px] text-grafite">{linha.quem}</span>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </div>
  );
}

/** Trecho "Registrar que revogou": confirmação e registro novo de termo não assinado (o anterior fica no histórico). */
function TermRevoke({ motorista, onCancel, onRevoked }: { motorista: Motorista; onCancel: () => void; onRevoked: (motorista: Motorista) => void }) {
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function revogar() {
    setEnviando(true);
    setErro(null);
    const resposta = await bridge.motorista_salvar({ ...dadosDoMotorista(motorista), termo: { assinado: false, data: null, versao: null } });
    setEnviando(false);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }
    onRevoked(resposta.dados);
  }

  return (
    <div className="anim-enter mt-4 grid gap-3 rounded-[10px] border border-fio bg-superficie p-4">
      <p className="text-[14px]">
        Registrar que {motorista.nome_curto} revogou o termo? Os vídeos das viagens voltam a ficar trancados. O histórico continua guardado.
      </p>
      {erro && (
        <p role="alert" className="text-[13.5px] font-semibold text-alarme">
          {erro}
        </p>
      )}
      <div className="flex gap-2">
        <button type="button" className="btn btn-small border-alarme text-alarme" disabled={enviando} onClick={revogar}>
          {enviando ? "Registrando…" : "Registrar que revogou"}
        </button>
        <button type="button" className="btn btn-small" disabled={enviando} onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
