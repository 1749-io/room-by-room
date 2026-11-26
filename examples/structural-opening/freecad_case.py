"""Build and read the fictional FEM example in the live FreeCAD MCP desktop."""

import json
import os
import re
import shutil
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import ObjectsFem
from femtools.ccxtools import FemToolsCcx


def solve_scratch(scratch_dir):
    root = Path(scratch_dir)
    c = json.loads((root / "case.json").read_text(encoding="utf-8-sig"))
    assert c["title"].startswith("Fictional kitchen opening")
    doc = App.newDocument("ScratchOpeningSolver")
    doc.Label = "Fictional opening | solver benchmark"
    b, h, L = c["width_mm"], c["depth_mm"], c["span_mm"]
    item = doc.addObject("Part::Box", "IdealisedMember")
    item.Label = f"Assumed test prism | {L} x {b} x {h} mm"
    item.Length = L
    item.Width = b
    item.Height = h
    item.Placement.Base = App.Vector(0, -b / 2, -h / 2)
    analysis = ObjectsFem.makeAnalysis(doc, "ScratchAnalysis")
    analysis.Label = "Linear static | assumed inputs"
    solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "Calculix")
    analysis.addObject(solver)
    doc.recompute()
    runner = FemToolsCcx(analysis=analysis, solver=solver)
    executable = "ccx.exe" if os.name == "nt" else "ccx"
    bundled = Path(App.getHomePath()) / "bin" / executable
    configured = App.ParamGet(
        "User parameter:BaseApp/Preferences/Mod/Fem/Ccx"
    ).GetString("ccxBinaryPath", "")
    binary = configured or (
        str(bundled) if bundled.is_file() else shutil.which(executable)
    )
    runner.setup_ccx(binary)
    assert runner.ccx_binary_present
    for label in ("coarse", "fine"):
        folder = root / "calculix" / label
        runner.working_dir = str(folder)
        runner.inp_file_name = str(folder / "opening.inp")
        code = runner.start_ccx()
        (folder / "solver.log").write_text(
            runner.ccx_stdout + "\n" + runner.ccx_stderr, encoding="utf-8"
        )
        assert code == 0 and "Job finished" in runner.ccx_stdout, (
            label,
            code,
            runner.ccx_stdout[-1000:],
            runner.ccx_stderr,
        )
        assert (folder / "opening.frd").stat().st_size > 1000
    runner.load_results_ccxfrd()
    result = next(
        obj for obj in analysis.Group if obj.isDerivedFrom("Fem::FemResultObject")
    )
    result.Label = "Fine mesh | displacement and stresses"
    analysis.addProperty("App::PropertyString", "InputBasis", "Benchmark")
    analysis.InputBasis = "Synthetic pin and roller benchmark. Geometry, elastic constants and load are assumed. See case.json and calculix/fine/opening.inp to repeat this solve."
    analysis.addProperty("App::PropertyString", "InputDeck", "Benchmark")
    analysis.InputDeck = "calculix/fine/opening.inp"
    doc.recompute()
    if App.GuiUp:
        item.ViewObject.Visibility = False
        result.Mesh.ViewObject.Visibility = True
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    doc.saveAs(str(root / "Scratch opening.FCStd"))


def reopen_and_measure(root):
    target = root / "Scratch opening.FCStd"
    doc = next(
        o
        for o in App.listDocuments().values()
        if o.FileName and Path(o.FileName).resolve() == target
    )
    log = (root / "calculix/fine/solver.log").read_text(encoding="utf-8")
    ccx_version = re.search(r"CalculiX Version\s+([^, ]+)", log).group(1)
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(target))
    result = next(
        obj
        for obj in reopened.ScratchAnalysis.Group
        if obj.isDerivedFrom("Fem::FemResultObject")
    )
    mesh = result.Mesh.FemMesh
    case = json.loads((root / "case.json").read_text())
    mid_x, half_depth = case["span_mm"] / 2, case["depth_mm"] / 2

    def result_index(z):
        point = App.Vector(mid_x, 0, z)
        return next(
            i
            for i, node in enumerate(result.NodeNumbers)
            if mesh.getNodeById(node).distanceToPoint(point) < 0.001
        )

    measured = {
        "FreeCAD": ".".join(App.Version()[:3]),
        "CalculiX": ccx_version,
        "document": target.name,
        "solid_elements": mesh.VolumeCount,
        "nodes": mesh.NodeCount,
        "mid_vertical_mm": result.DisplacementVectors[result_index(0)].z,
        "mid_top_Sxx_MPa": result.NodeStressXX[result_index(half_depth)],
        "mid_bottom_Sxx_MPa": result.NodeStressXX[result_index(-half_depth)],
    }
    (root / "freecad-readback.json").write_text(json.dumps(measured, indent=2) + "\n")
