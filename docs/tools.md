# Which renovation tools do I need?

Start with the job. A brief, a tender comparison and a bathroom programme run on an ordinary Python installation. A change to a live building model needs the corresponding desktop application and its MCP connection. A fresh clone carries the scripts, examples and shared evidence. Machine installations, authenticated services and private house files have their own readiness checks.

For a highly glazed room, use the [seasonal comfort study](../skills/renovation-pack/references/glazed-rooms.md) to connect map registration, QGIS terrain and surface heights, solar positions and local-weather thermal comparisons to the choice of seat, shade and ventilation.

## Choose the tools for the decision

| Job | Required input and tool | How a fresh agent checks readiness |
| --- | --- | --- |
| Start, resume or review project records | Python 3.11 or 3.12 for the standard-library starter, the repository and the relevant house records | Run `python house.py --help` and `python house.py list`. Restore private files when the requested issue depends on them. For a registered CAD route, install the route dependencies too. |
| Tender or bathroom programme | Python standard library and the written scope, dated quotes or occupied sequence | Run the two standalone commands below. For a live commission use the actual quotes, routes and service evidence. A spreadsheet or OpenProject can be an output when requested. |
| Occupied CAD route | Python environment with Shapely and NetworkX from the [route requirements](../requirements/routes.txt), plus native geometry read back in mm | Python 3.11 or 3.12 is a tested choice for these examples. Run the pier replay or route tests to exercise the GEOS operations on a real geometry. Check continuous clearance, the controlling object and household target. |
| Editable plans, sections and native evidence | FreeCAD, its matching add-on and MCP server. BIM and TechDraw for the corresponding drawings | Start the RPC add-on, call `get_rpc_status`, then `list_documents`. Save and reopen a scratch feature through live MCP and inspect its dimensions before working on house files. The [pier example](../examples/whole-house-changes/README.md) includes a repeatable builder and read-back. [Connector installation](https://github.com/neka-nat/freecad-mcp) |
| Structural solver benchmark | Python 3.11, the [pinned example requirements](../examples/structural-opening/requirements.txt), live FreeCAD FEM, CalculiX and the FreeCAD MCP executable | Run the [two-solver replay](../examples/structural-opening/README.md#replay) in a new scratch folder. It exercises PyNite, verifies both mesh runs and reads stress and displacement from the reopened file. The pins belong to this benchmark. |
| Furnished scene and camera | Blender, its matching MCP add-on/server, the approved shell and product references | Call `get_addon_status` and `get_scene_info` with settings. Inspect the file, units, named camera and available asset providers. On a new machine exercise a scratch transfer with a known dimension. [Connector setup](https://github.com/ahujasid/mcp-for-blender) |
| Final AI photo and palette | An image-editing tool accepting the actual furnished camera image, reviewed product variants and render permission. The colour adviser is optional | Confirm reference-image editing in the agent's current tool list. At release compare the actual output against the exact camera. Use the [palette and decorator guidance](../skills/renovation-pack/references/colour-decisions.md) for a colour choice or physical finish. |
| Sun, GIS and rooftop PV | The garden replay reads saved angles with standard Python. To recalculate, use pvlib, pandas and timezone data. For a 3D study use a verified north offset and a compatible solar setup in Blender. QGIS and dated DSM/DTM coverage are useful for surrounding obstructions | Run the garden replay first. Follow the [angle regeneration instructions](../examples/garden-sun/README.md) for new times. Check Blender Sun Position in the active application. For GIS, inspect the coordinate system, vertical datum and a known site feature. [Sun Position](https://extensions.blender.org/add-ons/sun-position/) · [QGIS profiles](https://docs.qgis.org/latest/en/docs/user_manual/map_views/elevation_profile.html) |
| Thermal simulation, IFC or construction scheduling | EnergyPlus with appropriate weather, fabric and occupancy for thermal work. IfcOpenShell in the interpreter reading the IFC. OpenProject with an accessible project for a hosted programme | Check the installed simulator and run a supplied weather/model pair before presenting temperatures. Open an IFC and inspect units and levels before claiming coordination. Confirm access to the intended programme before using OpenProject. The worked bathroom schedule runs locally. [EnergyPlus](https://energyplus.net/) · [IfcOpenShell](https://docs.ifcopenshell.org/ifcopenshell-python.html) · [OpenProject](https://www.openproject.org/docs/user-guide/gantt-chart/) |
| Drawing illustration and issue | Matplotlib for the optional pier illustration. A document or workbook writer, PDF viewer and archive tool for the commissioned pack. Graphviz for the workflow diagram. | Open the exported page and extracted issue as the recipient. The [plan illustration](../examples/whole-house-changes/draw_plan.py) redraws the occupied kitchen. Run `python docs/render_workflow.py` from the repository root to rebuild both standalone SVGs. It uses Graphviz for the [room map](workflow.dot) and lays out the [review decisions](workflow-decisions.md) and [specialist triggers](../skills/renovation-pack/references/specialist-design-tools.md#requests-that-trigger-a-specialist-study). |

Planning authorities, data portals, imagery and supplier pages provide evidence. Check jurisdiction, plot, source date and access for each live enquiry. The [UK consent workflow](../skills/renovation-pack/references/uk-consents.md) identifies the official starting points.

## Commands to exercise the local workflows

Run from the repository root. Install the route requirements into the interpreter running the tests.

```sh
python house.py list
python examples/whole-house-changes/replay.py quotes
python examples/whole-house-changes/replay.py bathrooms
python examples/garden-sun/replay.py
python -m pip install -r requirements/dev.txt
python examples/whole-house-changes/replay.py pier
python -m unittest discover -s tests -v
```

For site, solar or thermal work, run the relevant desktop check as well. These use temporary inputs. The Blender check uses a fresh background process and reads the saved add-on preferences.

```sh
python examples/tool-readiness/check_site_tools.py qgis
python examples/tool-readiness/check_site_tools.py energyplus
blender --background --python-exit-code 1 --python examples/tool-readiness/check_sun_position.py
```

The [site checks](../examples/tool-readiness/check_site_tools.py) accept `--executable` with the full path to `qgis_process` or `energyplus`. For the EnergyPlus check, keep the supplied `ExampleFiles` and `WeatherData` beside the executable. Open a fresh terminal after changing the user PATH. If Blender is outside PATH, invoke its full executable path for the [Sun Position check](../examples/tool-readiness/check_sun_position.py).
