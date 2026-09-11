import mediapipe as mp

print("Versão do MediaPipe:", mp.__version__)
print("\nAtributos disponíveis:")
for attr in dir(mp):
    if not attr.startswith('_'):
        print(f"  - {attr}")

print("\nVerificando API:")
if hasattr(mp, 'solutions'):
    print("✅ API mp.solutions disponível!")
    print("  Atributos em solutions:")
    for attr in dir(mp.solutions):
        if not attr.startswith('_'):
            print(f"    - {attr}")
elif hasattr(mp, 'FaceMesh'):
    print("✅ API mp.FaceMesh disponível!")
else:
    print("❌ API não reconhecida")
