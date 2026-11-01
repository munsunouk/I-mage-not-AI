# Blind complex icon repair task

Repair all 20 supplied 128x128 RGBA game inventory icons. Each icon has exactly one injected defect. `requirements.json` gives both output limits for every sample: maximum number of visible exact RGB colors and minimum transparent margin ratio on each canvas edge. Meet both limits while preserving the icon’s artwork, fine detail, dimensions, and unaffected pixels. Do not regenerate artwork. One repair attempt per sample.

Save a repaired PNG per input with the same sample ID in your assigned output folder. Save `decisions.json` keyed by sample ID with the diagnosed issue(s) and a short evidence-based reason. Do not access dataset files, ground-truth mapping, the other condition’s outputs, previous chats, or previous benchmark results. Use only this input folder and tools explicitly allowed for your condition.
