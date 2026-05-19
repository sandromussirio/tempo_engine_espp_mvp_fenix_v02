from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "scripts" / "run_blender_scene.py"

runpy.run_path(str(TARGET), run_name="__main__")
