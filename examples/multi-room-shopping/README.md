# One purchasing handover for three rooms

Maple Mews is a fictional flat with a kitchen, shower room and studio. The owner commissions a shopping schedule for each room and a combined purchasing issue. The [four input lines](items.csv) include a retained stool and two packs of floor pads shared between the kitchen and studio.

```sh
python -m pip install -r requirements-packs.txt
python examples/multi-room-shopping/replay.py "../Maple purchasing"
```

Open the printed index. Each of the three room headings links to an editable workbook and a CSV. The kitchen lists six handles at £3 each. The studio lists a £26 lamp. Both relevant schedules show the two shared packs with a blank room allocation. The shower room carries just its retained stool. The replay compares every combined schedule with its issued standalone file before saving the house revision.

For the visual design and mixed audience editions of a house pack, see [Alder Cottage](../trade-schedules/README.md). For a change affecting several rooms, see the [Orchard House model and programme](../whole-house-changes/README.md).
