# Diagram files

| Diagram | Editable source | Image used in documentation |
|---------|-----------------|-----------------------------|
| Data model | [erd.svg](erd.svg) | [ERD PNG](../images/erd.png) |
| Use cases | [PlantUML model](use-case-diagram.puml) and [SVG layout](use-case-diagram.svg) | [Use-case PNG](use-case-diagram.png) |
| Buy sequence | [PlantUML](sequence-buy-order.puml) | [PNG](sequence-buy-order.png) |
| Sell sequence | [PlantUML](sequence-sell-order.puml) | [PNG](sequence-sell-order.png) |

The [diagram script](../../scripts/diagram.py) recreates the ERD and use-case
SVG/PNG files from its layout definitions. From the repository root:

```bash
python -m pip install Pillow
python scripts/diagram.py
```

Running it overwrites those diagram files. After manually editing an SVG or
replacing the ERD in #56, update the script to match before running it again,
or export directly from the replacement source instead.

Edit the ERD SVG in a vector editor and export the updated PNG to
`docs/images/erd.png`. Check that text, primary/foreign keys and relationship
multiplicities remain readable. Keep the model consistent with `src/virtutrade/database/schema.py`
and the data dictionary in `docs/design.md`.

For the use-case diagram, the PlantUML file describes the model and the SVG
contains its current layout. If the model changes, update the published image
and both sources together, or use PlantUML as the single source and export fresh
SVG/PNG files. Merely changing the `.puml` file does not update existing images.

Tuệ may replace the ERD with a new model and editable source under #56 if review
finds the current design unsuitable. Update links when changing file names or
source format. Include the findings and schema impact in the review PR.
