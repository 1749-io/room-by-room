# Colour choices, visual review and decorator issue

Use meodai’s `color-expert` as an optional adviser when someone needs to choose, compare or explain a colour, or diagnose an unexpected colour cast. Read the parts relevant to physical materials, lightness, saturation and illumination. The homeowner’s brief, retained items and selected shopping variants establish the starting point. The adviser can propose alternatives. The homeowner decides matters of taste, including which choices to delegate.

## Review every furnished room before final AI

Open the furnished Blender view beside the room brief or recorded colour choice. Look at the main surfaces, fixed furniture and accents together, including any adjoining room visible through a doorway. Can you pick out the pieces the homeowner wants to emphasise? Do adjacent undertones or strong accents pull attention somewhere unintended? Judge a bold or deliberately tonal scheme against the requested effect. Check other authorised views if they reveal a concern. Name the lighting actually reviewed and any relevant condition still untested.

Record a current `room-palette` row in the room's `finish-checks.csv`. Put the room or view in `subject`, the house-relative brief or decision path in `source` and the house-relative furnished view in `evidence`. In `finding`, say what works or point to a specific place where colours compete or merge. For a concern, give the smallest change worth trying and identify any fixed finish it preserves. A visually reviewed scheme that serves the brief can pass, including with an optional suggestion. A material or lighting error holds the affected review until corrected. If a consequential choice is still open, present the actual question to the homeowner and record a held `palette` row as described below. On resuming an older room, open its saved view before backfilling the review.

## When a choice is open

Identify the surfaces that are open and the finishes that are fixed. For a consequential choice, show two or three meaningful options with the same fixed items, camera, exposure and lighting. Show an adjoining room through the threshold if the choice affects both spaces. Describe the trade-off in ordinary terms, such as which paint lets the timber stand out in evening light. When renders are on hold, use permitted swatches or describe the options. Record a `palette` row in the room’s `finish-checks.csv`. A `hold` keeps the choice open while authorised studies and unrelated work continue.

Once the homeowner selects a scheme, record the decision in the house log and pass the row with that house-relative evidence path. A delegated choice should cite the original authority and record what the agent selected. A request for advice alone gives the agent no authority to change a specified finish. An agreed look needs only the standard furnished-room review unless that review reveals a new decision. A homeowner can approve the look of a concept and leave the exact paint to a site sample.

## When a colour changes in an image

Use the neutral product view and supplier variant to check the Blender material. Use the reviewed room camera to judge the agreed daylight or practical lighting. Check the actual AI output beside that camera. If a selected caramel chair looks right in Blender and turns orange in the AI image, retry from the reviewed camera. If the source material is already wrong in Blender, correct it there and repeat the affected tests. Camera pixels are useful for comparing like-for-like views. Lighting, exposure and display differences limit their value for identifying physical paint.

Record an `ai-colour` row per issued camera. Identify the camera in `subject`, link the reviewed Blender image in `source` and the actual generated image in `evidence`, both relative to the house. Record which fixed colours, accents and light were compared. A failed output holds release and allows a retry from the reviewed camera whenever the homeowner’s visual permissions allow it. On resuming an older room, inspect its existing image pair before recording this check.

## When handing finishes to a decorator

Enter the surfaces covered by the instruction in the room’s `decorator-finishes.csv`. Use `sample required` for a provisional shade. Compare the physical sample beside the retained finishes in daylight and under the room’s lamps where applicable. Use `approved` after recorded approval or an explicit instruction specifying the finish. Record manufacturer, named colour, code where supplied, finish or sheen, the affected surface and a house-relative record of the decision. Keep one current entry per surface and bring forward applicable lines when issuing a new revision.

Run `python house.py check-decorator "House" "Room" --input-revision R3` before issuing these rows as decorator instructions. Add `--surface "Walls"` for a scoped issue and include only that surface. A concept pack can include outstanding samples labelled for decision. The decorator check validates the recorded specification and approval for the listed scope. Review the surface list against the commission before issue.

## Adviser source

The reviewed upstream revision is `5bf7c7704d56bccc6aeea38c36bcf449abe56a6c`. On a new computer the agent can read the pinned skill on demand or use its skill installer with repository `meodai/skill.color-expert`, that revision, root path `.` and local name `color-expert`. The house checks also work with the local guidance above when offline. [Meodai’s skill](https://github.com/meodai/skill.color-expert/blob/5bf7c7704d56bccc6aeea38c36bcf449abe56a6c/SKILL.md) · [When the adviser applies](https://github.com/meodai/skill.color-expert/blob/5bf7c7704d56bccc6aeea38c36bcf449abe56a6c/evals/TRIGGERING.md)
