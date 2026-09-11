"""Render local curto do estudo de engenharia: giro e montagem, sem serviços pagos.
Executar: blender -b -P render_site.py -- <pasta-de-saida> [teste|video]
O modelo técnico é um estudo distinto da visualização de design gerada por IA.
"""
import importlib.util
import os
import sys
import math
import bpy

spec = importlib.util.spec_from_file_location("caixa", os.path.join(os.path.dirname(__file__), "caixa_rotaguard.py"))
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)
args = sys.argv[sys.argv.index("--") + 1:]
output = os.path.abspath(args[0])
mode = args[1] if len(args) > 1 else "teste"
os.makedirs(output, exist_ok=True)
model.limpar_cena()
m = model.materiais()
root, groups = model.montar_caixa(m)
# Expose the optical elements ahead of the opaque cover in this explanatory render.
model.cilindro("Optica visivel", 4.0*model.MM, 1.4*model.MM, (0,-37*model.MM,17*model.MM), m["lente"], groups["camera"], eixo="Y")
for x in [-19,19]:
    model.cilindro("IR visivel "+str(x), 1.5*model.MM, 1.0*model.MM, (x*model.MM,-37*model.MM,17*model.MM), m["chip"], groups["camera"], eixo="Y")
target = model.estudio(m)
camera = model.camera(target, (0.31, -0.37, 0.22))
camera.data.dof.use_dof = False
scene = bpy.context.scene
scene.render.resolution_x = 800
scene.render.resolution_y = 500
scene.render.resolution_percentage = 100
scene.render.fps = 16
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25
scene.view_settings.view_transform = "AgX"
for name in ["aluminio", "vidro"]:
    bsdf = m[name].node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Metallic"].default_value = 0.65 if name == "aluminio" else 0
    bsdf.inputs["Roughness"].default_value = 0.38 if name == "aluminio" else 0.25
    if name == "vidro":
        bsdf.inputs["Coat Weight"].default_value = 0
        bsdf.inputs["Specular IOR Level"].default_value = 0.08
    else:
        bsdf.inputs["Base Color"].default_value = (0.009,0.012,0.01,1)
        bsdf.inputs["Metallic"].default_value = 0.25
for light in bpy.data.lights:
    light.energy *= 0.35
floor = m["estudio"].node_tree.nodes.get("Principled BSDF")
floor.inputs["Base Color"].default_value = (0.82,0.86,0.78,1)
floor.inputs["Emission Strength"].default_value = 0.16
try:
    scene.eevee.taa_render_samples = 24
except AttributeError:
    pass
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
model.chave(root, 1, rotacao=(0,0,0), interp="LINEAR")
model.chave(root, 65, rotacao=(0,0,math.tau), interp="LINEAR")
model.chave(root, 80, rotacao=(0,0,math.tau), interp="LINEAR")
for name, displacement in model.EXPLOSAO.items():
    scaled = tuple(v*0.50 for v in displacement)
    model.chave(groups[name], 80, local=(0,0,0))
    model.chave(groups[name], 105, local=scaled)
    model.chave(groups[name], 116, local=scaled)
    model.chave(groups[name], 148, local=(0,0,0))
scene.frame_start, scene.frame_end = 1, 160
scene.render.filepath = os.path.join(output, "frame-")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(output, "estudo-engenharia.blend"))
if mode == "teste":
    scene.frame_set(1)
    scene.render.filepath = os.path.join(output, "preview.png")
    bpy.ops.render.render(write_still=True)
else:
    for index, frame in enumerate(range(1,161,2), start=1):
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(output, f"frame-{index:04d}.png")
        bpy.ops.render.render(write_still=True)
