"use client";

import { usePathname } from "next/navigation";
import { Suspense, use, useEffect, useRef, useState } from "react";
import { CommandPalette } from "@/components/command-palette";
import { Wordmark } from "@/components/icons";
import { useSession } from "@/components/session-provider";
import { Sidebar } from "@/components/sidebar";
import { Field } from "@/components/ui/field";
import { bridge, type NovoAdministrador, SENHA_MINIMA } from "@/lib/bridge";
import { cn } from "@/lib/utils";

// Portão do painel (spec 014): ativar → criar administrador → guardar o código → entrar → trocar senha se pedido.
// Depois de entrar, o menu e o conteúdo; a tela de bloqueio fica por cima sem perder a página aberta.
// A faixa de prévia aparece em todas as telas (o --verificar do app procura "dados fictícios").
export const AVISO_PREVIA = "Prévia com dados fictícios. Ler a caixa de verdade (registro e vídeos) ainda está em desenvolvimento.";

/** Pede para parar vídeos e fechar janelas de vídeo quando a tela bloqueia. */
export const EVENTO_BLOQUEIO = "rotaguard:bloqueio";

const TOQUE_MS = 30_000;
const nunca = new Promise<never>(() => {});

function Faixa({ className }: { className?: string }) {
  return <p className={cn("no-print border-b border-fio px-10 py-2.5 text-[12px] text-grafite", className)}>{AVISO_PREVIA}</p>;
}

// No build o conteúdo sai no HTML (escondido); na janela ele só monta depois de alguém entrar.
function Conteudo({ liberado, children }: { liberado: boolean; children: React.ReactNode }) {
  if (typeof window !== "undefined" && !liberado) use(nunca);
  return <>{children}</>;
}

type Fase = "carregando" | "falha" | "ativar" | "codigo" | "entrar" | "trocar" | "app";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { estado, usuario, atualizar, sair, falha } = useSession();
  const [codigo, setCodigo] = useState<string | null>(null);
  const rota = usePathname() || "/";

  let fase: Fase;
  if (codigo) fase = "codigo";
  else if (!estado) fase = falha ? "falha" : "carregando";
  else if (!estado.ativado) fase = "ativar";
  else if (!usuario) fase = "entrar";
  else if (usuario.trocar_senha) fase = "trocar";
  else fase = "app";

  const bloqueado = fase === "app" && Boolean(estado?.bloqueado);
  useVigiaDeUso(fase === "app" && !bloqueado, atualizar);

  // Texto maior (spec 016, decisão 8): vale para todas as pessoas deste computador, inclusive na tela de entrar.
  const textoMaior = Boolean(estado?.texto_maior);
  useEffect(() => {
    document.documentElement.toggleAttribute("data-texto-maior", textoMaior);
  }, [textoMaior]);

  // Tema (spec 019, decisão 4): o da pessoa que entrou; "Igual ao Windows" acompanha a troca do sistema na hora.
  const tema = estado?.tema ?? "claro";
  useEffect(() => {
    const raiz = document.documentElement;
    if (tema !== "sistema") {
      raiz.dataset.tema = tema;
      return;
    }
    const escuro = window.matchMedia("(prefers-color-scheme: dark)");
    const aplicar = () => {
      raiz.dataset.tema = escuro.matches ? "escuro" : "claro";
    };
    aplicar();
    escuro.addEventListener("change", aplicar);
    return () => escuro.removeEventListener("change", aplicar);
  }, [tema]);

  return (
    <>
      {fase === "carregando" && (
        <TelaDeFora versao={null}>
          <Wordmark />
          <p className="mt-6 text-[15px] text-grafite">Abrindo o painel…</p>
        </TelaDeFora>
      )}
      {fase === "falha" && (
        <TelaDeFora versao={null}>
          <Wordmark />
          <h1 className="mt-8 font-titulo text-[30px] font-semibold">O painel não abriu</h1>
          <p className="mt-2 text-[15px] text-grafite">{falha}</p>
          <button type="button" className="btn btn-primary mt-6" onClick={() => void atualizar()}>
            Tentar de novo
          </button>
        </TelaDeFora>
      )}
      {fase === "ativar" && (
        <TelaDeFora versao={estado?.versao ?? null}>
          <Ativar onAtivado={setCodigo} />
        </TelaDeFora>
      )}
      {fase === "codigo" && codigo && (
        <TelaDeFora versao={estado?.versao ?? null}>
          <CodigoRecuperacao
            codigo={codigo}
            onAnotei={async () => {
              await atualizar();
              setCodigo(null);
            }}
          />
        </TelaDeFora>
      )}
      {fase === "entrar" && (
        <TelaDeFora versao={estado?.versao ?? null}>
          <Entrar empresa={estado?.empresa?.nome ?? null} onEntrou={atualizar} />
        </TelaDeFora>
      )}
      {fase === "trocar" && usuario && (
        <TelaDeFora versao={estado?.versao ?? null}>
          <TrocarSenha nome={usuario.nome} onTrocou={atualizar} onSair={sair} />
        </TelaDeFora>
      )}

      {(fase === "app" || fase === "carregando") && (
        <div hidden={fase !== "app"} inert={bloqueado} className="app-shell grid h-[var(--altura-janela)] grid-cols-[288px_minmax(0,1fr)] overflow-hidden">
          <Sidebar />
          <main id="conteudo" className="overflow-y-auto">
            <Faixa />
            <Suspense key={fase === "app" ? "app" : "espera"} fallback={null}>
              <Conteudo liberado={fase === "app"}>
                <div key={rota} className="anim-enter">
                  {children}
                </div>
              </Conteudo>
            </Suspense>
          </main>
          {/* Painéis laterais e diálogos das telas abrem aqui (ui/layer.tsx), fora da animação de entrada da tela. */}
          <div id="camada-sobreposta" className="contents" />
        </div>
      )}

      {fase === "app" && !bloqueado && <CommandPalette />}

      {bloqueado && usuario && <TelaBloqueada nome={usuario.nome} minutos={estado?.bloqueio_min ?? 15} onDesbloqueou={atualizar} onSair={sair} />}
    </>
  );
}

