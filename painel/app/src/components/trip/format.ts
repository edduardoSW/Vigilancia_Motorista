// Formatos de hora e data do relatório da viagem. Sem importação.

const dois = (numero: number) => String(numero).padStart(2, "0");

/** "04:03:12". */
export const horaComSegundos = (iso: string) => iso.slice(11, 19);

/** "14/09/2026". */
export const dataCompleta = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** A decisão gravada pelo Python vem em UTC ("…Z"): mostra no relógio deste computador. A de demonstração já é local. */
export function quandoDecidiu(iso: string) {
  if (/(Z|[+-]\d\d:\d\d)$/.test(iso)) {
    const data = new Date(iso);
    return `${dois(data.getDate())}/${dois(data.getMonth() + 1)} às ${dois(data.getHours())}:${dois(data.getMinutes())}`;
  }
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)} às ${iso.slice(11, 16)}`;
}
