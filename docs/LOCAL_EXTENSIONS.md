# Local ArmorPaint extensions

## Installed components

- ArmorPaint source: `D:/Projects/armorpaint`, baseline `fcf10dd`.
- Modified application: `D:/Projects/armorpaint/paint/build/out/ArmorPaint.exe`.
- MCP checkout and environment: `D:/Projects/armorpaint-mcp` and `.venv`.
- Bridge plugin installed and enabled in the application's `data/plugins`.
- Project-scoped OpenCode configuration: `D:/Projects/armorpaint/opencode.json`.

The bridge speaks the original version-1 file-mailbox protocol and advertises
bridge version 1.1.0. The server now exposes 72 tools. It requires this modified
Windows build, rather than the older baseline documented by upstream.

Restart OpenCode from `D:/Projects/armorpaint` to load the MCP configuration.
The active session was verified through the actual MCP stdio transport and uses
the same validated tool handlers through `work/ap.py` for task automation.

## Additional tools

- `ap_history_status`, `ap_undo`, `ap_redo`
- `ap_layer_list`, `ap_layer_select`, `ap_layer_create`, `ap_layer_delete`
- `ap_layer_duplicate`, `ap_layer_move`, `ap_layer_update`
- `ap_texture_resolution`, `ap_view_set`, `ap_export_pbr`, `ap_pack_assets`

Layer kinds: paint, fill, black mask, white mask, fill mask, group. Layer updates
support names, visibility, opacity, native blend modes, object restrictions and
group membership. Indexes are counted from the bottom. Names are unique and
may change after duplication; always use the name returned by the tool.

Undo/redo acts on native history, not saved project snapshots. History is local
to an editing session and is reset when a project is opened. Each changed layer
property is a separate undo step. Creation and naming can also be separate steps.

## Native changes

The current upstream already exposes layer creation, masks, groups, reordering
and viewport PNG output. This extension connects those APIs to MCP and adds:

- GPU-boundary-safe native history calls and layer duplication.
- History-aware layer opacity, visibility, blend mode and naming.
- Restoration of deleted layer names and fill-layer metadata.
- Full stack/hierarchy snapshots for layer-order undo/redo, replacing two-slot swaps.
- Correct boolean field registration for material channels and live-preview settings.
- Layer texture resizing and a PBR preset that includes emission.
- A full-aspect viewport capture path that avoids square cropping and stretching.

Changes are marked with `armorpaint-mcp` comments where appropriate. The tested
build uses the MSBuild overrides in ArmorPaint's `LOCAL-SETUP.md`.

The plugin also uses the current pointer-based UI API, current config field
names, Windows-native import paths, and bloom/grain settings.

## Checks performed

```powershell
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe work/verify_stdio.py
```

Ten argument-validation tests passed. A live scratch-project sweep also checked
layer creation, renaming, opacity, visibility, duplication, deletion, masks,
groups, nonadjacent reordering, undo/redo, and restoring fill-layer metadata.
The test returned to the saved sign project afterwards.

`work/verify_bridge.py` is destructive to the open project and is intended only
for a disposable scratch session. It starts a new project and does not save it.

## Artwork workflow

The original FBX was inspected with Blender to identify front lip, recessed
diffuser and body surfaces. Deterministic, UV-aligned PBR source images were
authored from the existing surface positions, then imported and assembled as
three editable ArmorPaint fill layers. Final base, normal, occlusion, roughness,
metallic and emission-mask channels were exported by ArmorPaint.

RGB emission, packed ORM, and a DirectX-normal variant were derived from those
exports. The RGB emission image is explicitly restricted to the inset-front
surface mask. Blender linked these maps to the original geometry to produce the
GLB and presentation renders. The delivered GLB has the original triangle count.

Task scripts and local diagnostics are in `work/`; final assets are beside the
input logo under `MOZU_Illuminated_Sign`.
