# Live mask generators

## What changed

Mask Builder, Metal Edge Wear, Dirt Mask and Dust Mask are now native ArmorPaint
material nodes. Their output is evaluated by ArmorPaint's GPU shader system and
used by native fill masks. They do **not** load a generated mask PNG.

The generator uses ArmorPaint's existing Noise Texture fBM implementation,
shader compiler, image textures, mesh coordinates, fill-mask evaluation, node
serialization and history. The new code packages the composition and grouped
controls into a convenient node; it is not another renderer or baking engine.

The companion bridge is 1.3.0 and the server exposes 82 tools.

## Substance investigation

The installed Painter 1.7.3 `mg_mask_builder` package describes one grayscale
output and 58 inputs: seven image inputs, 50 scalar/integer controls, and output
size. Its interface was inspected from the package's embedded description XML
and the actual Machinery stack in DigitalJens.spp.

Image inputs are world-space normal, AO, signed curvature, custom grunge 1,
custom grunge 2, scatter input and position. Controls are grouped into Global,
Grunge, AO, Curvature, Gradient, World Space Normal, Scratches and Scatter.

In the native implementation:

1. AO contributes recess/occlusion coverage with range, contrast and noise.
2. Signed curvature separates convex and concave coverage. Their ranges may be
   positive or negative, with independent contrast/inversion. Smoothness uses
   a nine-tap texture-space filter at the actual input map's pixel size.
3. Seeded procedural grunge or custom grunge is blended in UV space or with
   normal-weighted triplanar projection.
4. Height gradient and six orientation weights add directional effects.
5. Procedural scratches and scattered stamps can add or subtract coverage.
6. Global level, contrast and inversion produce the final mask.

All 50 controls retain the legacy identifiers. The seed is exposed as
`$randomseed`, using the native UI's 0–65535 range. Output size follows the
ArmorPaint texture resolution.

The compiled Substance graph is not source code, and its bytecode is not being
executed. Noise patterns, blending formulas and filtering are independent
equivalents, **not pixel-identical reproduction** of Substance's internals.
Metal Edge Wear, Dirt and Dust are useful native presets of the shared builder.
Machinery itself uses the Mask Builder node with its recovered settings.

## Using the dirt example

Open `C:\Projects\DigitalJens-extracted\Dirt_Mask_Live_Example.arm`.

The example has yellow paint, a brown dirt fill layer, and a live Dirt Mask.
Select `03 - LIVE dirt generator (edit Level)` and its material
`Example - LIVE Dirt Mask`, then open **Nodes**.

- The **Controls** dropdown switches parameter sections.
- Under **Global**, Level 0 hides dirt and Level 1 reveals it everywhere.
- AO and concave curvature restrict the intermediate mask to creases/recesses.
- **Use Triplanar** projects the procedural/custom grunge in object space.
- White mask pixels reveal the brown dirt; black pixels retain yellow paint.
- The baked AO/normal/curvature/position inputs remain UV-space mesh data.
  This is also how mesh-map-driven generators work in Painter.

For an unconnected world normal/position input, the node uses current mesh
geometry in Y-up coordinates. Missing AO defaults to unoccluded and missing
curvature to neutral. Noise can be previewed without baking, but meaningful
cavity dirt needs AO and/or signed curvature.

Existing **Bake Texture** nodes can supply cached bake results directly, as can
Image Texture nodes. The older Curvature Texture node is unsigned; it is not a
substitute for a signed curvature map when convex/concave separation matters.
Direct Image/Bake Texture inputs support the builder's texture resampling.
For arbitrary upstream graphs, apply filtering/projection upstream rather than
expecting the builder to resample the entire graph at shifted coordinates.

## Machinery assembly

`ap_smart_material_apply` now builds live mask nodes for a Machinery manifest.
Only the baked geometry inputs are materialized as images; mask output is GPU
evaluated. Existing image-backed PBR base materials are retained.

ArmorPaint has one group level, so the functional stack is:

```text
Dust + live Dust mask (disabled in the supplied project)
Paint group + live shared paint-wear mask
    Dirty Paint + live dirty-paint mask
    Clean Paint
Steel Rust and Wear
```

Changing the shared Paint mask affects both Clean and Dirty Paint through the
group. There is no copied paint mask baked into the dirty mask and no duplicated
parameter set to keep in sync.

The Python generator may still write offline preview masks, but the live
assembler does not import or depend on those preview mask images.

## MCP control

Use `ap_node_add` with one of `MASK_BUILDER`, `MASK_EDGE_WEAR`, `MASK_DIRT`,
`MASK_DUST`. Wire its Mask output to a mask material's Base Color input.

`ap_mask_generator_get` reads all values and legal ranges in the active material:

```json
{"id":9}
```

`ap_mask_generator_set` supports one control or an atomic batch:

```json
{"id":9,"parameter":"Level","value":0.6}
```

```json
{"id":9,"parameters":{"Level":0.6,"AO":1,"Grunge":0.25,"$randomseed":7}}
```

Invalid batches are rejected without partial changes. A successful batch is one
native undo step. Updates automatically refill the masks. UI edits use the
normal node-editor live-preview/history path. Nodes, values, links and packed
mesh-map images persist in `.arm` projects; Python is not needed to edit them.

## Verification and performance

`work/smoke_live_mask.py` checks nonconstant GPU output and automatic Level 0/1
updates. `work/verify_live_mask_controls.py` checks seeded repeatability, AO,
convex/concave separation, smoothing, scratches, scatter, custom-image triplanar
projection, atomic validation, all 50 values on save/reopen, and undo/redo.
These checks compare real ArmorPaint texture exports, not mocked functions.

The measured median edit-to-next-frame time was about 660 ms on the local RTX
2080 at the current resolution. The current implementation still recompiles the
material shader and refills the mask during edits; it does not yet have a
uniform-only fast update path. This is a known interactive-performance limit.
It is separate from further matching Substance's noise and bake ranges.

`work/dirt_mask_example.py` creates the minimal example.
`work/build_jens.py live_masks` assembles the full Machinery example.
