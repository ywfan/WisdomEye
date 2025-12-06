import os
import shutil
from pathlib import Path


def ensure_dir(p: str) -> str:
    Path(p).mkdir(parents=True, exist_ok=True)
    return p


def make_output_root() -> str:
    root = Path.cwd() / "output"
    ensure_dir(str(root))
    return str(root)


def slugify(name: str) -> str:
    s = name.strip().replace(" ", "_")
    s = "".join(ch for ch in s if ch.isalnum() or ch in {"_", "-"})
    return s or "resume"


def create_resume_folder(input_path: str) -> str:
    root = make_output_root()
    base = Path(input_path).stem
    folder = Path(root) / slugify(base)
    ensure_dir(str(folder))
    return str(folder)


def write_text(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")
