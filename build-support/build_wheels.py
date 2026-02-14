#!/usr/bin/env python3
"""Build and patch wheels into 3rdparty/python/wheels.

Usage:
  python3.9 build-support/build_wheels.py
  python3.9 build-support/build_wheels.py --requirements 3rdparty/python/requirements.txt

Notes:
- Requires a Python 3.9 interpreter (for cp39 wheels).
- Uses pip to build wheels without dependencies.
- Applies local patch rules for known metadata/code issues.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ_DIR = ROOT / "3rdparty" / "python"
WHEEL_DIR = REQ_DIR / "wheels"

# Extra wheels that we build with CPython but are not pinned directly in
# requirements*.txt (e.g. legacy/transitive dependencies).
CPYTHON_REQUIREMENTS = [
    "pykerberos==1.2.1",
    "redis==3.5.3",
    "mesos.interface==0.21.1",
    "compactor==0.2.2",
    "trollius==2.1.post2",
    "tornado==4.1",
]

PATCH_REQUIRES = {
    "pesos": ["futures", "compactor"],
    "twitter_common_concurrent": ["futures"],
    "compactor": ["protobuf"],
    "mesos.interface": ["protobuf"],
}


def parse_requirements(path: Path) -> list[str]:
    reqs: list[str] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r"):
            nested = line.split(None, 1)[1]
            reqs.extend(parse_requirements((path.parent / nested).resolve()))
            continue
        reqs.append(line)
    return reqs


def run_pip_wheel(reqs: list[str]) -> None:
    if not reqs:
        return
    WHEEL_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(WHEEL_DIR)] + reqs
    subprocess.check_call(cmd, cwd=str(ROOT))


def patch_metadata_requires(wheel: Path, remove_deps: list[str]) -> bool:
    with zipfile.ZipFile(wheel, "r") as zf:
        data = {name: zf.read(name) for name in zf.namelist()}

    meta_name = None
    for name in data:
        if name.endswith("METADATA") and ".dist-info/" in name:
            meta_name = name
            break
    if not meta_name:
        return False

    meta = data[meta_name].decode("utf-8")
    lines = meta.splitlines()
    remove_prefixes = tuple(f"Requires-Dist: {dep}" for dep in remove_deps)
    new_lines = [line for line in lines if not line.startswith(remove_prefixes)]
    if new_lines == lines:
        return False

    data[meta_name] = ("\n".join(new_lines) + "\n").encode("utf-8")
    tmp = wheel.with_suffix(".tmp.whl")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in data.items():
            zf.writestr(name, content)
    tmp.replace(wheel)
    return True


def patch_twitter_common_lang(wheel: Path) -> bool:
    path = "twitter/common/lang/__init__.py"
    with zipfile.ZipFile(wheel, "r") as zf:
        if path not in zf.namelist():
            return False
        data = {name: zf.read(name) for name in zf.namelist()}

    text = data[path].decode("utf-8")
    needle = "from io import BytesIO\n\n\n# Singletons\n"
    if needle not in text:
        return False

    replacement = (
        "from io import BytesIO\n\n"
        "try:\n"
        "  BytesIO\n"
        "except NameError:\n"
        "  from io import BytesIO\n\n"
        "# Singletons\n"
    )
    text = text.replace(needle, replacement)
    data[path] = text.encode("utf-8")

    tmp = wheel.with_suffix(".tmp.whl")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in data.items():
            zf.writestr(name, content)
    tmp.replace(wheel)
    return True


def patch_twitter_common_zookeeper(wheel: Path) -> bool:
    path = "twitter/common/zookeeper/kazoo_client.py"
    with zipfile.ZipFile(wheel, "r") as zf:
        if path not in zf.namelist():
            return False
        data = {name: zf.read(name) for name in zf.namelist()}

    text = data[path].decode("utf-8")
    new_text = text.replace("    async = kw.pop('async', True)\n", "    async_ = kw.pop('async', True)\n")
    new_text = new_text.replace("    if async:\n", "    if async_:\n")
    if new_text == text:
        return False

    data[path] = new_text.encode("utf-8")
    tmp = wheel.with_suffix(".tmp.whl")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in data.items():
            zf.writestr(name, content)
    tmp.replace(wheel)
    return True


def patch_wheels() -> None:
    if not WHEEL_DIR.exists():
        return

    for wheel in WHEEL_DIR.glob("*.whl"):
        base = wheel.name
        pkg = base.split("-")[0].replace("_", ".")

        for key, deps in PATCH_REQUIRES.items():
            if pkg == key:
                patch_metadata_requires(wheel, deps)
                break

        if pkg == "twitter.common.lang":
            patch_twitter_common_lang(wheel)
        elif pkg == "twitter.common.zookeeper":
            patch_twitter_common_zookeeper(wheel)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--requirements",
        action="append",
        default=[],
        help="requirements*.txt path (repeatable); defaults to 3rdparty/python/requirements*.txt",
    )
    args = parser.parse_args()

    if args.requirements:
        req_files = [Path(p).resolve() for p in args.requirements]
    else:
        req_files = sorted(REQ_DIR.glob("requirements*.txt"))

    reqs: list[str] = []
    for req_file in req_files:
        reqs.extend(parse_requirements(req_file))
    reqs.extend(CPYTHON_REQUIREMENTS)

    def normalize_req(req: str) -> str:
        name = re.split(r"[<=>\\s]", req, maxsplit=1)[0]
        return name.lower().replace("_", "-")

    # Keep first occurrence of a project name to avoid version conflicts.
    seen: set[str] = set()
    filtered: list[str] = []
    for req in reqs:
        key = normalize_req(req)
        if key in seen:
            continue
        seen.add(key)
        filtered.append(req)
    reqs = filtered

    run_pip_wheel(reqs)
    patch_wheels()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
