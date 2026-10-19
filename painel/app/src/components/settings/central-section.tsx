"use client";

import { useEffect, useState } from "react";
import { haQuanto, hora, statusDaCentral } from "@/components/remote/remote-data";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { SaveButton } from "@/components/ui/save-button";
import { useToast } from "@/components/ui/toast";
import { bridge, type CentralEstado, type CodigoPareamento } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { Row, Section, type SaveState } from "./section";

type Erro = { texto: string; campo?: string } | null;

// Configurações › Central (spec 026, decisão 7): o painel executável busca na central os testes feitos no RotaGuard Teste
// de outros computadores. Guarda só o token da sessão (no Windows, protegido pelo DPAPI); a senha nunca é gravada.
export function CentralSection() {
  const { toast } = useToast();
  const [estado, setEstadoBruto] = useState<CentralEstado | null>(null);
  const [agora, setAgora] = useState(() => Date.now());
  const [erroCarregar, setErroCarregar] = useState<string | null>(null);
  const [endereco, setEndereco] = useState("");
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [conectando, setConectando] = useState<SaveState>("idle");
  const [erro, setErro] = useState<Erro>(null);
  const [nomeComputador, setNomeComputador] = useState("");
  const [gerando, setGerando] = useState(false);
  const [codigo, setCodigo] = useState<CodigoPareamento | null>(null);
  const [erroCodigo, setErroCodigo] = useState<Erro>(null);
  const [confirmar, setConfirmar] = useState(false);
  const [saindo, setSaindo] = useState(false);

  function setEstado(novo: CentralEstado) {
    setEstadoBruto(novo);
    setAgora(Date.now());
  }

  useEffect(() => {
    let vivo = true;
    bridge.central_estado().then((resposta) => {
      if (!vivo) return;
      if (resposta.ok) {
        setEstado(resposta.dados);
        setEndereco(resposta.dados.endereco);
      } else setErroCarregar(resposta.erro);
    });
    return () => {
      vivo = false;
    };
  }, []);

  async function conectar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setConectando("saving");
    const resposta = await bridge.central_conectar(endereco.trim(), usuario.trim(), senha);
    setSenha(""); // a senha só passa pela ponte uma vez
    if (!resposta.ok) {
      setConectando("idle");
      setErro({ texto: resposta.erro, campo: resposta.campo });
      return;
    }
    setEstado(resposta.dados);
    setConectando("idle");
    setUsuario("");
    toast({ text: `Painel conectado à central${resposta.dados.empresa ? ` da ${resposta.dados.empresa.nome}` : ""}.` });
  }

  async function gerarCodigo(evento: React.FormEvent) {
    evento.preventDefault();
    setErroCodigo(null);
    setGerando(true);
    const resposta = await bridge.central_gerar_codigo(nomeComputador.trim() || null);
    setGerando(false);
    if (!resposta.ok) {
      setErroCodigo({ texto: resposta.erro, campo: resposta.campo });
      return;
    }
    setCodigo(resposta.dados);
    setNomeComputador("");
  }

  async function desconectar() {
    setSaindo(true);
    const resposta = await bridge.central_desconectar();
    setSaindo(false);
    setConfirmar(false);
    if (!resposta.ok) {
      toast({ text: resposta.erro });
      return;
    }
    setEstado(resposta.dados);
    setCodigo(null);
    toast({ text: "Painel desconectado da central. O que já foi baixado continua aqui." });
  }

  if (erroCarregar) {
    return (
      <Section title="Central" summary="Testes feitos em outros computadores.">
        <p role="alert" className="pt-5 text-[14px] text-alarme">
          {erroCarregar}
        </p>
      </Section>
    );
  }
  if (!estado) return <p className="text-[14px] text-grafite">Carregando…</p>;

  // Conectado e alcançando a central: a frase curta (quem e qual empresa ficam na linha de baixo); senão, o aviso inteiro.
  const status =
    estado.conectado && !estado.sem_conexao
      ? { texto: estado.ultima_busca ? `Recebendo · última busca ${haQuanto(estado.ultima_busca, agora)}` : "Recebendo · buscando pela primeira vez", alarme: false }
      : statusDaCentral(estado, agora);

  return (
    <Section
      title="Central"
      summary="Recebe os testes feitos no RotaGuard Teste de outros computadores da empresa: eventos, resumo de cada sessão e trechos de vídeo."
    >
      <Row label="Situação" description={estado.conectado ? `O painel busca novidades a cada ${estado.intervalo_s} s enquanto está aberto.` : undefined}>
        <p className={cn("text-[14px]", status.alarme ? "font-semibold text-alarme" : "text-tinta")}>{status.texto}</p>
      </Row>

      {!estado.conectado ? (
        <form className="grid max-w-[560px] gap-1 pt-5" onSubmit={conectar} noValidate>
          <p className="mb-4 text-[14px]">
            Use o usuário <b className="font-semibold">gestor ou administrador</b> que a RotaGuard criou para a empresa na central. A senha não fica
            guardada neste computador, só a sessão.
          </p>
          <Field label="Endereço da central" htmlFor="central-endereco" error={erro?.campo === "endereco" ? erro.texto : undefined}>
            <input
              id="central-endereco"
              className="input"
              type="url"
              inputMode="url"
              autoComplete="url"
              spellCheck={false}
              value={endereco}
              onChange={(e) => setEndereco(e.target.value)}
            />
          </Field>
          <Field label="E-mail ou telefone" htmlFor="central-usuario" error={erro?.campo === "usuario" ? erro.texto : undefined}>
            <input
              id="central-usuario"
              className="input"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
            />
          </Field>
          <Field label="Senha da central" htmlFor="central-senha" error={erro?.campo === "senha" ? erro.texto : undefined}>
            <input id="central-senha" className="input" type="password" autoComplete="current-password" value={senha} onChange={(e) => setSenha(e.target.value)} />
          </Field>
          {erro && !["endereco", "usuario", "senha"].includes(erro.campo ?? "") && (
            <p role="alert" className="mb-3 text-[14px] text-alarme">
              {erro.texto}
            </p>
          )}
          <div>
            <SaveButton state={conectando}>Conectar</SaveButton>
          </div>
        </form>
      ) : (
        <>
          <Row label="Conectado como">
            <p className="text-[14px]">
              <b className="font-semibold">{estado.usuario?.nome ?? "Usuário da central"}</b>
              {estado.usuario?.funcao ? ` (${estado.usuario.funcao})` : ""}
              {estado.empresa ? ` · ${estado.empresa.nome}` : ""}
            </p>
          </Row>
          <Row label="Endereço" description={estado.token_protegido ? "Sessão guardada protegida pelo Windows." : "Sessão guardada só neste computador."}>
            <p className="break-all text-[14px]">{estado.endereco}</p>
          </Row>

          <form className="grid max-w-[620px] gap-1 border-b border-fio py-5" onSubmit={gerarCodigo} noValidate>
            <h3 className="font-titulo text-[17px] font-semibold">Gerar código para outro computador</h3>
            <p className="mb-3 text-[14px] text-grafite">O código vale 30 minutos e serve uma vez só. Cada computador recebe o seu.</p>
            <Field label="Nome do computador" optional htmlFor="central-nome" hint="Por exemplo, Computador da portaria." error={erroCodigo?.campo === "nome" ? erroCodigo.texto : undefined}>
              <input id="central-nome" className="input" maxLength={80} value={nomeComputador} onChange={(e) => setNomeComputador(e.target.value)} />
            </Field>
            {erroCodigo && erroCodigo.campo !== "nome" && (
              <p role="alert" className="mb-3 text-[14px] text-alarme">
                {erroCodigo.texto}
              </p>
            )}
            <div>
              <button type="submit" className="btn btn-primary" disabled={gerando}>
                {gerando ? "Gerando…" : "Gerar código"}
              </button>
            </div>
            {codigo && (
              <div className="anim-enter mt-5 rounded-[12px] border border-fio bg-superficie p-5">
                <p className="text-[13.5px] text-grafite">{codigo.nome ? `Código para ${codigo.nome}` : "Código para o outro computador"}</p>
                <p className="mt-1 font-titulo text-[38px] font-semibold tabular-nums tracking-[0.08em]" aria-live="polite">
                  {codigo.codigo}
                </p>
                <p className="text-[14px]">
                  Vale por {codigo.validade_min} min, até <b className="font-semibold">{hora(codigo.expira_em)}</b>, e só uma vez.
                </p>
                <ol className="mt-3 grid list-decimal gap-1 pl-5 text-[14px]">
                  <li>No outro computador, abra o RotaGuard Teste › Conectar à empresa e digite este código.</li>
                  <li>Lá aparece o nome da empresa e o aviso do que vai ser enviado.</li>
                  <li>Os testes daquele computador aparecem em Testes à distância, em até 30 s.</li>
                </ol>
              </div>
            )}
          </form>

          <Row label="Parar de receber" description="O painel para de buscar novidades. Os testes já baixados continuam aqui.">
            <button type="button" className="btn" onClick={() => setConfirmar(true)}>
              Desconectar
            </button>
          </Row>
        </>
      )}

      <Dialog
        open={confirmar}
        onClose={() => setConfirmar(false)}
        title="Desconectar da central?"
        summary="O painel para de buscar os testes dos outros computadores. Nada do que já foi baixado é apagado."
        footer={
          <>
            <button type="button" className="btn btn-primary" disabled={saindo} onClick={() => void desconectar()}>
              {saindo ? "Desconectando…" : "Desconectar"}
            </button>
            <button type="button" className="btn" onClick={() => setConfirmar(false)}>
              Cancelar
            </button>
          </>
        }
      />
    </Section>
  );
}
