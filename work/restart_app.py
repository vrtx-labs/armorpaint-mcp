"""Gracefully restart only the local source build used by this task."""
import subprocess
import time
from pathlib import Path
import win32gui
import win32process
import win32con
import win32api
import ctypes

app = Path("D:/Projects/armorpaint/paint/build/out")
scratch_pids = set()
def close(hwnd, _):
    if "ArmorPaint" not in win32gui.GetWindowText(hwnd):
        return
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    handle = win32api.OpenProcess(0x1000, False, pid)
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = ctypes.c_ulong(len(buf))
        if not ctypes.windll.kernel32.QueryFullProcessImageNameW(int(handle), 0, buf, ctypes.byref(size)):
            return
        image = buf.value
    finally:
        handle.Close()
    if Path(image) == app / "ArmorPaint.exe":
        if not win32gui.GetWindowText(hwnd).startswith("untitled"):
            raise RuntimeError("Save the named project and quit via MCP before restarting")
        scratch_pids.add(pid)
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
win32gui.EnumWindows(close, None)
time.sleep(1)
def discard_scratch(hwnd, _):
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    if pid in scratch_pids and win32gui.GetWindowText(hwnd) == "Save Changes?":
        win32gui.PostMessage(hwnd, win32con.WM_COMMAND, 7, 0)
win32gui.EnumWindows(discard_scratch, None)
time.sleep(3)
subprocess.run(["D:/Projects/armorpaint-mcp/.venv/Scripts/python.exe", "D:/Projects/armorpaint-mcp/work/install_bridge.py"], check=True)
stdout = open(Path(__file__).with_name("app-stdout.log"), "w")
stderr = open(Path(__file__).with_name("app-stderr.log"), "w")
p = subprocess.Popen([str(app / "ArmorPaint.exe")], cwd=app, stdout=stdout, stderr=stderr)
print("Started ArmorPaint", p.pid)
