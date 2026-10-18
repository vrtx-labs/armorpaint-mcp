"""Install the local bridge into this source build and enable it on startup."""
import json
import shutil
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
app = Path("D:/Projects/armorpaint/paint/build/out")
shutil.copy2(repo / "plugin/armorpaint_mcp_bridge.c", app / "data/plugins/armorpaint_mcp_bridge.c")
config_path = app / "data/config.json"
config = json.loads(config_path.read_text())
plugins = config.setdefault("plugins", [])
if "armorpaint_mcp_bridge.c" not in plugins:
    plugins.append("armorpaint_mcp_bridge.c")
config_path.write_text(json.dumps(config, separators=(",", ":")))
shutil.copy2(app.parent / "x64/Release/ArmorPaint.exe", app / "ArmorPaint.exe")
print("Installed bridge and rebuilt executable:", app)
