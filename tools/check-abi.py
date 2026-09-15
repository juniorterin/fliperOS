import ctypes
import importlib.util
import subprocess
from pathlib import Path
spec = importlib.util.spec_from_file_location('video', '/workspace/fliperos-video-check.py')
video = importlib.util.module_from_spec(spec)
spec.loader.exec_module(video)
expected = [ctypes.sizeof(t) for t in (video.Mode, video.Resources, video.Connector, video.Encoder, video.Crtc)]
expected += [video.Connector.modes.offset, video.Crtc.mode.offset]
actual = list(map(int, subprocess.check_output(['/audit/root/tmp/drm-abi'], text=True).split()))
assert expected == actual, (expected, actual)
print('libdrm ABI checked:', actual)
