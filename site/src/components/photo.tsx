import Image from "next/image";
import { getLocale, getTranslations } from "next-intl/server";
import { fotoPorCodigo } from "@/lib/fotos";

/**
 * Foto de uma cena do roteiro de mídia (docs/site/midia/). Hoje usa a foto provisória de licença livre;
 * quando a série própria existir, troca-se só o manifesto. Sem foto, mostra um bloco com o código da cena,
 * no padrão do São Jorge (espaço reservado e nomeado).
 */
export async function Photo({
  codigo,
  cena,
  className,
  sizes,
  prioridade = false,
  preencher = true,
  credito = "canto",
  tom = "claro",
}: {
  codigo: string;
  cena: string;
  className?: string;
  sizes: string;
  prioridade?: boolean;
  preencher?: boolean;
  credito?: "canto" | "abaixo" | "nenhum";
  tom?: "claro" | "escuro";
}) {
  const foto = await fotoPorCodigo(codigo);
  const locale = await getLocale();
  const t = await getTranslations("comum");

  if (!foto) {
    return (
      <div
        role="img"
        aria-label={cena}
        className={`flex ${credito === "nenhum" ? "items-start" : "items-end"} ${tom === "escuro" ? "bg-noite-2 text-noite-muted" : "bg-terra text-grafite"} ${className ?? ""}`}
      >
        <span className="etiqueta p-4">
          {codigo.toUpperCase()} · {cena}
        </span>
      </div>
    );
  }

  const alt = locale === "pt-BR" ? foto.altPt : foto.altEn;
  const textoCredito = `${t("fotoProvisoria")} · ${foto.autor} · ${foto.licenca}`;

  return (
    <figure className={`relative overflow-hidden ${className ?? ""}`}>
      {preencher ? (
        <Image src={foto.arquivo} alt={alt} fill sizes={sizes} preload={prioridade} className="object-cover" />
      ) : (
        <Image
          src={foto.arquivo}
          alt={alt}
          width={foto.largura}
          height={foto.altura}
          sizes={sizes}
          preload={prioridade}
          className="h-auto w-full"
        />
      )}
      {credito === "canto" ? (
        <figcaption className="etiqueta absolute right-0 bottom-0 max-w-full bg-noite/70 px-2 py-1 text-[0.58rem] text-noite-texto">
          {textoCredito}
        </figcaption>
      ) : null}
      {credito === "abaixo" ? (
        <figcaption className="etiqueta mt-2 text-[0.62rem] text-grafite">{textoCredito}</figcaption>
      ) : null}
    </figure>
  );
}