// Toca a ponte no máximo a cada 30 s quando há uso, e confere a cada 30 s se o Python bloqueou a tela sozinho.
function useVigiaDeUso(ativo: boolean, atualizar: () => Promise<void>) {
  const ultimo = useRef(0);

  useEffect(() => {
    if (!ativo) return;
    ultimo.current = Date.now();
    const conferir = (bloqueou: boolean) => {
      if (bloqueou) void atualizar();
    };
    const uso = () => {
      const agora = Date.now();
      if (agora - ultimo.current < TOQUE_MS) return;
      ultimo.current = agora;
      void bridge.tocar().then((resposta) => conferir(resposta.ok ? resposta.dados.bloqueado : resposta.codigo === "bloqueado" || resposta.codigo === "sem_sessao"));
    };
    const eventos = ["pointerdown", "keydown", "wheel", "pointermove"] as const;
    for (const nome of eventos) window.addEventListener(nome, uso, { passive: true });
    const vigia = window.setInterval(() => {
      void bridge.estado().then((resposta) => conferir(resposta.ok && (resposta.dados.bloqueado || !resposta.dados.sessao)));
    }, TOQUE_MS);
    return () => {
      for (const nome of eventos) window.removeEventListener(nome, uso);
      window.clearInterval(vigia);
    };
  }, [ativo, atualizar]);
}

function TelaDeFora({ children, versao }: { children: React.ReactNode; versao: string | null }) {
  return (
    <div className="flex min-h-[var(--altura-janela)] flex-col">
      <Faixa />
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="anim-enter w-full max-w-[400px]">{children}</div>
      </div>
      <p className="no-print pb-5 text-center text-[12.5px] text-grafite">
        RotaGuard Painel{versao ? ` ${versao}` : ""} · Os dados ficam guardados neste computador.
      </p>
    </div>
  );
}

