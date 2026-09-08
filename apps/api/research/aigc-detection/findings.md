# Findings log

Running notes, most recent first. Not a report — raw observations as
samples/measurements come in, to turn into a real writeup once there's
enough to say something.

## 2026-09-08 — spike against the 3 samples already on hand

Before this skeleton existed, ran the *existing* vision-embedding signal
(MobileNetV3 + cosine distance vs the reference set) against the real
original/fake/pre-WhatsApp trio from #67:

| sample | cosine distance to closest reference |
| --- | --- |
| real (post-WhatsApp) | 0.2696 |
| fake, ChatGPT (post-WhatsApp) | 0.2792 |
| fake, ChatGPT (pre-WhatsApp) | 0.2932 |

Directionally consistent with the hypothesis (fake > real) but the gap is
tiny (well under the 0.30 "low" threshold) and the comparison is confounded:
the "real" sample is near-pixel-identical to the one real fixture already in
`samples/images/reference/` (same dimensions, same underlying receipt),
so its low distance isn't informative on its own. Not usable as-is — this
generic ImageNet-pretrained embedding doesn't have the resolution for this
task. Full context in issue #67.

No font/kerning measurement has been attempted yet — that's what
`measure.py` exists to start collecting data for, once real samples land in
`samples/`.
