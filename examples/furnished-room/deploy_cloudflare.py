"""Build a fresh, complete public site and upload it to the existing Pages project."""
from argparse import ArgumentParser
from pathlib import Path
import runpy
import shutil
import subprocess
from tempfile import TemporaryDirectory

if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--wrangler", default="wrangler", help="Wrangler CLI executable or wrangler.js entry point")
    args = parser.parse_args()
    entry = Path(args.wrangler)
    if entry.suffix == ".js" and entry.is_file():
        command = [shutil.which("node"), str(entry.resolve())]
    else:
        command = [shutil.which(args.wrangler)]
    if not command[0]:
        parser.error("Install Wrangler or pass its executable with --wrangler")
    build = runpy.run_path(str(Path(__file__).with_name("build_site.py")))["build"]
    with TemporaryDirectory() as scratch:
        stage = Path(scratch) / "site"
        build(stage)
        subprocess.run([*command, "pages", "deploy", str(stage), "--project-name", "roombyroom",
                        "--branch", "gh-pages"], cwd=scratch, check=True)
