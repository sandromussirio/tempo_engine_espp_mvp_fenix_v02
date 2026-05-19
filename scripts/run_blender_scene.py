# ============================================================
# TEMPO ENGINE / ESPP — RUN BLENDER SCENE
# Arquivo de entrada para rodar o MVP Fênix no Blender.
#
# Uso:
# 1. Abra este arquivo no Blender:
#    Scripting > Text > Open > run_blender_scene.py
# 2. Clique em Run Script.
#
# Estrutura esperada:
#
# tempo-engine-espp-mvp-fenix/
# ├── run_blender_scene.py
# ├── engine/
# │   └── tempo_engine.py
# └── examples/
#     └── input_scene_room_test_v01.json
# ============================================================

from pathlib import Path
import sys


# ============================================================
# RESOLVER PASTA DO PROJETO
# ============================================================

def find_project_root():
    """
    Tenta descobrir a pasta raiz do projeto.

    Quando rodado como arquivo aberto no Blender, __file__ costuma funcionar.
    Quando rodado como Text interno, pode falhar. Nesse caso, usa a pasta do .blend.
    """

    # Caso 1: script salvo em arquivo .py
    try:
        current_file = Path(__file__).resolve()
        return current_file.parent
    except Exception:
        pass

    # Caso 2: arquivo .blend salvo na raiz do projeto
    try:
        import bpy
        blend_dir = Path(bpy.path.abspath("//")).resolve()
        return blend_dir
    except Exception:
        pass

    # Caso 3: fallback
    return Path.cwd().resolve()


PROJECT_ROOT = find_project_root()
ENGINE_DIR = PROJECT_ROOT / "engine"
INPUT_JSON = PROJECT_ROOT / "examples" / "input_scene_room_test_v01.json"


# ============================================================
# PREPARAR IMPORT DO MOTOR
# ============================================================

if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))


try:
    from tempo_engine import load_json, run_engine
except Exception as exc:
    raise RuntimeError(
        "Não foi possível importar o motor.\n"
        f"PROJECT_ROOT: {PROJECT_ROOT}\n"
        f"ENGINE_DIR: {ENGINE_DIR}\n"
        "Verifique se existe o arquivo:\n"
        "engine/tempo_engine.py\n"
        f"Erro original: {exc}"
    )


# ============================================================
# EXECUTAR CENA
# ============================================================

if not INPUT_JSON.exists():
    raise FileNotFoundError(
        "Arquivo JSON de exemplo não encontrado.\n"
        f"Esperado em: {INPUT_JSON}\n"
        "Verifique se existe:\n"
        "examples/input_scene_room_test_v01.json"
    )


data = load_json(str(INPUT_JSON))
run_engine(data)

print("\nrun_blender_scene.py executado com sucesso.")
print(f"Projeto: {PROJECT_ROOT}")
print(f"JSON: {INPUT_JSON}")
