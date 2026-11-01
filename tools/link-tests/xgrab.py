import ctypes, sys
x = ctypes.CDLL("libX11.so.6")
x.XOpenDisplay.restype = ctypes.c_void_p
d = x.XOpenDisplay(b":0")
if not d: sys.exit("no display")
x.XDefaultRootWindow.restype = ctypes.c_ulong
x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
root = x.XDefaultRootWindow(d)
class Attr(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("w", ctypes.c_int), ("h", ctypes.c_int)] + [("pad", ctypes.c_byte * 200)]
a = Attr()
x.XGetWindowAttributes.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p]
x.XGetWindowAttributes(d, root, ctypes.byref(a))
w, h = a.w, a.h
x.XGetImage.restype = ctypes.c_void_p
x.XGetImage.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_int]
img = x.XGetImage(d, root, 0, 0, w, h, 0xFFFFFFFF, 2)
if not img: sys.exit("no image")
class XImage(ctypes.Structure):
    _fields_ = [("width", ctypes.c_int), ("height", ctypes.c_int), ("xoffset", ctypes.c_int), ("format", ctypes.c_int), ("data", ctypes.c_void_p), ("byte_order", ctypes.c_int), ("bitmap_unit", ctypes.c_int), ("bitmap_bit_order", ctypes.c_int), ("bitmap_pad", ctypes.c_int), ("depth", ctypes.c_int), ("bytes_per_line", ctypes.c_int), ("bits_per_pixel", ctypes.c_int)]
im = ctypes.cast(img, ctypes.POINTER(XImage)).contents
raw = ctypes.string_at(im.data, im.bytes_per_line * im.height)
out = bytearray()
for y in range(im.height):
    row = raw[y * im.bytes_per_line:(y * im.bytes_per_line) + im.width * 4]
    for px in range(im.width):
        b, g, r = row[px*4], row[px*4+1], row[px*4+2]
        out += bytes((r, g, b))
open("/tmp/dl/x.ppm", "wb").write(b"P6\n%d %d\n255\n" % (im.width, im.height) + bytes(out))
print(w, h, im.bits_per_pixel)
