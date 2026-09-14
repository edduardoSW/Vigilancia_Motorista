"use client";

import { Icon } from "@/components/icons";

export function PrintButton() {
  return (
    <button type="button" onClick={() => window.print()} className="btn no-print">
      <Icon name="print" size={16} />
      Imprimir
    </button>
  );
}
