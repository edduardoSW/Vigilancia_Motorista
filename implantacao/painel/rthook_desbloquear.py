"""Gancho do PyInstaller (roda antes do rotaguard_painel.py): tira a marca "baixado da internet" do pacote.

Quem baixa o .zip pelo site e extrai com o Explorer recebe todos os arquivos com o fluxo NTFS Zone.Identifier. O .NET
Framework recusa carregar o _internal/pythonnet/runtime/Python.Runtime.dll marcado assim, e o pywebview falha ao abrir
com "Failed to resolve Python.Runtime.Loader.Initialize". Apagar o fluxo antes do pythonnet carregar resolve, sem a
pessoa precisar desbloquear nada. Em pasta sem permissão de escrita (ou fora do NTFS), segue em frente sem erro.
"""
import os
import sys


def desbloquear(pasta):
    """Apaga o Zone.Identifier de cada arquivo da pasta; devolve quantos estavam marcados."""
    desbloqueados = 0
    for raiz, _pastas, arquivos in os.walk(pasta):
        for nome in arquivos:
            try:
                os.remove(os.path.join(raiz, nome) + ":Zone.Identifier")
                desbloqueados += 1
            except OSError:
                pass
    return desbloqueados


if sys.platform == "win32" and getattr(sys, "frozen", False):
    desbloquear(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