function SenhaInput({
  id,
  value,
  onChange,
  invalid,
  autoComplete,
  autoFocus,
}: {
  id: string;
  value: string;
  onChange: (valor: string) => void;
  invalid?: boolean;
  autoComplete: string;
  autoFocus?: boolean;
}) {
  const [mostrar, setMostrar] = useState(false);
  return (
    <div className="relative">
      <input
        id={id}
        type={mostrar ? "text" : "password"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        autoFocus={autoFocus}
        aria-invalid={invalid || undefined}
        className="input h-[46px] pr-20"
      />
      <button
        type="button"
        onClick={() => setMostrar((valor) => !valor)}
        className="absolute inset-y-0 right-1.5 my-auto h-8 rounded-[7px] px-2.5 text-[13px] font-semibold text-tinta transition-colors hover:bg-lateral"
      >
        {mostrar ? "Esconder" : "Mostrar"}
      </button>
    </div>
  );
}

function RegraDaSenha({ senha }: { senha: string }) {
  const pronta = senha.length >= SENHA_MINIMA;
  return (
    <span className="flex justify-between gap-3">
      <span>No mínimo {SENHA_MINIMA} caracteres. Pode ser uma frase fácil de lembrar; não precisa de símbolo.</span>
      <span className={cn("shrink-0 tabular-nums", pronta ? "font-semibold text-verde" : "text-grafite")}>
        {pronta ? "ok" : `${senha.length} de ${SENHA_MINIMA}`}
      </span>
    </span>
  );
}

function Entrar({ empresa, onEntrou }: { empresa: string | null; onEntrou: () => Promise<void> }) {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [espera, setEspera] = useState(0);
  const [enviando, setEnviando] = useState(false);
  const [recuperar, setRecuperar] = useState(false);

  useEffect(() => {
    if (espera <= 0) return;
    const timer = window.setTimeout(() => setEspera((valor) => valor - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [espera]);

  if (recuperar) return <Recuperar onVoltar={() => setRecuperar(false)} />;

  async function enviar(event: React.FormEvent) {
    event.preventDefault();
    if (espera > 0 || enviando) return;
    if (!usuario.trim() || !senha) {
      setErro("Escreva o usuário e a senha.");
      return;
    }
    setEnviando(true);
    setErro(null);
    const resposta = await bridge.entrar(usuario.trim(), senha);
    setEnviando(false);
    setSenha("");
    if (resposta.ok) {
      await onEntrou();
      return;
    }
    if (resposta.codigo === "espera") setEspera(Math.max(1, Math.ceil(resposta.esperar_s ?? 30)));
    setErro(resposta.erro);
  }

  return (
    <form onSubmit={enviar} noValidate>
      <Wordmark />
      <h1 className="mt-10 font-titulo text-[34px] font-semibold leading-tight tracking-[-0.01em]">Entrar</h1>
      {empresa && <p className="mt-1 text-[15px] text-grafite">Painel da {empresa}</p>}
      <div className="mt-7">
        <Field label="Usuário" htmlFor="entrar-usuario">
          <input
            id="entrar-usuario"
            value={usuario}
            onChange={(event) => setUsuario(event.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            autoFocus
            className="input h-[46px]"
          />
        </Field>
        <Field label="Senha" htmlFor="entrar-senha">
          <SenhaInput id="entrar-senha" value={senha} onChange={setSenha} autoComplete="current-password" invalid={Boolean(erro)} />
        </Field>
      </div>
      <button type="submit" disabled={enviando || espera > 0} className="btn btn-primary mt-2 h-[46px] w-full justify-center">
        {enviando ? "Entrando…" : "Entrar"}
      </button>
      <p role="alert" className="mt-3 min-h-5 text-[14px] text-alarme">
        {espera > 0 ? `Espere ${espera} ${espera === 1 ? "segundo" : "segundos"} para tentar de novo.` : erro}
      </p>
      <p className="mt-2 text-[14px] leading-relaxed text-grafite">
        Esqueceu a senha? Peça ao administrador da empresa uma senha nova.{" "}
        <button type="button" onClick={() => setRecuperar(true)} className="font-semibold text-tinta hover:underline">
          Sou o administrador e tenho o código de recuperação
        </button>
      </p>
    </form>
  );
}

function Recuperar({ onVoltar }: { onVoltar: () => void }) {
  const [usuario, setUsuario] = useState("");
  const [codigo, setCodigo] = useState("");
  const [nova, setNova] = useState("");
  const [erro, setErro] = useState<{ campo?: string; texto: string } | null>(null);
  const [pronto, setPronto] = useState(false);
  const [enviando, setEnviando] = useState(false);

  async function enviar(event: React.FormEvent) {
    event.preventDefault();
    setEnviando(true);
    const resposta = await bridge.recuperar_acesso(usuario.trim(), codigo.trim(), nova);
    setEnviando(false);
    if (resposta.ok) {
      setPronto(true);
      return;
    }
    setErro({ campo: resposta.campo, texto: resposta.erro });
  }

  if (pronto) {
    return (
      <div>
        <Wordmark />
        <h1 className="mt-10 font-titulo text-[30px] font-semibold">Senha trocada</h1>
        <p className="mt-2 text-[15px] text-grafite">O código de recuperação não vale mais. Entre com a senha nova.</p>
        <button type="button" onClick={onVoltar} className="btn btn-primary mt-6">
          Voltar para Entrar
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={enviar} noValidate>
      <Wordmark />
      <h1 className="mt-10 font-titulo text-[30px] font-semibold leading-tight">Voltar a entrar com o código</h1>
      <p className="mt-1 text-[15px] text-grafite">O código foi mostrado uma vez, na ativação do painel. Ele só vale uma vez.</p>
      <div className="mt-6">
        <Field label="Usuário do administrador" htmlFor="rec-usuario">
          <input id="rec-usuario" value={usuario} onChange={(event) => setUsuario(event.target.value)} autoComplete="username" className="input" autoFocus />
        </Field>
        <Field label="Código de recuperação" htmlFor="rec-codigo">
          <input id="rec-codigo" value={codigo} onChange={(event) => setCodigo(event.target.value)} autoComplete="off" spellCheck={false} className="input" />
        </Field>
        <Field label="Senha nova" htmlFor="rec-nova" hint={<RegraDaSenha senha={nova} />} error={erro?.campo === "nova_senha" ? erro.texto : null}>
          <SenhaInput id="rec-nova" value={nova} onChange={setNova} autoComplete="new-password" invalid={erro?.campo === "nova_senha"} />
        </Field>
      </div>
      {erro && erro.campo !== "nova_senha" && (
        <p role="alert" className="mb-3 text-[14px] text-alarme">
          {erro.texto}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={enviando} className="btn btn-primary">
          {enviando ? "Conferindo…" : "Trocar a senha"}
        </button>
        <button type="button" onClick={onVoltar} className="btn">
          Voltar
        </button>
      </div>
    </form>
  );
}

function Ativar({ onAtivado }: { onAtivado: (codigo: string) => void }) {
  const [etapa, setEtapa] = useState<"escolher" | "admin">("escolher");
  const [arquivo, setArquivo] = useState<{ nome: string; conteudo: string } | null>(null);
  const [erroArquivo, setErroArquivo] = useState<string | null>(null);
  const [admin, setAdmin] = useState<NovoAdministrador>({ nome: "", usuario: "", senha: "" });
  const [erro, setErro] = useState<{ campo?: string; texto: string } | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function lerArquivo(event: React.ChangeEvent<HTMLInputElement>) {
    const escolhido = event.target.files?.[0];
    event.target.value = "";
    if (!escolhido) return;
    if (escolhido.size > 2_000_000) {
      setErroArquivo("Este arquivo não é válido. Peça um novo à RotaGuard.");
      return;
    }
    setErroArquivo(null);
    setArquivo({ nome: escolhido.name, conteudo: await escolhido.text() });
    setEtapa("admin");
  }

  async function criar(event: React.FormEvent) {
    event.preventDefault();
    setEnviando(true);
    setErro(null);
    const resposta = arquivo ? await bridge.ativar_com_arquivo(arquivo.conteudo, admin) : await bridge.ativar_demonstracao(admin);
    setEnviando(false);
    if (resposta.ok) {
      setAdmin({ nome: "", usuario: "", senha: "" });
      onAtivado(resposta.dados.codigo_recuperacao);
      return;
    }
    if (resposta.campo === "arquivo") {
      setArquivo(null);
      setEtapa("escolher");
      setErroArquivo(resposta.erro);
      return;
    }
    setErro({ campo: resposta.campo, texto: resposta.erro });
  }

  if (etapa === "escolher") {
    return (
      <div>
        <Wordmark />
        <h1 className="mt-10 font-titulo text-[34px] font-semibold leading-tight tracking-[-0.01em]">Ativar o painel</h1>
        <p className="mt-2 text-[15px] leading-relaxed text-grafite">
          Abra o arquivo da empresa que a RotaGuard entregou. Sem ele, dá para ver uma demonstração com dados fictícios.
        </p>
        <label className="btn btn-primary mt-7 h-[46px] w-full cursor-pointer justify-center">
          Abrir arquivo da empresa
          <input type="file" accept=".json,application/json" onChange={lerArquivo} className="sr-only" />
        </label>
        <button
          type="button"
          onClick={() => {
            setArquivo(null);
            setErroArquivo(null);
            setEtapa("admin");
          }}
          className="btn mt-2.5 h-[46px] w-full justify-center"
        >
          Ver demonstração
        </button>
        {erroArquivo && (
          <p role="alert" className="anim-enter mt-4 text-[14px] text-alarme">
            {erroArquivo}
          </p>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={criar} noValidate>
      <Wordmark />
      <h1 className="mt-10 font-titulo text-[30px] font-semibold leading-tight tracking-[-0.01em]">Criar o administrador</h1>
      <p className="mt-1.5 text-[15px] text-grafite">
        {arquivo ? `Arquivo ${arquivo.nome}.` : "Demonstração com dados fictícios."} Quem administra cria depois as contas da equipe.
      </p>
      <div className="mt-6">
        <Field label="Nome" htmlFor="adm-nome" error={erro?.campo === "nome" ? erro.texto : null}>
          <input
            id="adm-nome"
            value={admin.nome}
            onChange={(event) => setAdmin({ ...admin, nome: event.target.value })}
            autoComplete="name"
            autoFocus
            aria-invalid={erro?.campo === "nome" || undefined}
            className="input"
          />
        </Field>
        <Field label="Usuário" htmlFor="adm-usuario" hint="Nome curto para entrar, por exemplo marina.lopes." error={erro?.campo === "usuario" ? erro.texto : null}>
          <input
            id="adm-usuario"
            value={admin.usuario}
            onChange={(event) => setAdmin({ ...admin, usuario: event.target.value })}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            aria-invalid={erro?.campo === "usuario" || undefined}
            className="input"
          />
        </Field>
        <Field label="Senha" htmlFor="adm-senha" hint={<RegraDaSenha senha={admin.senha} />} error={erro?.campo === "senha" ? erro.texto : null}>
          <SenhaInput
            id="adm-senha"
            value={admin.senha}
            onChange={(senha) => setAdmin({ ...admin, senha })}
            autoComplete="new-password"
            invalid={erro?.campo === "senha"}
          />
        </Field>
      </div>
      {erro && !["nome", "usuario", "senha"].includes(erro.campo ?? "") && (
        <p role="alert" className="mb-3 text-[14px] text-alarme">
          {erro.texto}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={enviando} className="btn btn-primary">
          {enviando ? "Criando…" : "Criar e continuar"}
        </button>
        <button type="button" onClick={() => setEtapa("escolher")} className="btn">
          Voltar
        </button>
      </div>
    </form>
  );
}

function CodigoRecuperacao({ codigo, onAnotei }: { codigo: string; onAnotei: () => Promise<void> }) {
  const [seguindo, setSeguindo] = useState(false);
  return (
    <div>
      <Wordmark />
      <h1 className="mt-10 font-titulo text-[30px] font-semibold leading-tight tracking-[-0.01em]">Guarde o código de recuperação</h1>
      <p className="mt-2 text-[15px] leading-relaxed text-grafite">
        Ele aparece só agora. Se quem administra esquecer a senha, é com este código que se volta a entrar. Imprima ou anote e
        guarde longe do computador.
      </p>
      <p className="my-6 rounded-[12px] border border-fio bg-superficie px-4 py-6 text-center font-titulo text-[26px] font-semibold tabular-nums tracking-[0.06em]">
        {codigo}
      </p>
      <div className="flex gap-2">
        <button type="button" onClick={() => window.print()} className="btn no-print">
          Imprimir
        </button>
        <button
          type="button"
          disabled={seguindo}
          onClick={() => {
            setSeguindo(true);
            void onAnotei();
          }}
          className="btn btn-primary no-print"
        >
          Anotei o código
        </button>
      </div>
    </div>
  );
}

function TrocarSenha({ nome, onTrocou, onSair }: { nome: string; onTrocou: () => Promise<void>; onSair: () => Promise<void> }) {
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [repetir, setRepetir] = useState("");
  const [erro, setErro] = useState<{ campo?: string; texto: string } | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(event: React.FormEvent) {
    event.preventDefault();
    if (nova !== repetir) {
      setErro({ campo: "repetir", texto: "As duas senhas novas não são iguais." });
      return;
    }
    setEnviando(true);
    const resposta = await bridge.trocar_senha(atual, nova);
    setEnviando(false);
    if (resposta.ok) {
      await onTrocou();
      return;
    }
    setErro({ campo: resposta.campo, texto: resposta.erro });
  }

  return (
    <form onSubmit={enviar} noValidate>
      <Wordmark />
      <h1 className="mt-10 font-titulo text-[30px] font-semibold leading-tight">Troque a senha</h1>
      <p className="mt-1.5 text-[15px] text-grafite">{nome}, a senha que você usou foi criada pelo administrador. Escolha uma sua para continuar.</p>
      <div className="mt-6">
        <Field label="Senha que você recebeu" htmlFor="troca-atual" error={erro?.campo === "atual" ? erro.texto : null}>
          <SenhaInput id="troca-atual" value={atual} onChange={setAtual} autoComplete="current-password" invalid={erro?.campo === "atual"} autoFocus />
        </Field>
        <Field label="Senha nova" htmlFor="troca-nova" hint={<RegraDaSenha senha={nova} />} error={erro?.campo === "nova" ? erro.texto : null}>
          <SenhaInput id="troca-nova" value={nova} onChange={setNova} autoComplete="new-password" invalid={erro?.campo === "nova"} />
        </Field>
        <Field label="Repita a senha nova" htmlFor="troca-repetir" error={erro?.campo === "repetir" ? erro.texto : null}>
          <SenhaInput id="troca-repetir" value={repetir} onChange={setRepetir} autoComplete="new-password" invalid={erro?.campo === "repetir"} />
        </Field>
      </div>
      {erro && !["atual", "nova", "repetir"].includes(erro.campo ?? "") && (
        <p role="alert" className="mb-3 text-[14px] text-alarme">
          {erro.texto}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={enviando} className="btn btn-primary">
          {enviando ? "Salvando…" : "Salvar e entrar"}
        </button>
        <button type="button" onClick={() => void onSair()} className="btn">
          Sair
        </button>
      </div>
    </form>
  );
}

function TelaBloqueada({
  nome,
  minutos,
  onDesbloqueou,
  onSair,
}: {
  nome: string;
  minutos: number;
  onDesbloqueou: () => Promise<void>;
  onSair: () => Promise<void>;
}) {
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    for (const video of document.querySelectorAll("video")) video.pause();
    window.dispatchEvent(new Event(EVENTO_BLOQUEIO));
  }, []);

  async function enviar(event: React.FormEvent) {
    event.preventDefault();
    setEnviando(true);
    const resposta = await bridge.desbloquear(senha);
    setEnviando(false);
    setSenha("");
    if (resposta.ok) {
      await onDesbloqueou();
      return;
    }
    if (resposta.codigo === "sem_sessao") {
      await onDesbloqueou();
      return;
    }
    setErro(resposta.erro);
  }

  return (
    <div className="veu-forte anim-fade fixed inset-0 z-[70] flex flex-col">
      <p className="no-print border-b border-sobre-video/10 px-10 py-2.5 text-[12px] text-sobre-video/70">{AVISO_PREVIA}</p>
      <div className="grid flex-1 place-items-center p-6">
        <form onSubmit={enviar} noValidate className="anim-dialog w-full max-w-[380px] rounded-[14px] border border-fio bg-elevada p-6">
          <h2 className="font-titulo text-[24px] font-semibold">Tela bloqueada</h2>
          <p className="mt-1.5 text-[14.5px] text-grafite">
            Ficou {minutos} min sem uso. Digite a senha de {nome} para continuar de onde parou.
          </p>
          <div className="mt-5">
            <Field label="Senha" htmlFor="bloqueio-senha" error={erro}>
              <SenhaInput id="bloqueio-senha" value={senha} onChange={setSenha} autoComplete="current-password" invalid={Boolean(erro)} autoFocus />
            </Field>
          </div>
          <div className="flex items-center gap-2">
            <button type="submit" disabled={enviando || !senha} className="btn btn-primary">
              {enviando ? "Conferindo…" : "Desbloquear"}
            </button>
            <button type="button" onClick={() => void onSair()} className="btn btn-quiet">
              Sair
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
