"""
Caixa RotaGuard (conceito v1) modelada peça por peça em tamanho real, para renders de referência e vídeo do produto.

Hipóteses (docs/site/midia/00-regras-gerais.md, seção 5): Raspberry Pi 4 (placa 85 × 56 mm), módulo de câmera
de ~25 × 24 × 11,5 mm atrás de uma janela de vidro escuro, dois emissores infravermelhos escondidos, buzzer,
corpo de alumínio anodizado grafite com aletas no topo, ~110 × 72 × 40 mm, berço preto fosco. Sem logotipo.

Uso (Blender 5.2, sem janela):
  blender -b -P caixa_rotaguard.py -- montar <pasta_saida>        salva turntable.blend e montagem.blend
  blender -b -P caixa_rotaguard.py -- stills <pasta_saida> [res]  renders PNG com fundo transparente
  blender -b <pasta_saida>/turntable.blend -a                     renderiza o giro de 360°
  blender -b <pasta_saida>/montagem.blend -a                      renderiza a montagem

Unidade: metro. Objetos sem escala de objeto (tamanho aplicado na malha), então não há transform_apply (erro 70).
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

MM = 0.001
FPS = 24


# ---------------------------------------------------------------- utilidades
def argumentos():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    modo = args[0] if args else "montar"
    saida = os.path.abspath(args[1]) if len(args) > 1 else os.path.abspath("saida-caixa")
    resolucao = int(args[2]) if len(args) > 2 else 1920
    os.makedirs(saida, exist_ok=True)
    return modo, saida, resolucao


def limpar_cena():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(nome, cor, metal=0.0, rugosidade=0.5, emissao=0.0, ior=1.5, coat=0.0):
    m = bpy.data.materials.new(nome)
    try:
        m.use_nodes = True
    except Exception:
        pass
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*cor, 1.0)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rugosidade
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    if coat and "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = 0.03
    if emissao:
        bsdf.inputs["Emission Color"].default_value = (*cor, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emissao
    return m


def objeto_malha(nome, bm, mat, pai=None, liso=False):
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    if liso:
        for p in malha.polygons:
            p.use_smooth = True
    obj = bpy.data.objects.new(nome, malha)
    bpy.context.scene.collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    if pai:
        obj.parent = pai
    return obj


def caixa(nome, tamanho, centro, mat, pai=None, chanfro=0.0, segmentos=4):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(tamanho), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(centro), verts=bm.verts)
    obj = objeto_malha(nome, bm, mat, pai)
    if chanfro:
        mod = obj.modifiers.new("Chanfro", "BEVEL")
        mod.width = chanfro
        mod.segments = segmentos
        mod.limit_method = "ANGLE"
        mod.harden_normals = True
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def cilindro(nome, raio, altura, centro, mat, pai=None, eixo="Z", lados=40, chanfro=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=lados, radius1=raio, radius2=raio, depth=altura)
    if eixo == "Y":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, "X"))
    elif eixo == "X":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, "Y"))
    bmesh.ops.translate(bm, vec=Vector(centro), verts=bm.verts)
    obj = objeto_malha(nome, bm, mat, pai, liso=True)
    if chanfro:
        mod = obj.modifiers.new("Chanfro", "BEVEL")
        mod.width = chanfro
        mod.segments = 3
        mod.limit_method = "ANGLE"
        mod.harden_normals = True
    return obj


def vazio(nome, local=(0, 0, 0), pai=None):
    obj = bpy.data.objects.new(nome, None)
    obj.empty_display_size = 0.02
    obj.location = local
    bpy.context.scene.collection.objects.link(obj)
    if pai:
        obj.parent = pai
    return obj


def cortar(alvo, cortador):
    cortador.hide_render = True
    cortador.display_type = "WIRE"
    mod = alvo.modifiers.new(f"Corte {cortador.name}", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cortador
    mod.solver = "EXACT"
    return mod


# ---------------------------------------------------------------- materiais
def materiais():
    return {
        "aluminio": material("Aluminio grafite anodizado", (0.055, 0.058, 0.062), metal=1.0, rugosidade=0.52),
        "vidro": material("Vidro escuro", (0.004, 0.004, 0.005), metal=0.0, rugosidade=0.04, coat=1.0),
        "preto": material("Plastico preto fosco", (0.018, 0.018, 0.018), rugosidade=0.55),
        "berco": material("Berco preto fosco", (0.012, 0.012, 0.013), rugosidade=0.45),
        "pcb": material("Placa verde", (0.02, 0.19, 0.08), rugosidade=0.38),
        "prata": material("Metal das portas", (0.78, 0.78, 0.8), metal=1.0, rugosidade=0.22),
        "ouro": material("Pinos dourados", (1.0, 0.74, 0.32), metal=1.0, rugosidade=0.28),
        "chip": material("Chip", (0.03, 0.03, 0.035), rugosidade=0.35),
        "branco": material("Conector branco", (0.85, 0.84, 0.8), rugosidade=0.5),
        "fita": material("Fita da camera", (0.72, 0.62, 0.36), rugosidade=0.45),
        "almofada": material("Almofada termica", (0.35, 0.37, 0.4), rugosidade=0.8),
        "lente": material("Lente", (0.01, 0.012, 0.02), metal=0.2, rugosidade=0.05, coat=1.0),
        "estudio": material("Estudio branco", (1.0, 1.0, 1.0), rugosidade=0.9, emissao=0.62),
    }


# ---------------------------------------------------------------- peças (medidas em mm)
def montar_caixa(M):
    raiz = vazio("CAIXA")

    # Base: casca com parede de 2,5 mm e piso de 2 mm, janela na frente (-Y) e conector atrás (+Y).
    g_base = vazio("G_base", pai=raiz)
    base = caixa("Base", (110 * MM, 72 * MM, 32 * MM), (0, 0, 16 * MM), M["aluminio"], g_base, chanfro=3 * MM)
    cavidade = caixa("Corte cavidade", (105 * MM, 67 * MM, 32 * MM), (0, 0, 18 * MM), None, g_base)
    janela = caixa("Corte janela", (92 * MM, 8 * MM, 20 * MM), (0, -35 * MM, 17 * MM), None, g_base)
    conector = caixa("Corte conector", (12 * MM, 8 * MM, 6 * MM), (30 * MM, 35 * MM, 10 * MM), None, g_base)
    for c in (cavidade, janela, conector):
        cortar(base, c)
    caixa("USB-C traseiro", (9 * MM, 4 * MM, 3.2 * MM), (30 * MM, 33 * MM, 10 * MM), M["prata"], g_base, chanfro=1 * MM)

    # Raspberry Pi 4: placa 85 × 56 × 1,6 mm sobre espaçadores de 4 mm; portas altas voltadas para +X.
    g_pi = vazio("G_pi", pai=raiz)
    px, py, pz = 8 * MM, 3 * MM, 6 * MM  # canto de referência deslocado dentro da cavidade
    placa_c = (px, py, pz + 0.8 * MM)
    caixa("Placa Pi 4", (85 * MM, 56 * MM, 1.6 * MM), placa_c, M["pcb"], g_pi, chanfro=0.8 * MM, segmentos=2)
    x0, y0, topo = px - 42.5 * MM, py - 28 * MM, pz + 1.6 * MM

    def na_placa(nome, dx, dy, sx, sy, sz, mat, chanfro=0.0):
        return caixa(nome, (sx * MM, sy * MM, sz * MM), (x0 + dx * MM, y0 + dy * MM, topo + sz * MM / 2), mat, g_pi, chanfro * MM)

    na_placa("SoC com tampa metalica", 29, 32.5, 15, 15, 2.4, M["prata"], 0.6)
    na_placa("Memoria", 46, 32.5, 10, 14, 1.2, M["chip"])
    na_placa("Controlador USB", 60, 20, 6, 6, 1.0, M["chip"])
    na_placa("USB 2.0", 77.5, 9, 17.5, 13.5, 16, M["prata"], 0.8)
    na_placa("USB 3.0", 77.5, 27, 17.5, 13.5, 16, M["prata"], 0.8)
    na_placa("Rede", 76, 45.8, 21, 16, 13.5, M["prata"], 0.8)
    na_placa("Barramento GPIO", 32.5, 52.5, 51, 5, 2.5, M["preto"])
    for i in range(20):
        for j in range(2):
            na_placa(f"Pino {i}-{j}", 8 + i * 2.54, 51.3 + j * 2.54, 0.64, 0.64, 8.5, M["ouro"])
    na_placa("USB-C energia", 11.2, 3.2, 9, 7.5, 3.2, M["prata"], 1.0)
    na_placa("Micro HDMI 0", 26, 3, 7.5, 6.5, 3.5, M["prata"], 0.8)
    na_placa("Micro HDMI 1", 39.5, 3, 7.5, 6.5, 3.5, M["prata"], 0.8)
    na_placa("Conector da camera", 45, 11.5, 2.8, 22, 5.5, M["branco"])
    na_placa("Conector da tela", 2.5, 28, 2.8, 22, 5.5, M["branco"])
    cilindro("Saida de audio", 3.1 * MM, 7 * MM, (x0 + 54 * MM, y0 + 5 * MM, topo + 3.2 * MM), M["preto"], g_pi, eixo="Y")
    for hx, hy in ((3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)):
        cilindro("Espacador", 2.6 * MM, 4 * MM, (x0 + hx * MM, y0 + hy * MM, 4 * MM), M["prata"], g_pi, lados=6)

    # Almofada térmica entre o SoC e a tampa (a tampa com aletas é o dissipador).
    g_almofada = vazio("G_almofada", pai=raiz)
    caixa("Almofada termica", (15 * MM, 15 * MM, 19.8 * MM), (x0 + 29 * MM, y0 + 32.5 * MM, topo + 2.4 * MM + 9.9 * MM), M["almofada"], g_almofada, chanfro=0.8 * MM)

    # Câmera: módulo vertical atrás do vidro, lente de frente para o motorista (-Y), dois emissores infravermelhos.
    g_cam = vazio("G_camera", pai=raiz)
    caixa("Placa da camera", (25 * MM, 1.2 * MM, 24 * MM), (0, -29.5 * MM, 17 * MM), M["pcb"], g_cam)
    caixa("Corpo da lente", (8.5 * MM, 5 * MM, 8.5 * MM), (0, -32.4 * MM, 17 * MM), M["preto"], g_cam, chanfro=0.6 * MM)
    cilindro("Lente", 3.2 * MM, 1.2 * MM, (0, -35.2 * MM, 17 * MM), M["lente"], g_cam, eixo="Y")
    for lado in (-1, 1):
        caixa(f"Emissor IR {lado}", (5 * MM, 1.6 * MM, 5 * MM), (lado * 19 * MM, -30.2 * MM, 17 * MM), M["chip"], g_cam, chanfro=0.5 * MM)
    caixa("Fita da camera", (16 * MM, 26 * MM, 0.3 * MM), (8 * MM, -16 * MM, 7.8 * MM), M["fita"], g_cam)

    # Buzzer do alarme.
    g_buzzer = vazio("G_buzzer", pai=raiz)
    cilindro("Buzzer", 6 * MM, 9 * MM, (-42 * MM, 21 * MM, 6.5 * MM), M["preto"], g_buzzer, chanfro=0.8 * MM)

    # Vidro escuro da frente, encaixado no rebaixo da janela.
    g_vidro = vazio("G_vidro", pai=raiz)
    caixa("Vidro frontal", (94 * MM, 1.6 * MM, 22 * MM), (0, -35.4 * MM, 17 * MM), M["vidro"], g_vidro, chanfro=1.2 * MM)

    # Tampa com aletas finas no dorso (dissipador).
    g_tampa = vazio("G_tampa", pai=raiz)
    caixa("Tampa", (110 * MM, 72 * MM, 4 * MM), (0, 0, 34 * MM), M["aluminio"], g_tampa, chanfro=2.5 * MM)
    aleta = caixa("Aletas", (86 * MM, 1.3 * MM, 4.2 * MM), (0, -29.25 * MM, 38 * MM), M["aluminio"], g_tampa, chanfro=0.5 * MM, segmentos=2)
    arr = aleta.modifiers.new("Array", "ARRAY")
    arr.count = 14
    arr.use_relative_offset = False
    arr.use_constant_offset = True
    arr.constant_offset_displace = (0, 4.5 * MM, 0)
    aleta.modifiers.move(len(aleta.modifiers) - 1, 0)

    # Parafusos nos cantos da tampa.
    g_paraf = vazio("G_parafusos", pai=raiz)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cilindro("Parafuso", 2.3 * MM, 1.4 * MM, (sx * 49 * MM, sy * 30 * MM, 36.7 * MM), M["prata"], g_paraf, lados=24, chanfro=0.4 * MM)

    grupos = {
        "base": g_base, "pi": g_pi, "almofada": g_almofada, "camera": g_cam,
        "buzzer": g_buzzer, "vidro": g_vidro, "tampa": g_tampa, "parafusos": g_paraf,
    }
    return raiz, grupos


def montar_berco(M):
    g = vazio("BERCO")
    berco = caixa("Berco", (118 * MM, 80 * MM, 10 * MM), (0, 0, 3 * MM), M["berco"], g, chanfro=2.5 * MM)
    cortar(berco, caixa("Corte berco", (111 * MM, 73.5 * MM, 12 * MM), (0, 0, 9 * MM), None, g))
    return g


# ---------------------------------------------------------------- estúdio
def estudio(M, com_piso=True):
    cena = bpy.context.scene
    for motor in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            cena.render.engine = motor
            break
        except TypeError:
            continue
    cena.render.fps = FPS
    cena.view_settings.view_transform = "Standard"
    cena.view_settings.look = "None"
    try:
        cena.eevee.taa_render_samples = 64
        cena.eevee.use_raytracing = True
    except AttributeError:
        pass

    mundo = bpy.data.worlds.new("Estudio")
    try:
        mundo.use_nodes = True
    except Exception:
        pass
    fundo = mundo.node_tree.nodes.get("Background")
    fundo.inputs["Color"].default_value = (1, 1, 1, 1)
    fundo.inputs["Strength"].default_value = 0.85
    cena.world = mundo

    if com_piso:
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0)
        objeto_malha("Piso do estudio", bm, M["estudio"])

    alvo = vazio("Alvo", (0, 0, 20 * MM))

    def luz(nome, pos, energia, tamanho):
        dados = bpy.data.lights.new(nome, "AREA")
        dados.energy = energia
        dados.size = tamanho
        obj = bpy.data.objects.new(nome, dados)
        obj.location = pos
        cena.collection.objects.link(obj)
        c = obj.constraints.new("TRACK_TO")
        c.target = alvo
        c.track_axis = "TRACK_NEGATIVE_Z"
        c.up_axis = "UP_Y"
        return obj

    luz("Principal", (-0.45, -0.55, 0.65), 55, 0.6)
    luz("Preenchimento", (0.6, -0.35, 0.3), 18, 0.7)
    luz("Contra", (0.25, 0.6, 0.55), 35, 0.4)
    return alvo


def camera(alvo, local, lente=85, nome="Camera"):
    dados = bpy.data.cameras.new(nome)
    dados.lens = lente
    dados.clip_start = 0.005
    dados.clip_end = 20
    dados.dof.use_dof = True
    dados.dof.focus_object = alvo
    dados.dof.aperture_fstop = 11
    obj = bpy.data.objects.new(nome, dados)
    obj.location = local
    bpy.context.scene.collection.objects.link(obj)
    c = obj.constraints.new("TRACK_TO")
    c.target = alvo
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    bpy.context.scene.camera = obj
    return obj


def saida_video(caminho, largura=1920, altura=1080):
    r = bpy.context.scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = largura, altura, 100
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.filepath = caminho


def chave(obj, quadro, local=None, rotacao=None, interp="BEZIER"):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    if local is not None:
        obj.location = local
        obj.keyframe_insert("location", frame=quadro)
    if rotacao is not None:
        obj.rotation_euler = rotacao
        obj.keyframe_insert("rotation_euler", frame=quadro)


# ---------------------------------------------------------------- cenas
def cena_turntable(saida):
    limpar_cena()
    M = materiais()
    raiz, _ = montar_caixa(M)
    alvo = estudio(M)
    camera(alvo, (0.42, -0.46, 0.24))
    cena = bpy.context.scene
    cena.frame_start, cena.frame_end = 1, 8 * FPS
    chave(raiz, 1, rotacao=(0, 0, 0), interp="LINEAR")
    chave(raiz, 8 * FPS + 1, rotacao=(0, 0, math.radians(360)), interp="LINEAR")
    saida_video(os.path.join(saida, "quadros-turntable", "turntable_####"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(saida, "turntable.blend"))


EXPLOSAO = {
    "tampa": (0, 0, 78 * MM),
    "parafusos": (0, 0, 100 * MM),
    "almofada": (0, 0, 52 * MM),
    "pi": (0, 0, 34 * MM),
    "camera": (0, -52 * MM, 12 * MM),
    "vidro": (0, -92 * MM, 0),
    "buzzer": (0, 46 * MM, 22 * MM),
    "base": (0, 0, 0),
}
ORDEM = [("pi", 12), ("almofada", 26), ("camera", 40), ("buzzer", 54), ("vidro", 68), ("tampa", 86), ("parafusos", 106)]
DURACAO_PECA = 22


def cena_montagem(saida):
    limpar_cena()
    M = materiais()
    raiz, grupos = montar_caixa(M)
    berco = montar_berco(M)
    alvo = estudio(M)
    orbita = vazio("Orbita")
    cam = camera(alvo, (0.46, -0.50, 0.30))
    cam.parent = orbita
    cena = bpy.context.scene
    fim = 9 * FPS
    cena.frame_start, cena.frame_end = 1, fim

    # Caixa começa levantada acima do berço, peças separadas; monta em sequência e desce no berço.
    chave(raiz, 1, local=(0, 0, 60 * MM))
    chave(raiz, 136, local=(0, 0, 60 * MM))
    chave(raiz, 168, local=(0, 0, 7 * MM))
    for nome, deslocamento in EXPLOSAO.items():
        chave(grupos[nome], 1, local=deslocamento)
    for nome, inicio in ORDEM:
        chave(grupos[nome], inicio, local=EXPLOSAO[nome])
        chave(grupos[nome], inicio + DURACAO_PECA, local=(0, 0, 0))
    chave(berco, 1, local=(0, 0, 0))

    chave(orbita, 1, rotacao=(0, 0, math.radians(-28)))
    chave(orbita, fim, rotacao=(0, 0, math.radians(8)))
    saida_video(os.path.join(saida, "quadros-montagem", "montagem_####"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(saida, "montagem.blend"))


def renders_estaticos(saida, largura):
    vistas = {
        "tres-quartos": (0.42, -0.46, 0.24),
        "frente": (0.0, -0.62, 0.05),
        "lateral": (0.62, 0.0, 0.06),
        "traseira": (-0.30, 0.55, 0.18),
        "topo": (0.02, -0.12, 0.62),
    }
    for nome, local in list(vistas.items()) + [("no-berco", (0.42, -0.46, 0.24)), ("explodida", (0.5, -0.55, 0.36))]:
        limpar_cena()
        M = materiais()
        raiz, grupos = montar_caixa(M)
        if nome == "no-berco":
            montar_berco(M)
            raiz.location = (0, 0, 7 * MM)
        if nome == "explodida":
            for g, d in EXPLOSAO.items():
                grupos[g].location = d
        alvo = estudio(M, com_piso=False)
        if nome == "explodida":
            alvo.location = (0, -10 * MM, 45 * MM)
        camera(alvo, local)
        cena = bpy.context.scene
        cena.render.film_transparent = True
        cena.render.resolution_x = largura
        cena.render.resolution_y = int(largura * 9 / 16)
        cena.render.image_settings.file_format = "PNG"
        cena.render.image_settings.color_mode = "RGBA"
        cena.render.filepath = os.path.join(saida, f"S15-caixa-render-{nome}-v1.png")
        bpy.ops.render.render(write_still=True)
        print(f"render: {cena.render.filepath}")


if __name__ == "__main__":
    modo, pasta, resolucao = argumentos()
    if modo == "montar":
        cena_turntable(pasta)
        cena_montagem(pasta)
    elif modo == "stills":
        renders_estaticos(pasta, resolucao)
    elif modo == "teste":
        limpar_cena()
        M = materiais()
        montar_caixa(M)
        alvo = estudio(M)
        camera(alvo, (0.42, -0.46, 0.24))
        saida_video(os.path.join(pasta, "teste.png"), 1280, 720)
        bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(pasta, "teste.blend"))
    print("ok")
