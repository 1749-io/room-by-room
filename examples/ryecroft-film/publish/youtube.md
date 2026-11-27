# room-by-room film, version 7: YouTube details (written to be found in search)

Thumbnail: `thumbnail.jpg` (1280 × 720, 170 KB). Rebuild with [make_thumbnail.py](../film/scripts/make_thumbnail.py) from the run's saved outputs.

## Title

AI agent plans a house renovation in FreeCAD and Blender (open source)

## Description

An AI agent plans a home renovation from start to finish: it models the house in FreeCAD, checks a wall removal, fixes an overheating conservatory, furnishes the rooms in Blender and makes concept photos of the finished rooms. It uses room-by-room, an open-source renovation toolkit for coding agents such as Codex and Claude Code.

Get room-by-room on GitHub: https://github.com/1749-io/room-by-room

Hannah and James have found their dream home, and it needs a lot of work. Before they make an offer, they ask an AI coding agent to show them the house finished.

What the AI agent does in 2 min 42 s:
• 3D model of the house in FreeCAD, built from a floor plan
• Removing the wall between kitchen and dining room: the wall carries the floor above, so a trial steel beam is run in two solvers (2.30 mm deflection in PyNite, 2.51 mm in CalculiX) for a structural engineer to size
• Doorway width check with Shapely and NetworkX: carrying shopping through the kitchen door, 756 mm as it is, 895 mm widened
• Sun and shade study from public LiDAR with QGIS and pvlib
• Conservatory overheating simulated in EnergyPlus: 35 °C on a hot day as it stands
• Conservatory rebuilt in FreeCAD with new glazing and 150 mm of roof insulation, then simulated for a whole year: 29 °C peak, and between 16 and 28 °C for 90% of waking hours, up from 39%
• Rooms furnished in Blender, an eye-level walkthrough, and an IFC (BIM) export for the architect
• AI concept photos made from the 3D model's own cameras, each checked against the model
• A dining room handover pack: review, drawing and shopping schedule

Chapters
0:00 A dream home that needs work
0:12 AI agent models the house in FreeCAD
0:39 Can the wall come out? Beam check and kitchen doorway
0:58 Sun, trees and an overheating conservatory (EnergyPlus)
1:13 Conservatory roof insulation: temperatures before and after
1:27 Rattan armchairs and sliding doors
1:44 Blender walkthrough, IFC export and build programme
2:02 AI concept photos from the 3D model
2:18 The dining room handover pack

Ryecroft is an example house, not a real one. Every figure on screen came from a real run of the named tool on that example. The photos are AI concepts made from the model. The beam is a trial case for a structural engineer, and the programme and budget are the agent's allowances. Nothing here is a survey, a structural design or a compliance check: these are concepts to brief your architect, engineer and builder.

Tools used: FreeCAD, Gmsh, CalculiX, PyNite, Shapely, NetworkX, QGIS, pvlib, EnergyPlus, Blender, IfcOpenShell. Product names belong to their owners.
Site data: Environment Agency LiDAR, contains public sector information licensed under the Open Government Licence v3.0. Building outlines and the road © OpenStreetMap contributors, Open Database Licence. Weather: climate.onebuilding.org TMYx, London Biggin Hill.
Music and sound synthesised for this film.

#AIagents #HomeRenovation #FreeCAD #Blender #OpenSource

## Tags

AI home renovation, AI agent, AI renovation planning, house renovation, home renovation ideas, AI interior design, FreeCAD, Blender, 3D house model, floor plan to 3D, EnergyPlus, conservatory overheating, conservatory roof insulation, removing a wall, IFC, BIM, IfcOpenShell, QGIS, Codex, Claude Code, coding agent, open source, room-by-room

## Playlist

Name: AI home renovation with room-by-room (open source)

Description:
AI agents planning home renovations with room-by-room, an open-source toolkit for coding agents such as Codex and Claude Code. Watch an agent model a house in FreeCAD, test ideas such as removing a wall or insulating a conservatory, furnish rooms in Blender and show them finished. Demos, walkthroughs, example houses and updates.
https://github.com/1749-io/room-by-room
