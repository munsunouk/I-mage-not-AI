# Blind icon repair task

For each provided 32x32 PNG, repair the existing image to satisfy both constraints:
1. Exactly one visible RGB color (fully transparent pixels do not count).
2. At least 10% transparent margin on each canvas edge.

Keep each source canvas at 32x32, preserve all pixels outside the smallest needed repair area, and make at most one repair attempt per image. Do not regenerate the image from a text prompt. Save one repaired PNG per input using the same sample ID under your assigned output folder. Also save `decisions.json` with each sample ID, the diagnosed rule(s), and a short reason. Do not access the original dataset, ground-truth labels, the other condition's files, previous chats, or any earlier benchmark result. Only the assigned input bundle and the tools explicitly allowed for your condition may be used.
