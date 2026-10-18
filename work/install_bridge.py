"""Install the local bridge into this source build and enable it on startup."""
import json
import shutil
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
app = repo.parent / "armorpaint/paint/build/out"
shutil.copy2(repo / "plugin/armorpaint_mcp_bridge.c", app / "data/plugins/armorpaint_mcp_bridge.c")
config_path = app / "data/config.json"
config = json.loads(config_path.read_text()) if config_path.exists() else {}
if "version" in config:
    plugins = config.setdefault("plugins", [])
    if "armorpaint_mcp_bridge.c" not in plugins:
        plugins.append("armorpaint_mcp_bridge.c")
    # config_load checks that the version field is literally the first key.
    config = {"version": config.pop("version"), **config}
    config_path.write_text(json.dumps(config, separators=(",", ":")))
else:
    print("First launch: enable armorpaint_mcp_bridge in Preferences > Plugins, or close the app and rerun this installer after its config has been created.")
shutil.copy2(app.parent / "x64/Release/ArmorPaint.exe", app / "ArmorPaint.exe")
print("Installed bridge and rebuilt executable:", app)
