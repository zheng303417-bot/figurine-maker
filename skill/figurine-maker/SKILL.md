---
name: figurine-maker
description: Design a static figurine and orchestrate the local Figurine Maker workflow for text, reference images, or existing meshes, with evidence-based 3D printing checks.
---

# Figurine Maker

Clarify the subject, input ownership, target height in mm and whether it includes the base, printer process, and desired files. Use reasonable defaults for noncritical details and state them. Use [continuity guidance](references/character-design.md) to produce a character specification for review or reference image generation.

Use the separate runtime only if available. Inspect its documentation and run `figurine probe`, then `figurine validate --job PATH`, `figurine design --job PATH`, `figurine run --job PATH`, and `figurine verify --job PATH`. These commands accept `--output DIR`; run also accepts `--blender PATH`, `--approve-upload`, and `--approve-paid`. Job-relative source paths must stay within the job directory; default output is `./projects/<job_id>`. Adapt [the example](templates/job.example.json). Existing OBJ, STL, and GLB are supported inputs; request only supported export formats. Do not claim a file exists until the runtime actually produces and verifies it.

For one image, prefer the installed local `hunyuan` provider when likeness or complex small features matter. See the runtime's Hunyuan3D guide for setup. Use local `triposr` for a quick shape draft. Mock generates synthetic test geometry independent of the reference image. Obtain explicit consent and the job upload flag for an external upload, and explicit approval with a sufficient budget for paid calls. Keep credentials private.

Read [quality guidance](references/print-quality.md) before interpreting reports. Preserve original geometry; disclose actual fixes, limitations, and output paths. Report PASS only for checks with evidence, FAIL for executed failed checks, and UNVERIFIED for unperformed checks. Ask for review if processing changes important character features. 3MF, splitting, slicing, physical printing, and multi-view generation are not implied by a successful run.

When a reference image drives the job, follow [visual review](references/visual-review.md) before presenting a model as a finished figurine. Identify the features that make the subject recognizable, then inspect the printable geometry from matched views. If likeness fails, label the artifact a prototype and try available reconstruction or refinement options. Repeat geometry and slicing checks after modifications.
