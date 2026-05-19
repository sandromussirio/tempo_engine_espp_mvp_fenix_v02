# ============================================================
# TEMPO ENGINE / ESPP — FÊNIX CORE ENGINE
# Arquivo: engine/tempo_engine.py
#
# Motor genérico validado:
# - lê JSON externo
# - valida contrato ESPP mínimo
# - cria BASES
# - cria CUTS
# - aplica boolean apenas em target explícito
# - oculta CUTs
# - gera log simples
#
# Este arquivo deve ser importado por run_blender_scene.py
# ============================================================

import json
from pathlib import Path

import bpy
import bmesh


# ============================================================
# ERRO DE PROTOCOLO
# ============================================================

class TempoProtocolError(Exception):
    """Erro explícito do protocolo Tempo Engine / ESPP."""
    pass


# ============================================================
# LEITURA DO JSON
# ============================================================

def load_json(path_text):
    path = Path(path_text)

    if not path.exists():
        raise TempoProtocolError(f"Arquivo JSON não encontrado: {path}")

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception as exc:
        raise TempoProtocolError(f"Falha ao ler JSON: {path}. Detalhe: {exc}")

    print(f"JSON carregado: {path}")
    return data


# ============================================================
# VALIDAÇÃO
# ============================================================

def fail(message):
    raise TempoProtocolError(message)


def is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate(data):
    if not isinstance(data, dict):
        fail("A raiz do JSON deve ser um dicionário.")

    if "objects" not in data:
        fail("O JSON deve conter a chave 'objects'.")

    if not isinstance(data["objects"], list):
        fail("'objects' deve ser uma lista.")

    if not data["objects"]:
        fail("'objects' não pode estar vazio.")

    names = set()
    base_names = set()

    for obj in data["objects"]:
        if not isinstance(obj, dict):
            fail("Cada item em 'objects' deve ser um dicionário.")

        name = obj.get("name")
        role = obj.get("role")

        if not isinstance(name, str) or not name.strip():
            fail("Objeto sem 'name' válido.")

        if name in names:
            fail(f"Nome duplicado: {name}")

        names.add(name)

        if role not in ("BASE", "CUT"):
            fail(f"Role inválido em {name}. Use BASE ou CUT.")

        if obj.get("type") != "POLYLINE":
            fail(f"Type inválido em {name}. Nesta versão use POLYLINE.")

        if not isinstance(obj.get("category"), str) or not obj.get("category").strip():
            fail(f"Category inválida em {name}.")

        points = obj.get("points")

        if not isinstance(points, list) or len(points) < 3:
            fail(f"Points inválido em {name}. Use lista com pelo menos 3 pontos.")

        for point in points:
            if not isinstance(point, list) or len(point) != 2:
                fail(f"Ponto inválido em {name}. Use apenas [x, y].")

            if not is_num(point[0]) or not is_num(point[1]):
                fail(f"Coordenadas inválidas em {name}. Use números em [x, y].")

        if len({tuple(point) for point in points}) < 3:
            fail(f"{name} precisa de pelo menos 3 pontos únicos.")

        if not is_num(obj.get("base_z")):
            fail(f"base_z inválido em {name}.")

        if not is_num(obj.get("extrude")) or obj["extrude"] <= 0:
            fail(f"extrude inválido em {name}. Use número maior que zero.")

        if role == "BASE":
            color = obj.get("color")

            if not isinstance(color, list) or len(color) != 3:
                fail(f"BASE {name} precisa de color [r, g, b].")

            for value in color:
                if not isinstance(value, int) or not 0 <= value <= 255:
                    fail(f"Color inválido em {name}. Use inteiros RGB entre 0 e 255.")

            base_names.add(name)

        if role == "CUT":
            target = obj.get("target")

            if not isinstance(target, list) or not target:
                fail(f"CUT {name} precisa de target.")

            for target_name in target:
                if not isinstance(target_name, str) or not target_name.strip():
                    fail(f"Target inválido em CUT {name}.")

    for obj in data["objects"]:
        if obj["role"] == "CUT":
            for target_name in obj["target"]:
                if target_name not in base_names:
                    fail(
                        f"CUT {obj['name']} aponta para target inexistente "
                        f"ou não-BASE: {target_name}"
                    )


# ============================================================
# BLENDER — LIMPEZA DA SAÍDA
# ============================================================

