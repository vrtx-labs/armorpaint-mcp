"""Use ArmorPaint's existing node-editor reset-view shortcut to reveal controls."""
import time
import win32api
import win32con
import win32gui

windows=[]
win32gui.EnumWindows(lambda h,_:windows.append(h) if win32gui.GetWindowText(h).endswith(' - ArmorPaint') and win32gui.IsWindowVisible(h) else None,None)
window=windows[0]
win32gui.SetForegroundWindow(window)
x,y,_,_=win32gui.GetWindowRect(window)
win32api.SetCursorPos((x+1050,y+460))
time.sleep(.1)
win32api.keybd_event(ord('0'),0,0,0)
time.sleep(.1)
win32api.keybd_event(ord('0'),0,win32con.KEYEVENTF_KEYUP,0)
time.sleep(.3)
