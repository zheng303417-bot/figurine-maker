# Reference review and refinement

Use after generating a mesh when the user wants closer resemblance to a reference. Compare the same model under matched cameras before editing.

1. Record the reference's main silhouette, head-to-body ratio, limb spacing and distinctive features. Limit the first correction pass to the most visible gaps.
2. Render the existing model from front, side and three-quarter angles. Use the same framing, shading and scale for before/after pairs. Include an untextured view to inspect the actual printable surface.
3. Explain which features can be recovered from the reference and which are inferred. Reuse the original model and preserve it as the rollback version. Keep modifications in a reproducible script or saved Blender file.
4. Correct large proportions before facial and surface details. Important printable details must exist as geometry. Recheck wall thickness and connection risk according to the selected printer profile.
5. Render the modified model using the saved review cameras. Record each gap as improved, unresolved or changed by interpretation. Continue for up to three passes when useful.
6. Re-run geometry inspection, target size and export roundtrips after modifications. Slice the revised file with appropriate support settings. Report the visual review independently from geometry and slicing evidence.

For a likeness test, inspect the front view against the reference before calling it successful. Record a visual failure when recognizable features in the brief are absent, fused, or materially distorted in the printable geometry. A model that passes slicing with those defects is suitable for geometry testing and should be labeled as such in the handoff.

This procedure adapts the reference comparison and QA workflow from [arjun988/blender-skills](https://github.com/arjun988/blender-skills). See [third-party notice](../THIRD_PARTY_NOTICES.md).
