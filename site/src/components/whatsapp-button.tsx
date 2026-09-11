import { linkWhatsApp } from "@/content/site";

// Sem número configurado, o botão aparece desativado (nunca href="#", o erro da prévia v2).
export function WhatsAppButton({
  mensagem,
  rotulo,
  className,
  secao,
}: {
  mensagem: string;
  rotulo: string;
  className?: string;
  secao?: string;
}) {
  const href = linkWhatsApp(mensagem);

  if (!href) {
    return (
      <span role="link" aria-disabled="true" title="WhatsApp: número ainda não configurado" className={className}>
        {rotulo}
      </span>
    );
  }

  return (
    <a href={href} target="_blank" rel="noopener" data-evento="whatsapp_clique" data-secao={secao} className={className}>
      {rotulo}
    </a>
  );
}
