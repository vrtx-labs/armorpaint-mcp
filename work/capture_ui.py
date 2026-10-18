"""Capture the ArmorPaint window for inspecting native node controls."""
from pathlib import Path
from PIL import ImageGrab
import win32gui
import win32con
import time

windows=[]
win32gui.EnumWindows(lambda hwnd,_: windows.append(hwnd) if win32gui.GetWindowText(hwnd).endswith(' - ArmorPaint') and win32gui.IsWindowVisible(hwnd) else None,None)
if not windows:
    raise RuntimeError('ArmorPaint window not found')
path=Path(__file__).with_name('armorpaint_ui.png')
window=windows[0]
win32gui.ShowWindow(window,win32con.SW_RESTORE)
win32gui.SetForegroundWindow(window)
time.sleep(.4)
if win32gui.GetForegroundWindow()!=window:
    raise RuntimeError('Could not foreground ArmorPaint for a GPU-window capture')
ImageGrab.grab(bbox=win32gui.GetWindowRect(window),all_screens=True).save(path)
print(path)
