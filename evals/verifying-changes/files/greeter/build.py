"""Bundle src/greeter into build/greeter.pyz."""

import shutil
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
    shutil.copytree(ROOT / "src" / "greeter", Path(tmp) / "greeter")
    (Path(tmp) / "__main__.py").write_text("import runpy\nrunpy.run_module('greeter', run_name='__main__')\n")
    (ROOT / "build").mkdir(exist_ok=True)
    zipapp.create_archive(tmp, ROOT / "build" / "greeter.pyz", interpreter="/usr/bin/env python3")
print("built build/greeter.pyz")
