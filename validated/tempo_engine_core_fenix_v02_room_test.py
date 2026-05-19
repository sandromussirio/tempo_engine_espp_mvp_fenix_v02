# TEMPO ENGINE / ESPP — FÊNIX CORE V01
# Teste: cômodo simples com piso, 4 paredes, porta e janela
# Rode no Blender: Scripting > New > colar tudo > Run Script

import bpy
import bmesh


class TempoProtocolError(Exception):
    pass


DATA = {
    "objects": [
        {
            "name": "PISO_01", "role": "BASE", "type": "POLYLINE", "category": "FLOOR",
            "points": [[0, 0], [6, 0], [6, 4], [0, 4]],
            "base_z": -0.15, "extrude": 0.15, "color": [120, 120, 120]
        },
        {
            "name": "PAREDE_FRENTE", "role": "BASE", "type": "POLYLINE", "category": "WALL",
            "points": [[0, 0], [6, 0], [6, 0.20], [0, 0.20]],
            "base_z": 0.0, "extrude": 2.80, "color": [0, 46, 61]
        },
        {
            "name": "PAREDE_FUNDO", "role": "BASE", "type": "POLYLINE", "category": "WALL",
            "points": [[0, 3.80], [6, 3.80], [6, 4.00], [0, 4.00]],
            "base_z": 0.0, "extrude": 2.80, "color": [0, 46, 61]
        },
        {
            "name": "PAREDE_ESQUERDA", "role": "BASE", "type": "POLYLINE", "category": "WALL",
            "points": [[0, 0], [0.20, 0], [0.20, 4], [0, 4]],
            "base_z": 0.0, "extrude": 2.80, "color": [0, 46, 61]
        },
        {
            "name": "PAREDE_DIREITA", "role": "BASE", "type": "POLYLINE", "category": "WALL",
            "points": [[5.80, 0], [6.00, 0], [6.00, 4], [5.80, 4]],
            "base_z": 0.0, "extrude": 2.80, "color": [0, 46, 61]
        },
        {
            "name": "PORTA_CUT_01", "role": "CUT", "type": "POLYLINE", "category": "OPENING",
            "target": ["PAREDE_FRENTE"],
            "points": [[2.40, -0.05], [3.30, -0.05], [3.30, 0.25], [2.40, 0.25]],
            "base_z": 0.0, "extrude": 2.10
        },
        {
            "name": "JANELA_CUT_01", "role": "CUT", "type": "POLYLINE", "category": "OPENING",
            "target": ["PAREDE_DIREITA"],
            "points": [[5.75, 1.40], [6.05, 1.40], [6.05, 2.60], [5.75, 2.60]],
            "base_z": 0.90, "extrude": 1.00
        }
    ]
}


def fail(msg):
    raise TempoProtocolError(msg)


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate(data):
    if not isinstance(data, dict):
        fail("A raiz deve ser um dicionário.")
    if "objects" not in data or not isinstance(data["objects"], list):
        fail("O JSON deve conter objects como lista.")

    names = set()
    base_names = set()

    for obj in data["objects"]:
        name = obj.get("name")
        role = obj.get("role")

        if not isinstance(name, str) or not name:
            fail("Objeto sem name válido.")
        if name in names:
            fail(f"Nome duplicado: {name}")
        names.add(name)

        if role not in ("BASE", "CUT"):
            fail(f"Role inválido em {name}.")
        if obj.get("type") != "POLYLINE":
            fail(f"Type inválido em {name}. Use POLYLINE.")
        if not isinstance(obj.get("category"), str):
            fail(f"Category inválida em {name}.")

        pts = obj.get("points")
        if not isinstance(pts, list) or len(pts) < 3:
            fail(f"Points inválido em {name}.")
        for p in pts:
            if not isinstance(p, list) or len(p) != 2 or not is_num(p[0]) or not is_num(p[1]):
                fail(f"Ponto inválido em {name}. Use apenas [x, y].")

        if len({tuple(p) for p in pts}) < 3:
            fail(f"{name} precisa de pelo menos 3 pontos únicos.")
        if not is_num(obj.get("base_z")) or not is_num(obj.get("extrude")) or obj["extrude"] <= 0:
            fail(f"base_z/extrude inválidos em {name}.")

        if role == "BASE":
            color = obj.get("color")
            if not isinstance(color, list) or len(color) != 3:
                fail(f"BASE {name} precisa de color [r,g,b].")
            base_names.add(name)

        if role == "CUT":
            target = obj.get("target")
            if not isinstance(target, list) or not target:
                fail(f"CUT {name} precisa de target.")

    for obj in data["objects"]:
        if obj["role"] == "CUT":
            for target in obj["target"]:
                if target not in base_names:
                    fail(f"CUT {obj['name']} aponta para target inexistente: {target}")


def clear_output():
    name = "TEMPO_ENGINE_OUTPUT"
    old = bpy.data.collections.get(name)
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)

    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def material_rgb(name, rgb):
    mat_name = f"MAT_{name}_{rgb[0]}_{rgb[1]}_{rgb[2]}"
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.diffuse_color = (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1)
    return mat


def solid_from_polyline(spec, collection):
    name = spec["name"]
    pts = []
    for p in spec["points"]:
        pair = (float(p[0]), float(p[1]))
        if pair not in pts:
            pts.append(pair)

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    bm = bmesh.new()
    try:
        verts = [bm.verts.new((x, y, float(spec["base_z"]))) for x, y in pts]
        face = bm.faces.new(verts)
        bmesh.ops.recalc_face_normals(bm, faces=[face])

        ext = bmesh.ops.extrude_face_region(bm, geom=[face])
        ext_verts = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=ext_verts, vec=(0, 0, float(spec["extrude"])))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

        bm.to_mesh(mesh)
        mesh.update()
        return obj
    except Exception as exc:
        fail(f"Falha ao criar sólido {name}: {exc}")
    finally:
        bm.free()


def boolean_difference(base, cutter):
    backup = list(base.data.materials)
    mod = base.modifiers.new(name=f"BOOL_{cutter.name}", type="BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = base
    base.select_set(True)

    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception as exc:
        fail(f"Boolean falhou: {base.name} x {cutter.name}: {exc}")

    base.data.materials.clear()
    for mat in backup:
        base.data.materials.append(mat)


def run_engine(data):
    validate(data)
    col = clear_output()

    bases = {}
    cuts = {}
    log = {"bases": [], "cuts": [], "booleans": []}

    for spec in data["objects"]:
        if spec["role"] == "BASE":
            obj = solid_from_polyline(spec, col)
            obj.data.materials.append(material_rgb(spec["name"], spec["color"]))
            bases[spec["name"]] = obj
            log["bases"].append(spec["name"])

    for spec in data["objects"]:
        if spec["role"] == "CUT":
            obj = solid_from_polyline(spec, col)
            cuts[spec["name"]] = obj
            log["cuts"].append(spec["name"])

    for spec in data["objects"]:
        if spec["role"] == "CUT":
            cutter = cuts[spec["name"]]
            for target in spec["target"]:
                boolean_difference(bases[target], cutter)
                log["booleans"].append({"cut": spec["name"], "target": target})

    for obj in cuts.values():
        obj.hide_set(True)
        obj.hide_render = True

    print("\n=== TEMPO ENGINE / ESPP — FÊNIX CORE V01 ===")
    print(log)
    print("Execução concluída.\n")
    return log


run_engine(DATA)
