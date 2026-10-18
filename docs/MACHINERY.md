# Machinery: legacy Painter study and ArmorPaint reconstruction

## Live-mask update

The current assembler uses native live mask generators with grouped UI controls,
triplanar grunge and native undo/redo. See [LIVE_MASK_GENERATORS.md](LIVE_MASK_GENERATORS.md).
Bridge 1.3.0 exposes 82 tools. The older image-backed mask implementation described
in parts of this investigation is retained as historical/offline-preview context.
The steel base is still image-backed; mask controls no longer require Python
regeneration. Performance and exact Substance-pattern matching remain separate
areas for improvement.

## Status

The Windows build includes native GPU baking through MCP, a signed-curvature
baker, and an independent procedural Machinery reconstruction. This is a working
first implementation, **not pixel-identical Substance compatibility**. The
installed Substance engine is not used to evaluate the reconstructed material.

The MCP server exposes 80 tools with bridge 1.2.0. Install the optional numerical
dependencies with `python -m pip install -e ".[smart]"` from this checkout.

## Local source and recovered assets

The running legacy application is:

`F:\SteamLibrary\steamapps\common\Substance Painter\Substance Painter.exe`

Its Machinery preset is:

`resources\shelf\allegorithmic\smart-materials\Machinery.spsm`

SHA-256: `15f84a06456082cd337aa11d814fdff176d81cf790aa8dc0cca7a95a9b7501fc`.

The other installation under `C:\Program Files\Allegorithmic\Substance Painter`
is version 7.1.0 and has a substantially different Machinery preset. Its Mask
Editor and additional grunges are not dependencies of the 1.7.3 version.

`C:\Projects\DigitalJens.spp` is an HDF5 container. A read-shared snapshot was
taken while Painter remained open. The original was not edited. Its embedded
`paint/scene.assbin` was exported through the locally installed Assimp DLL to:

`C:\Projects\DigitalJens-extracted\DigitalJens.obj`

Positions, normals, UVs and faces are retained; no remeshing is performed.
The project contains seven 1024-square baked maps: tangent normal, world-space
normal, AO, signed curvature, position, thickness and ID. Their float values are
retained in `mesh_maps\mesh_maps.npz`, with portable PNG copies alongside it.
Painter image resources use QDataStream metadata and raw/LZ4 float pixels. Their
row order is preserved. The separate GPU texture cache is bottom-left-origin
and is flipped for PNG output. Correct resource orientation was checked against
native world normals: mean cosine agreement was approximately 0.998.

The user-exported reference textures are in `C:\Projects\DigitalJens`.
The decoded project texture cache includes all visible lower layers; it is kept
separately under `painter_reference_textures`. The isolated Machinery stack and
its numeric settings are recorded in `machinery_painter_stack.json` and
`machinery_summary.json`.

## Actual 1.7.3 dependency graph

```text
Machinery
  Steel Rust and Wear
  Paint [MG Mask Builder mask]
    Clean Paint
    Dirty Paint [MG Mask Builder mask, generator opacity 80%]
  Dust [MG Mask Builder mask, generator opacity 71%]
```

Dust is disabled in the supplied DigitalJens project. It is retained but hidden
in the reconstructed project.

Only two Substance packages are embedded in the legacy smart material:

| Package | Embedded version |
|---|---|
| Steel Rust and Wear | `7de6ce7b22b59833ff740b51b097133464b4604b` |
| MG Mask Builder | `09e809072f2948c69548fd8d0e38a6afeffae6cb` |

The generator takes world-space normals, AO, curvature, position, custom grunge
1/2 and scatter image inputs. Grunge, noise, scratches and scatter are generated
inside its compiled package rather than referencing separate shelf packages.
Thickness is available in the mesh-map set but is not consumed by this legacy
generator. Tangent normal is used by the surface shader rather than the mask.

The paint mask uses Level 0.46, Contrast 0.9, Invert on, Grunge 0.6, AO 0.9 and
Curvature 0.97. Dirty Paint uses Level 0.8, Contrast 0.3, Grunge 0.3, AO 1 and
Curvature 1, matching the selected generator in the reference screenshot.

## Future meshes: native ArmorPaint workflow

Blender and existing Substance bakes are **not required** for this workflow.
Import a UV-mapped mesh into ArmorPaint first, then call:

1. `ap_bake_mesh_maps`:

   ```json
   {"directory":"C:/Projects/MyMesh/bakes","samples":64}
   ```

   Writes world-space normal, position, signed curvature, AO, thickness and
   tangent normal as PNGs, plus `mesh_maps.npz`. Use a new output directory.
   It uses the current ArmorPaint texture resolution. AO and thickness require
   hardware raytracing; the local RTX 2080 supports both.

2. `ap_smart_material_generate`:

   ```json
   {
     "mesh_maps":"C:/Projects/MyMesh/bakes/mesh_maps.npz",
     "output":"C:/Projects/MyMesh/machinery",
     "size":2048,
     "settings":{"paint":{"Level":0.46},"dust_enabled":false}
   }
   ```

