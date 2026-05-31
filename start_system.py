import os
import sys
import webbrowser
import subprocess
import time

def main():
    print("🚗 Iniciando o sistema DriveSafe AI...")
    
    # Caminho do projeto
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Abrir a página web no navegador
    print("🌐 Abrindo o painel administrativo...")
    time.sleep(1)
    webbrowser.open("http://localhost:8000")
    
    # Iniciar o servidor
    print("🔧 Iniciando o servidor web...")
    print("📝 Quando o servidor estiver rodando, execute o monitoramento em outro terminal!")
    print("="*70)
    
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "backend.main:app", "--reload"], cwd=project_dir)
    except KeyboardInterrupt:
        print("\n⏹️ Sistema parado!")

if __name__ == "__main__":
    main()
