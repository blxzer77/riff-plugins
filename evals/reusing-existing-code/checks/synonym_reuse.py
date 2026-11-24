#!/usr/bin/env python3
"""Pass when register_member gets its normalization from app/core/identity.py instead of
re-implementing it: its module imports from app.core.identity and not unicodedata."""
import ast

from reuse_lib import finish, trees

failures, owner = [], None
for rel, tree in trees().items():
    if any(isinstance(n, ast.FunctionDef) and n.name == "register_member" for n in ast.walk(tree)):
        owner = (rel, tree)
if owner is None:
    finish(["register_member is not defined under app/"], "")
rel, tree = owner
imports_identity = any(isinstance(n, ast.ImportFrom) and (n.module or "") in ("app.core.identity", "app.core")
                       or isinstance(n, ast.Import) and any(a.name == "app.core.identity" for a in n.names)
                       for n in ast.walk(tree))
imports_unicodedata = any(isinstance(n, ast.Import) and any(a.name == "unicodedata" for a in n.names)
                          or isinstance(n, ast.ImportFrom) and n.module == "unicodedata"
                          for n in ast.walk(tree))
if not imports_identity:
    failures.append(f"{rel} does not import from app.core.identity")
if imports_unicodedata:
    failures.append(f"{rel} re-implements normalization (imports unicodedata)")
finish(failures, f"{rel} reuses app.core.identity")
