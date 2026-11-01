#!/usr/bin/env python3
"""Inject keys into the X server with XTest. Args: KEYSYM:HOLD_SECONDS, wait:SECONDS,
down:KEYSYM, up:KEYSYM. Needs DISPLAY and XAUTHORITY."""
import ctypes, sys, time
x = ctypes.CDLL("libX11.so.6")
t = ctypes.CDLL("libXtst.so.6")
x.XOpenDisplay.restype = ctypes.c_void_p
d = x.XOpenDisplay(b":0")
if not d: sys.exit("no display")
x.XStringToKeysym.restype = ctypes.c_ulong
x.XKeysymToKeycode.restype = ctypes.c_ubyte
x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
t.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
def code(name):
    return x.XKeysymToKeycode(d, x.XStringToKeysym(name.encode()))
def key(name, down):
    t.XTestFakeKeyEvent(d, code(name), 1 if down else 0, 0); x.XFlush(d)
for a in sys.argv[1:]:
    k, _, v = a.partition(":")
    if k == "wait": time.sleep(float(v))
    elif k == "down": key(v, True)
    elif k == "up": key(v, False)
    else:
        key(k, True); time.sleep(float(v or 0.15)); key(k, False); time.sleep(0.1)
