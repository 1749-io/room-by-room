# Specialist design tools

In the renovation repository, open the [tool inventory and replay commands](../../../docs/tools.md) to check the installation for the question at hand. If using a personal skill linked to a checkout, resolve repository links from that checkout.

Start with the homeowner’s question, the options still open and what they are willing to change. When reviewing a layout, consider its character and views, how activities work together, comfort and privacy, building constraints, cost and phasing. Include the garden, daylight and roof when they affect the brief. Pick the question whose answer matters now.

Use the existing brief, sources, decisions and current model revision. Reuse established latitude and longitude, site levels, geometry and the recorded relationship between plan axes and true north. Location and time give the sun’s direction in the sky. To place it relative to a window or roof face, establish the plan rotation and roof aspect from a survey, aligned map or other evidence. Carry that orientation between CAD, Blender, GIS and calculations. State any assumption that could reverse the finding.

Run a quick check in the background when the evidence supports it. The specialist tools are optional. Follow the existing permissions for CAD, unrendered Blender exploration and renders. If a tool is unavailable, use an evidenced calculation or section when it answers the same question. Ask for a missing measurement or preference only when it could change the answer.

## Character and views

When moving an opening, seat or screen changes a view, use Blender through live MCP. Compare the same eye position, height, lens and lighting in each permitted option. Look from the entrance, seat or adjoining room that prompted the question, including the garden outlook or a neighbour’s view in where relevant. Say what becomes visible or screened. An authorised viewport comparison can settle this before any rendered image.

### Looking up an exterior by address

