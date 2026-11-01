"""Reproducible manual polygon masks for the i-mage-not-ai skill trial.

Coordinates are image-specific visual traces produced by the agent. The CLI
validates their files and alignment; it does not validate semantic boundaries.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).parent
SOURCE = ROOT / "fox-forest.png"
OUT = ROOT / "masks"

# Coordinates follow the generated source at 1448 x 1086. They are deliberately
# broad visual-feature boundaries, not pixel-perfect ground-truth annotations.
POLYGONS = {
    "fox_head": [[365, 305], [374, 208], [374, 135], [390, 98], [417, 81], [449, 107], [474, 166], [525, 171], [570, 147], [605, 128], [638, 148], [653, 174], [712, 158], [753, 174], [771, 223], [753, 276], [716, 323], [700, 354], [723, 383], [711, 410], [681, 435], [641, 449], [589, 446], [550, 464], [498, 453], [467, 431], [424, 438], [379, 418], [344, 391], [331, 361], [348, 338]],
    "fox_body": [[431, 436], [482, 444], [512, 467], [559, 476], [625, 460], [692, 477], [746, 512], [812, 524], [859, 555], [900, 606], [897, 672], [921, 746], [942, 824], [932, 876], [906, 900], [869, 899], [842, 880], [824, 820], [800, 780], [741, 775], [715, 810], [698, 866], [676, 899], [632, 905], [599, 887], [584, 836], [558, 813], [543, 863], [521, 895], [475, 899], [441, 882], [423, 830], [411, 766], [386, 744], [380, 674], [386, 593], [385, 521], [403, 476]],
    "fox_tail": [[739, 533], [787, 505], [854, 491], [916, 466], [984, 440], [1050, 421], [1125, 418], [1198, 433], [1252, 463], [1294, 509], [1320, 565], [1334, 614], [1317, 670], [1283, 715], [1230, 743], [1170, 747], [1110, 729], [1060, 713], [1015, 687], [978, 655], [937, 625], [900, 596], [860, 574], [814, 561], [772, 558]],
    "fox_scarf": [[407, 448], [438, 423], [469, 425], [507, 445], [548, 455], [583, 447], [611, 423], [632, 432], [624, 459], [688, 427], [725, 432], [797, 455], [819, 483], [804, 513], [762, 533], [788, 560], [805, 606], [796, 629], [774, 617], [744, 583], [713, 557], [671, 543], [621, 550], [576, 577], [536, 582], [485, 561], [439, 545], [408, 515], [396, 479]],
    "pink_flower": [[63, 565], [72, 540], [92, 532], [107, 538], [119, 518], [139, 524], [145, 544], [165, 540], [176, 558], [168, 577], [189, 589], [184, 610], [164, 618], [158, 640], [137, 647], [121, 632], [103, 646], [84, 636], [81, 617], [60, 608], [57, 587], [72, 576]],
    "blue_mushroom": [[1231, 711], [1250, 684], [1282, 670], [1324, 661], [1362, 666], [1394, 683], [1416, 710], [1428, 745], [1418, 766], [1388, 776], [1377, 798], [1374, 866], [1389, 889], [1385, 908], [1350, 918], [1306, 915], [1282, 899], [1285, 879], [1301, 863], [1300, 801], [1276, 786], [1247, 774], [1228, 755]],
    "distant_sky_and_mountain": [[790, 0], [1447, 0], [1447, 344], [1370, 328], [1300, 306], [1228, 285], [1178, 318], [1132, 278], [1096, 332], [1056, 300], [1002, 342], [957, 304], [908, 326], [850, 286], [810, 302], [790, 256]],
}

COLORS = {
    "fox_head": (255, 75, 75),
    "fox_body": (255, 170, 40),
    "fox_tail": (255, 235, 40),
    "fox_scarf": (40, 220, 220),
    "pink_flower": (255, 60, 190),
    "blue_mushroom": (50, 130, 255),
    "distant_sky_and_mountain": (80, 230, 120),
}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    source = Image.open(SOURCE).convert("RGB")
    width, height = source.size
    masks: dict[str, Image.Image] = {}
    for feature_id, points in POLYGONS.items():
        mask = Image.new("L", source.size, 0)
        ImageDraw.Draw(mask).polygon([tuple(point) for point in points], fill=255)
        masks[feature_id] = mask

    # Represent visible pixels for occluded parts: the scarf sits in front of
    # the head/chest, the torso sits in front of part of the tail, and the tail
    # sits in front of part of the mushroom cap.
    masks["fox_head"] = ImageChops.subtract(masks["fox_head"], masks["fox_scarf"])
    masks["fox_body"] = ImageChops.subtract(masks["fox_body"], masks["fox_scarf"])
    masks["fox_tail"] = ImageChops.subtract(masks["fox_tail"], masks["fox_body"])
    masks["blue_mushroom"] = ImageChops.subtract(masks["blue_mushroom"], masks["fox_tail"])
    for feature_id, mask in masks.items():
        mask.save(OUT / f"{feature_id}.png")

    # Aggregate object mask is the union of the traced fox parts.
    fox = Image.new("L", source.size, 0)
    for part in ("fox_head", "fox_body", "fox_tail", "fox_scarf"):
        fox = ImageChops.lighter(fox, masks[part])
    fox.save(OUT / "fox_character.png")
    masks["fox_character"] = fox

    overlay = source.convert("RGBA")
    tint = Image.new("RGBA", source.size, (0, 0, 0, 0))
    for feature_id, mask in masks.items():
        if feature_id == "fox_character":
            continue
        layer = Image.new("RGBA", source.size, (*COLORS[feature_id], 0))
        layer.putalpha(mask.point(lambda value: int(value * 0.42)))
        tint = Image.alpha_composite(tint, layer)
    overlay = Image.alpha_composite(overlay, tint)
    overlay.convert("RGB").save(ROOT / "segmentation-overlay.jpg", quality=94)

    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    specs = [
        ("fox_character", "character", None, "Combined fox silhouette from head, body, tail, and scarf traces; parts overlap by design."),
        ("fox_head", "head", "fox_character", "Fox ears and head/face silhouette; eyes, nose, muzzle, and fur markings are included as head detail."),
        ("fox_body", "body", "fox_character", "Visible fox torso and legs; scarf pixels are excluded and some overlap with tail remains at the attachment boundary."),
        ("fox_tail", "tail", "fox_character", "Visible large bushy tail including its cream tip; pixels covered by the torso are excluded."),
        ("fox_scarf", "clothing", "fox_character", "Teal scarf and loose end; overlaps the neck/chest and character body by design."),
        ("pink_flower", "flower", None, "Pink blossom only; surrounding leaves and stem are excluded."),
        ("blue_mushroom", "mushroom", None, "Visible blue cap and pale stem treated as one mushroom; pixels occluded by the fox tail are excluded."),
        ("distant_sky_and_mountain", "background_region", None, "Coarse upper-right sky/mountain region; intentionally not a precise semantic sky or mountain mask."),
    ]
    features = []
    for feature_id, role, parent_id, note in specs:
        feature = {
            "id": feature_id,
            "role": role,
            "geometry": {"type": "mask", "path": f"masks/{feature_id}.png"},
            "provenance": {"origin": "agent_inferred", "segmentation_note": note, "confidence": 0.72 if feature_id != "distant_sky_and_mountain" else 0.42},
        }
        if parent_id:
            feature["parent_id"] = parent_id
        features.append(feature)
    manifest = {
        "schema_version": "0.5",
        "asset": {"path": "fox-forest.png", "format": "png", "sha256": digest},
        "intent": {"kind": "game_asset", "style": "storybook", "purpose": "Test general visual-feature segmentation", "origin": "agent_inference"},
        "features": features,
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
