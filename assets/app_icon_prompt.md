# App 图标生成提示词

生成方式：Codex 内置 `imagegen`。

```text
Use case: logo-brand
Asset type: 1024×1024 macOS application icon for a Chinese photo workflow utility named “旭影的摄影工具集”
Primary request: Create one polished, professional macOS app icon that visually combines photo file organization, RAW/JPG pairing, chronological renaming, and star/color-label synchronization.
Subject: A premium dark graphite camera aperture at the center, layered with two subtly offset photo-file cards; one small five-point star and three tiny colored metadata dots (red, yellow, blue) integrated as functional accents; a gentle circular sync-arrow motif around the aperture.
Style/medium: clean modern 3D icon, Apple-like macOS utility icon aesthetics, restrained depth, crisp geometry, highly legible at small sizes, no photorealistic camera, no people.
Composition/framing: centered rounded-square app-icon object, generous padding, balanced and symmetrical, strong silhouette.
Lighting/mood: refined soft studio lighting, calm and trustworthy professional photography workflow.
Color palette: deep graphite, cool blue and violet gradient, small red/yellow/blue metadata accents.
Scene/backdrop: perfectly flat solid #00ff00 chroma-key background for background removal, uniform to every edge.
Constraints: no words, no letters, no Chinese characters, no watermark; the subject must not use #00ff00; no cast shadow or reflection outside the rounded-square icon; crisp clean outer edge; keep all important details away from the outer 10% margin.
Avoid: clutter, excessive tiny details, stock-photo look, glossy plastic toy appearance, Adobe or Apple logos, Finder logo, file-format text.
```

生成后使用项目内的透明背景处理流程移除色键，并转换为 macOS `.icns`。
