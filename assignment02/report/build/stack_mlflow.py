"""Stack the two MLflow UI crops from screenshot_mlflow.mjs into figures/fig_mlflow_ui.png (Figure 3)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FIG = Path(__file__).resolve().parent.parent / "figures"
PANELS = [
    ("mlflow_run_tags.png", "(a) Champion run: lineage tags and registered model version"),
    ("mlflow_registry.png", "(b) Model registry: version aliases and tags"),
]
LABEL_H, GAP = 44, 18

font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30, index=1)
images = [(Image.open(FIG / name).convert("RGB"), label) for name, label in PANELS]
width = max(img.width for img, _ in images)
height = sum(LABEL_H + img.height for img, _ in images) + GAP * (len(images) - 1)
out = Image.new("RGB", (width, height), "white")
draw = ImageDraw.Draw(out)
y = 0
for img, label in images:
    draw.text((4, y + 6), label, fill="#263238", font=font)
    y += LABEL_H
    out.paste(img, (0, y))
    draw.rectangle([0, y, img.width - 1, y + img.height - 1], outline="#cfd8dc", width=2)
    y += img.height + GAP
out.save(FIG / "fig_mlflow_ui.png")
print("saved fig_mlflow_ui.png", out.size)