Use an aerial view when identifying a rear addition, roof plane, garden boundary feature or neighbouring obstruction could change the decision. Start with the house photographs and plan. If another angle would help, search the full address in Google Maps and select **Layers > Satellite**. With established coordinates, open `https://www.google.com/maps/@?api=1&map_action=map&center=LAT,LON&zoom=19&basemap=satellite` after substituting the latitude and longitude. Match the footprint, adjoining buildings and street to the project before relying on the pin. Google Earth can offer an oblique 3D view where coverage exists. Street View can help with an elevation visible from the road. [Google Maps links](https://developers.google.com/maps/documentation/urls/get-started) · [Google Earth imagery and dates](https://support.google.com/earth/answer/6327779?hl=en)

Record the view link, provider, direction and capture date or range when available in the existing source record if you rely on it. Record the access date if the capture date is unknown. Keep provider attribution and check reuse terms before reproducing an image. For a wall outlet, use a close elevation photograph to identify visible obstructions and a site measurement to establish clearance. An overhead image alone cannot establish a concealed service, an opening height or permission to penetrate a wall. [Imagery reuse and attribution](https://about.google/brand-resource-center/products-and-services/geo-guidelines/)

## Daily life and circulation

Walk one real household routine through the occupied FreeCAD plan. Include doors and appliances in use, access to storage and the adjoining room. Use Shapely and NetworkX for a repeatable route comparison and Blender for a permitted walkthrough where the experience of moving through the space matters. Consider who can see or hear whom, where cooking smells travel and what must stay within reach. A measured passage may still take laundry through a private room or diners past the hob.

## Sun and comfort

For an example with a decision that changes with hedge height, replay the [garden tea-table study](../../../examples/garden-sun/README.md). When a proposed alteration raises an approval question, follow the [local planning and building-control enquiry](uk-consents.md).

Use Blender Sun Position for a specific seat, worktop, window or garden spot. Set the verified north offset, site coordinates, season, local time and daylight-saving setting. Compare direct sun and shadows at the relevant eye or task position across the permitted options. pvlib can repeat the solar-angle calculation across hours or seasons. A sun patch can identify exposure to direct light. Judging discomfort may also need the viewing direction, reflections, glass and blinds. Describe what the study establishes. [Blender Sun Position](https://extensions.blender.org/add-ons/sun-position/) · [pvlib solar position](https://pvlib-python.readthedocs.io/en/stable/reference/solarposition.html)

If surrounding trees, buildings or terrain could change the answer, check Environment Agency 1 m LiDAR coverage for the site in England. In QGIS use the surface model for obstructions and the terrain model where ground height matters. Check tile date, alignment and height datum against the project. Consider EnergyPlus when overheating could change the glazing or layout and the geometry, fabric, glass, shading, weather, ventilation and occupancy assumptions support comparing indoor conditions. [Environment Agency surface model](https://www.data.gov.uk/dataset/cf3f1137-c12b-44a1-a835-e80fe4a60b92/lidar-composite-digital-surface-model-dsm-1m) · [Terrain model](https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-dtm-2022-1m) · [QGIS elevation profiles](https://docs.qgis.org/latest/en/docs/user_manual/map_views/elevation_profile.html) · [EnergyPlus](https://energyplus.net/)

## Rooftop solar

Use pvlib when panels are part of the question or a live roof decision could materially affect an array. For two acceptable rooflight positions, first lay the same modules on the verified roof planes with the same clearances and obstructions. If the layouts fit different numbers of modules, the count and capacity in kWp may settle the choice.

For “Would panels be worthwhile?”, estimate annual AC generation in kWh. Use the site coordinates, each roof plane’s pitch and true azimuth, usable dimensions, module layout, near and distant shading, representative local weather, installed capacity, inverter and loss assumptions. Reuse an existing yield in kWh per kWp when those assumptions still fit. For a new model, integrate AC power over the weather time steps. Add seasonal totals when useful. If a material input is provisional, show a labelled case or range and identify the one fact that would most improve it. [pvlib system modelling](https://pvlib-python.readthedocs.io/en/stable/user_guide/modeling_topics/modelchain.html) · [PVGIS typical-year weather](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_pvgis_tmy.html)

When bill savings are requested, use the household’s consumption and its timing to estimate how much generation they will use on site. State any assumed self-consumption share. Value those kWh at the avoided import tariff and exported kWh at the export tariff. Show bill reduction and export income separately. Use an installed price before quoting payback.

## Fabric and feasibility

Use this optional study within the existing CAD review when the homeowner asks, or when a wall, level or service could change a live choice. A sentence in the room review can settle it. Use an annotated plan for position or a section for height and fall.

Use FreeCAD BIM and TechDraw for existing and proposed overlays and a section through the point at issue, such as a floor step, opening head or proposed waste run. When the architect supplies an IFC model, use IfcOpenShell to inspect the relevant elements, units, levels and placement against the house model. Record the specific survey question where concealed construction could reverse the recommendation. [FreeCAD BIM](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/BIM_Workbench.md) · [TechDraw sections](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/TechDraw_ArchView.md) · [IfcOpenShell](https://docs.ifcopenshell.org/ifcopenshell-python.html)

### Structural openings

Within the CAD review, trigger this study when a proposal creates, widens or relocates an opening, or removes a wall. Start with the recorded choice and the homeowner's limits. Compare retained and wider options only while that choice is open. For a selected opening, identify what the engineer must establish to deliver it.

Use live FreeCAD MCP and TechDraw to overlay the existing opening, the selected proposal and the floor above on a shared datum. Show evidenced joist directions and supports with their sources. Mark unknown bearings, floor direction and storey alignment on the drawing. Add a section when an upper wall, roof, opening head or the support below changes the interpretation. Ask the engineer one design question, such as where a finished pier or downstand would land. Carry its footprint or headroom consequence into the occupied layout, its cost into the allowance to be reconciled, and its resolution into the sequence before dependent work or orders.

The usual output is that overlay, its design consequence and the engineer's question. If an analysis is requested, use PyNite for an appropriate frame model or FreeCAD FEM with the CalculiX solver for a suitable finite-element study. Use engineer-verified loads and combinations, material properties, member geometry and support and connection conditions. Record the inputs, model limits and the engineer's interpretation before relying on results for the design. [PyNite](https://github.com/JWock82/PyNite) · [FreeCAD FEM](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/FEM_Workbench.md) · [CalculiX](https://github.com/Dhondtguido/CalculiX)

To check solver installation or practise the handover, replay the [fictional opening benchmark](../../../examples/structural-opening/README.md). It includes assumed loads, native results and an independent hand check. Its findings apply to the example.

## Phasing and handover

Start with a short phase table showing what depends on what, cost implications that distinguish the options, and how the household retains access, cooking, washing or heating during the work. Use OpenProject when a programme is requested or interdependent trades, lead times and occupation make sequencing consequential. [OpenProject programmes](https://www.openproject.org/docs/user-guide/gantt-chart/)

Surface a finding when it answers the homeowner, changes a recommendation or explains a trade-off. Put the assumption, result and deciding unknown in the existing brief, decision log, room review or handover wherever the next person will use it. A sentence is enough for a settled question. Provide a matched view, section, phase table or calculation when that is what the comparison needs.