3. `ap_smart_material_apply`:

   ```json
   {"manifest":"C:/Projects/MyMesh/machinery/machinery.json","prefix":"Machinery"}
   ```

   Adds native fill layers, a Machinery group, and editable fill masks. It is
   additive to the open project. Save using `ap_pack_assets` followed by
   `ap_project_save_as`. Regenerating a recipe does not automatically update an
   already packed project; reapply the generated material to use changed maps.

Individual native jobs are also exposed as `ap_bake_map_start` and
`ap_bake_map_status`. State 0 is idle, 1 pending, 2 complete; negative states
indicate output failure. Await completion before starting another bake or
editing the document. Native bakes use a temporary paint layer and restore the
selected layer, paint object, visibility, viewport mode and bake settings.
They add native creation/deletion history steps.

The normal baker uses ArmorPaint's current high-poly selection; with a single
mesh this is a self-bake and yields a near-neutral tangent normal map. Normal
transfer uses the internal Z-up basis; world-space output maps are Y-up for the
portable generator. A full automated high/low mesh assignment and cage workflow
has not been implemented.

### Signed curvature

The stock curvature baker measures unsigned squared normal derivatives. The new
native signed mode estimates mean curvature using normal and position
differentials. Flat is 0.5, convex is above 0.5, concave below 0.5. The stock UI
baker remains available separately. This is not Painter's multi-radius curvature
algorithm and its numerical range will differ.

### Optional CPU fallback

`ap_mesh_bake_start` / `ap_mesh_bake_status` launch a separate Blender background
process. This fallback rasterizes OBJ UVs, estimates signed vertex curvature,
and raytraces AO/thickness on the CPU. It supports a single 0–1 UV tile and
produces neutral tangent normals, not high-poly transfer. It was tested at
128-square / 8 samples. Prefer the native GPU workflow on this machine.

## Implementation details and current limits

- `armorpaint_mcp/machinery.py`: deterministic position-space noise, normal-
  weighted triplanar projections, AO/curvature/gradient/orientation masks,
  optional custom grunges, scratches/scatter, rusty-steel PBR and paint layers.
  Controls retain legacy names. The underlying formulas and noise patterns are
  independent approximations, not a reconstruction of Substance bytecode.
- `material_stack.py`: image-node materials, channel-aware fill layers and
  masks. Native fill-layer channel flags follow the source material so disabled
  channels do not erase lower-layer normals or height. Opacity writes remain
  enabled to establish layer coverage.
- ArmorPaint supports one group level. Painter's Paint subgroup is flattened:
  Clean Paint receives the paint mask; Dirty Paint receives the product of its
  own mask and the paint mask.
- Parameters are evaluated by the Python generator and applied as image-backed
  materials. They are not live Painter-style generator sliders inside ArmorPaint.
- Procedural evaluation currently runs at up to 1024-square and is resampled
  to the requested output size. Native mesh-map PNG export is currently 8-bit;
  recovered Painter float maps retain their original precision in NPZ.
- Single texture set / single UV tile is the verified use case. UDIMs, mesh-name
  matching, cages, antialiasing parity and multi-radius curvature parity remain
  future work.
- Materials rendered under different environment lighting will not have
  identical screenshots even with identical texture maps. Compare exported PBR
  channels on UV-covered texels as well as viewport appearance.

## Reproducible scripts and verification

Saved deliverables are in `C:\Projects\DigitalJens-extracted`:
`DigitalJens_reference.arm`, `DigitalJens_procedural.arm` and
`DigitalJens_native.arm`. Each includes packed textures and was checked on
reopen. The bridge's object-visibility tool now also updates active-stage
membership/hidden state, so a visible imported object stays visible on reopen.

Sixteen Python tests pass. The 80-tool handshake, recipe inspection and complete
six-map native bake suite were verified through the actual MCP stdio transport.
Native normal self-bake has mean encoded blue approximately 0.999 on covered
texels. The native reconstruction currently has more wear than the reference;
bake-range and generator-formula parity remain unfinished.

On covered texels, the reference-texture import/export round trip has mean
absolute errors approximately 0.006 base color, 0.007 roughness and 0.003 metallic
(0–1 units). The independent procedural preview remains substantially different:
approximately 0.097 base color and 0.172 roughness MAE against the supplied
exports. These are texture-space comparisons, not screenshot scores.

The `work` scripts inspect and decode SPSM/SPP files, recover the Assimp mesh,
extract float maps, assemble projects, and compare exported textures. Inspection
artifacts and original embedded packages are local ignored files, not source
dependencies of the reconstruction.

```powershell
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe work/verify_stdio.py
.venv/Scripts/python.exe work/verify_native_bake.py C:/Projects/MyMesh/new-bake-check
```

The native sweep requires an open mesh project. It checks all six bakers and
asserts that the layer stack and paint-object visibility match their initial
state. A viewport capture is written after completion. Tangent-normal self-bake
and nonconstant AO, position, normal, thickness and signed-curvature outputs
were inspected numerically and visually on DigitalJens.
