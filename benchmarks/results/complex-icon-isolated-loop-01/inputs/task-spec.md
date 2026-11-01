# Blind complex icon repair task

The input folder contains twenty 128x128 RGBA game inventory icons. Each has exactly one injected defect. For each sample, `requirements.json` gives two output limits: maximum number of visible exact RGB colors and minimum transparent margin ratio on every canvas edge. Repair each icon so it meets both limits. Preserve the design, fine details, dimensions, and all unaffected pixels; do not regenerate artwork. Make one repair attempt per sample.

Save one repaired PNG per input using the same sample ID in your assigned output folder. Also save `decisions.json` keyed by sample ID with the diagnosed issue(s) and a short evidence-based reason. The requirement values are the same for every condition. Do not access dataset files, labels, evaluator mappings, the other condition's outputs, earlier chats, or prior benchmark results. Work only from this input folder and tools explicitly allowed by your condition.