def clear_output(collection_name="TEMPO_ENGINE_OUTPUT"):
    old_collection = bpy.data.collections.get(collection_name)

    if old_collection:
        for obj in list(old_collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

        bpy.data.collections.remove(old_collection)

    collection = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(collection)
    return collection


# ============================================================
# BLENDER — MATERIAL
# ============================================================

def material_rgb(name, rgb):
    mat_name = f"MAT_{name}_{rgb[0]}_{rgb[1]}_{rgb[2]}"
    material = bpy.data.materials.get(mat_name)

    if material is None:
        material = bpy.data.materials.new(mat_name)

    material.diffuse_color = (
        rgb[0] / 255,
        rgb[1] / 255,
        rgb[2] / 255,
        1
    )

    return material


# ============================================================
# BLENDER — GEOMETRIA
# ============================================================

def sanitize_points(points):
    clean = []

    for point in points:
        pair = (float(point[0]), float(point[1]))

        if pair not in clean:
            clean.append(pair)

    return clean


def solid_from_polyline(spec, collection):
    name = spec["name"]
    points = sanitize_points(spec["points"])

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    bm = bmesh.new()

    try:
        verts = [
            bm.verts.new((x, y, float(spec["base_z"])))
            for x, y in points
        ]

        face = bm.faces.new(verts)
        bmesh.ops.recalc_face_normals(bm, faces=[face])

        extruded = bmesh.ops.extrude_face_region(bm, geom=[face])
        extruded_verts = [
            geom
            for geom in extruded["geom"]
            if isinstance(geom, bmesh.types.BMVert)
        ]

        bmesh.ops.translate(
            bm,
            verts=extruded_verts,
            vec=(0, 0, float(spec["extrude"]))
        )

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

        bm.to_mesh(mesh)
        mesh.update()
        return obj

    except Exception as exc:
        fail(f"Falha ao criar sólido {name}: {exc}")

    finally:
        bm.free()


# ============================================================
# BLENDER — BOOLEAN
# ============================================================

def boolean_difference(base, cutter):
    if base == cutter:
        fail("Base e cutter não podem ser o mesmo objeto.")

    material_backup = list(base.data.materials)

    modifier = base.modifiers.new(
        name=f"BOOL_{cutter.name}",
        type="BOOLEAN"
    )

    modifier.operation = "DIFFERENCE"
    modifier.object = cutter
    modifier.solver = "EXACT"

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = base
    base.select_set(True)

    try:
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    except Exception as exc:
        fail(f"Boolean falhou: {base.name} x {cutter.name}. Detalhe: {exc}")

    base.data.materials.clear()

    for material in material_backup:
        base.data.materials.append(material)


# ============================================================
# MOTOR — ORQUESTRADOR
# ============================================================

def run_engine(data):
    """
    Ordem interna fixa:

    1. Validar JSON
    2. Limpar/criar collection de saída
    3. Criar todos os objetos BASE
    4. Criar todos os objetos CUT
    5. Aplicar boolean apenas nos targets explícitos
    6. Ocultar CUTs
    7. Gerar log simples
    """

    validate(data)
    collection = clear_output()

    bases = {}
    cuts = {}

    log = {
        "bases": [],
        "cuts": [],
        "booleans": []
    }

    # 1. Criar BASES primeiro
    for spec in data["objects"]:
        if spec["role"] == "BASE":
            obj = solid_from_polyline(spec, collection)
            obj.data.materials.append(material_rgb(spec["name"], spec["color"]))

            bases[spec["name"]] = obj
            log["bases"].append(spec["name"])

    # 2. Criar CUTS depois
    for spec in data["objects"]:
        if spec["role"] == "CUT":
            obj = solid_from_polyline(spec, collection)

            cuts[spec["name"]] = obj
            log["cuts"].append(spec["name"])

    # 3. Aplicar boolean somente nos targets explícitos
    for spec in data["objects"]:
        if spec["role"] == "CUT":
            cutter = cuts[spec["name"]]

            for target_name in spec["target"]:
                base = bases[target_name]
                boolean_difference(base, cutter)

                log["booleans"].append({
                    "cut": spec["name"],
                    "target": target_name
                })

    # 4. Ocultar CUTS após uso
    for obj in cuts.values():
        obj.hide_set(True)
        obj.hide_render = True

    print("\n=== TEMPO ENGINE / ESPP — FÊNIX CORE ENGINE ===")
    print(log)
    print("Execução concluída.\n")

    return log
