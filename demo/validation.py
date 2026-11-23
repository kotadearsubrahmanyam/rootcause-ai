"""Validation of stock-contract changes in the demo store only."""
import ast
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from threading import Lock

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()
gate = Lock()
FILES = ("inventory.py", "service.py")
REVISION = subprocess.check_output(["git", "-C", "/store", "rev-parse", "HEAD"], text=True).strip()


class Proposal(BaseModel):
    revision: str
    patch: str = Field(max_length=8000)


def apply_hunk(directory, patch):
    """Accept one uniquely matching hunk, including the abbreviated @@ used by some models."""
    lines = patch.strip("\n").splitlines()
    if lines and lines[0].startswith("```") and lines[-1] == "```":
        lines = lines[1:-1]
    while lines and lines[0].startswith(("diff --git ", "index ")):
        lines.pop(0)
    if len(lines) < 4:
        raise ValueError("The proposal must contain a unified diff.")
    name = lines[0].removeprefix("--- a/")
    if name not in FILES or lines[0] != "--- a/" + name or lines[1] != "+++ b/" + name:
        raise ValueError("The demo accepts one patch to inventory.py or service.py.")
    if not re.fullmatch(r"@@(?: -\d+(?:,\d+)? \+\d+(?:,\d+)? @@.*)?", lines[2]):
        raise ValueError("Invalid patch header.")
    hunk = lines[3:]
    if any(not line or line[0] not in " +-" for line in hunk):
        raise ValueError("The demo requires a single contiguous change.")
    old = [line[1:] for line in hunk if line[0] != "+"]
    new = [line[1:] for line in hunk if line[0] != "-"]
    if not old or not new or not any(line.startswith("-") for line in hunk):
        raise ValueError("A replacement hunk is required.")
    path = directory / name
    original = path.read_text()
    source = original.splitlines()
    def normalized(block):
        return textwrap.dedent("\n".join(block)).strip("\n")
    hits = [i for i in range(len(source)-len(old)+1)
            if normalized(source[i:i+len(old)]) == normalized(old)]
    if len(hits) != 1:
        raise ValueError("Patch context does not uniquely match this release.")
    i = hits[0]
    def margin(block):
        return min(len(line)-len(line.lstrip(" ")) for line in block if line.strip())
    shift = margin(source[i:i+len(old)]) - margin(old)
    replacement = [(" " * shift + line if shift >= 0 else line[-shift:]) if line else "" for line in new]
    updated = "\n".join(source[:i] + replacement + source[i+len(old):]) + "\n"
    check_change(name, original, updated)
    path.write_text(updated)


def stock_expression(node):
    if isinstance(node, ast.Constant):
        return type(node.value) in (int, str, bool) and len(str(node.value)) < 80
    if isinstance(node, ast.Name):
        return node.id in {"qty", "quantity", "body"}
    if isinstance(node, ast.Dict):
        return all(stock_expression(v) for v in [*node.keys, *node.values])
    if isinstance(node, ast.Compare):
        return len(node.ops) == 1 and isinstance(node.ops[0], (ast.Gt, ast.In)) and all(
            stock_expression(v) for v in [node.left, *node.comparators])
    if isinstance(node, ast.IfExp):
        return all(stock_expression(v) for v in (node.test, node.body, node.orelse))
    if isinstance(node, ast.Subscript):
        return isinstance(node.value, ast.Name) and node.value.id == "body" and stock_expression(node.slice)
    if isinstance(node, ast.Call):
        return (isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "body"
                and 1 <= len(node.args) <= 2 and not node.keywords and all(map(stock_expression, node.args)))
    return False


def check_change(name, original, updated):
    old = ast.parse(original)
    new = ast.parse(updated)
    if name == "inventory.py":
        if len(new.body) == 1 and isinstance(new.body[0], ast.FunctionDef):
            statements = new.body[0].body
            if len(statements) == 2 and isinstance(statements[0], ast.Assign):
                assignment = statements[0]
                if (len(assignment.targets) == 1 and isinstance(assignment.targets[0], ast.Name)
                        and assignment.targets[0].id in {"qty", "quantity"}
                        and isinstance(assignment.value, ast.Constant) and type(assignment.value.value) is int):
                    statements = statements[1:]
            if (len(statements) == 1 and isinstance(statements[0], ast.Return)
                    and isinstance(statements[0].value, ast.Dict) and stock_expression(statements[0].value)):
                new.body[0].body = old.body[0].body
    else:
        # Only the stock calculation in the existing Orders exception handler is editable.
        old_try, = [n for n in ast.walk(old) if isinstance(n, ast.Try)]
        candidates = [n for n in ast.walk(new) if isinstance(n, ast.Try)]
        if len(candidates) == 1:
            target = candidates[0]
            if (1 <= len(target.body) <= 4 and all(isinstance(s, ast.Assign) and len(s.targets)==1
                    and isinstance(s.targets[0], ast.Name) and s.targets[0].id in {"qty","quantity","body"}
                    and stock_expression(s.value) for s in target.body)):
                target.body = old_try.body
    if ast.dump(old) != ast.dump(new):
        raise ValueError("The change exceeds the supported demo stock calculation.")


def run_tests(directory):
    result = subprocess.run([sys.executable,"-m","pytest","-q","--tb=short","-p","no:cacheprovider","test_checkout.py"],
                            cwd=directory, capture_output=True, text=True, timeout=18,
                            env={**os.environ,"STORE_SERVICE":"checkout","PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1","PYTHONDONTWRITEBYTECODE":"1"})
    return {"exit_code": result.returncode, "output": (result.stdout + result.stderr)[-6000:]}


@app.post("/validate")
def validate(proposal: Proposal):
    if proposal.revision != REVISION:
        return {"status":"unavailable", "message":"This runner has a different demo release. Generate a new checkout and investigation."}
    if not gate.acquire(blocking=False):
        raise HTTPException(409, "Runner is busy. Retry in a moment.")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in FILES:
                shutil.copyfile(Path("/store") / name, directory / name)
            shutil.copyfile("/checks/test_checkout.py", directory / "test_checkout.py")
            (directory/".git").symlink_to("/store/.git", target_is_directory=True)
            before = run_tests(directory)
            if before["exit_code"] != 1 or "test_deployed_checkout" not in before["output"]:
                return {"status":"inconclusive","before":before,"message":"Could not reproduce the expected checkout failure."}
            try:
                apply_hunk(directory, proposal.patch)
            except (ValueError, SyntaxError) as error:
                return {"status":"unapplied","before":before,"message":str(error)}
            after = run_tests(directory)
            return {"status":"passed" if after["exit_code"] == 0 else "failed","before":before,"after":after}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "The validation test timed out.")
    finally:
        gate.release()
