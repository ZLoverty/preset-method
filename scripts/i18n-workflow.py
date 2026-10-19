"""Small, repository-aware wrapper around the ``sop_i18n`` workflow."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORDER = Path("sop/pdf-order.txt")
MEMORY = Path("i18n/memory/zh-CN.json")
GLOSSARY = Path("i18n/glossary.json")
DOTENV = ROOT / ".env"


def env_value(name: str) -> str | None:
    """Read an environment variable, falling back to a simple .env entry."""
    value = os.getenv(name)
    if value:
        return value
    if not DOTENV.is_file():
        return None
    for line in DOTENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("\"'")
    return None


def run(*args: str) -> None:
    try:
        subprocess.run([sys.executable, "-m", "sop_i18n", *args], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from None


def run_name(value: str | None) -> str:
    value = value or env_value("I18N_RUN_NAME") or datetime.now().strftime("run-%Y%m%d-%H%M%S")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.name != value:
        raise SystemExit("run name must be a simple directory name")
    return value


def run_dir(name: str) -> Path:
    return Path("tmp/i18n-runs") / name


def plan(args: argparse.Namespace) -> None:
    name = run_name(args.run_name)
    directory = run_dir(name)
    directory.mkdir(parents=True, exist_ok=True)
    command = [
        "translate", "plan", "--order-file", str(ORDER), "--memory", str(MEMORY),
        "--glossary", str(GLOSSARY), "--out", str(directory / "translation-jobs.json"),
    ]
    if args.force:
        command.append("--force")
    run(*command)
    print(f"run: {name}\njobs: {directory / 'translation-jobs.json'}")


def translate(args: argparse.Namespace) -> None:
    name = run_name(args.run_name)
    directory = run_dir(name)
    directory.mkdir(parents=True, exist_ok=True)
    command = [
        "translate", "run", "--jobs", str(directory / "translation-jobs.json"),
        "--run-dir", str(directory), "--model", args.model, "--glossary", str(GLOSSARY),
    ]
    if args.endpoint:
        command += ["--endpoint", args.endpoint]
    if args.env_file:
        command += ["--env-file", args.env_file]
    run(*command)


def check(args: argparse.Namespace) -> None:
    directory = run_dir(run_name(args.run_name))
    directory.mkdir(parents=True, exist_ok=True)
    run(
        "translate", "check", "--jobs", str(directory / "translation-jobs.json"),
        "--candidates", str(directory / "candidates.json"), "--glossary", str(GLOSSARY),
        "--out", str(directory / "checked-candidates.json"), "--force",
    )


def review(args: argparse.Namespace) -> None:
    directory = run_dir(run_name(args.run_name))
    run(
        "review", "--jobs", str(directory / "translation-jobs.json"),
        "--candidates", str(directory / "checked-candidates.json"), "--memory", str(MEMORY),
        "--glossary", str(GLOSSARY), "--port", str(args.port),
    )


def import_drafts(args: argparse.Namespace) -> None:
    directory = run_dir(run_name(args.run_name))
    run(
        "translate", "import-drafts", "--jobs", str(directory / "translation-jobs.json"),
        "--candidates", str(directory / "checked-candidates.json"), "--memory", str(MEMORY),
        "--glossary", str(GLOSSARY), "--only-passing",
    )


def build_check(args: argparse.Namespace) -> None:
    directory = run_dir(run_name(args.run_name))
    directory.mkdir(parents=True, exist_ok=True)
    run(
        "build", "--check-only", "--translation-policy", "strict", "--order-file", str(ORDER),
        "--memory", str(MEMORY), "--report", str(directory / "strict-report.json"),
    )


def build(args: argparse.Namespace) -> None:
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "dist/i18n").mkdir(parents=True, exist_ok=True)
    command = [
        "build", "--translation-policy", "strict", "--order-file", str(ORDER),
        "--memory", str(MEMORY), "--output", args.output, "--report", "dist/i18n/zh-CN-report.json",
    ]
    if args.version:
        command += ["--version", args.version]
    run(*command)


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the repository i18n workflow with shared defaults.")
    sub = parser.add_subparsers(dest="command", required=True)

    command = sub.add_parser("plan", help="create translation jobs")
    command.add_argument("--run-name")
    command.add_argument("--force", action="store_true")
    command.set_defaults(func=plan)

    command = sub.add_parser("run", help="call the configured translation provider")
    command.add_argument("--run-name")
    command.add_argument("--model", default=env_value("I18N_MODEL"), required=not env_value("I18N_MODEL"))
    command.add_argument("--endpoint", default=env_value("I18N_ENDPOINT"))
    command.add_argument("--env-file", default=".env")
    command.set_defaults(func=translate)

    for name, function in (("check", check), ("review", review), ("import", import_drafts), ("build-check", build_check)):
        command = sub.add_parser(name)
        command.add_argument("--run-name", required=True)
        if name == "review":
            command.add_argument("--port", type=int, default=8765)
        command.set_defaults(func=function)

    command = sub.add_parser("build", help="strictly build the Chinese PDF")
    command.add_argument("--output", default="dist/sop-zh-CN.pdf")
    command.add_argument("--version")
    command.set_defaults(func=build)
    return parser


if __name__ == "__main__":
    args = parser().parse_args()
    args.func(args)
