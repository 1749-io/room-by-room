"""Replay the fictional opening from inputs in this checkout and verify its handovers."""

import argparse
import asyncio
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXAMPLE = Path(__file__).resolve().parent


def mcp_command(explicit):
    name = "freecad-mcp.exe" if os.name == "nt" else "freecad-mcp"
    default = Path.home() / ".local" / "bin" / name
    binary = shutil.which(explicit or name)
    if not explicit and not binary and default.is_file():
        binary = str(default)
    if not binary:
        raise SystemExit(
            "Cannot find freecad-mcp. Supply --mcp-command with its executable path."
        )
    return binary


async def solve_and_reopen(output, command):
    source = (EXAMPLE / "freecad_case.py").read_text(encoding="utf-8")
    # The connector receives source text; only the output directory has to be shared with FreeCAD.
    code = source + f"\nroot = Path({str(output)!r})\n"
    async with (
        stdio_client(StdioServerParameters(command=command)) as (reader, writer),
        ClientSession(reader, writer) as session,
    ):
        await session.initialize()
        for label, action in (
            ("Solve", "solve_scratch(root)"),
            ("Reopen", "reopen_and_measure(root)"),
        ):
            response = await session.call_tool(
                "execute_code",
                {
                    "code": code + action,
                    "include_screenshot": False,
                    "timeout": 120,
                },
            )
            if response.is_error:
                detail = "\n".join(
                    block.text for block in response.content if block.type == "text"
                )
                raise RuntimeError(f"{label} failed through FreeCAD MCP: {detail}")
            print(f"{label} completed through FreeCAD MCP.", flush=True)


def verify(output):
    def load(folder, name):
        return json.loads((folder / name).read_text(encoding="utf-8"))

    expected = load(EXAMPLE / "reference", "results.json")
    actual = load(output, "verified-results.json")
    native = load(output, "freecad-readback.json")
    # The reference comes from the independently saved original scratch run.
    # Numeric comparisons allow for solver and platform rounding.
    for group in ("hand", "pynite", "calculix"):
        pairs = [(actual[group], expected[group])]
        if group == "calculix":
            pairs = [
                (actual[group][mesh], expected[group][mesh])
                for mesh in ("coarse", "fine")
            ]
        for measured, recorded in pairs:
            for key, value in recorded.items():
                if isinstance(value, (int, float)) and not math.isclose(
                    measured[key], value, rel_tol=1e-4, abs_tol=1e-7
                ):
                    raise ValueError(
                        f"{group}.{key}: replay gave {measured[key]}, reference {value}"
                    )
    fine = actual["calculix"]["fine"]
    for key, value in {
        "nodes": fine["nodes"],
        "solid_elements": fine["elements"],
        "mid_vertical_mm": -fine["down_mm"],
        "mid_top_Sxx_MPa": fine["mid_top_Sxx_MPa"],
        "mid_bottom_Sxx_MPa": fine["mid_bottom_Sxx_MPa"],
    }.items():
        if not math.isclose(native[key], value, rel_tol=0, abs_tol=1e-5):
            raise ValueError(
                f"Reopened FreeCAD {key}: {native[key]}, raw CalculiX {value}"
            )
    print(
        f"PASS: PyNite {actual['pynite']['version']}, FreeCAD {native['FreeCAD']}, "
        f"CalculiX {native['CalculiX']}. Fine mesh deflection {fine['down_mm']:.5f} mm."
    )
    print(f"Run files: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, type=Path, help="A new scratch directory"
    )
    parser.add_argument(
        "--mcp-command", help="Path to the installed freecad-mcp executable"
    )
    args = parser.parse_args()
    command = mcp_command(args.mcp_command)
    output = args.output.expanduser().resolve()
    # Each replay owns its directory. A retry cannot use an earlier solver's files.
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.mkdir()
    except FileExistsError:
        parser.exit(
            2, f"Output already exists. Choose a new scratch directory: {output}\n"
        )
    shutil.copyfile(EXAMPLE / "case.json", output / "case.json")
    subprocess.run(
        [sys.executable, "-E", str(EXAMPLE / "prepare.py"), str(output)], check=True
    )
    asyncio.run(solve_and_reopen(output, command))
    subprocess.run(
        [sys.executable, "-E", str(EXAMPLE / "compare.py"), str(output)], check=True
    )
    verify(output)


if __name__ == "__main__":
    main()
