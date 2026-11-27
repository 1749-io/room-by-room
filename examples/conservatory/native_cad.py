"""Run build(root) in the FreeCAD MCP console with the example directory."""
def build(root):
    import FreeCAD as App
    import Part, runpy, json
    from pathlib import Path
    root = Path(root)
    doc = App.newDocument("OrchardFoldOF02")
    for name,mat,x,y,z,sx,sy,sz in runpy.run_path(str(root/"layout.py"))["pieces"]():
        obj=doc.addObject("Part::Box","Element")
        obj.Label=name
        obj.Length,obj.Width,obj.Height=sx*1000,sy*1000,sz*1000
        obj.Placement.Base=App.Vector((x-sx/2)*1000,(y-sy/2)*1000,z*1000)
        obj.Placement=App.Placement(App.Vector((x-sx/2)*1000,(y-sy/2)*1000,z*1000),App.Rotation())
    doc.recompute()
    path=root/"reference"/"Orchard-Fold.FCStd"
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    doc=App.openDocument(str(path))
    bounds=lambda label: doc.getObjectsByLabel(label)[0].Shape.BoundBox
    floor=bounds("Terracotta floor")
    head=bounds("Sliding doorway head")
    seat=bounds("Upholstered chair seat")
    assert floor.XLength==5400 and floor.YLength==3600 and head.ZMin==2100
    assert abs(seat.Center.x-3200)<1
    report={"design":"OF-02","floor_mm":[floor.XLength,floor.YLength],
            "north_sliding_threshold_mm":[head.XLength,head.ZMin],
            "clear_route_north_of_occupied_table_mm":round(3480-(1450+430+350)),
            "seat_centre_mm":[seat.Center.x,seat.Center.y],"objects":len(doc.Objects)}
    (root/"reference"/"geometry.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
