Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public class KB {
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint type);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  public struct RECT { public int L, T, R, B; }
  public static void Tap(byte vk, int ms, bool ext) { byte sc = (byte)MapVirtualKey(vk, 0); uint f = ext ? 1u : 0u; keybd_event(vk, sc, f, UIntPtr.Zero); System.Threading.Thread.Sleep(ms); keybd_event(vk, sc, f | 2u, UIntPtr.Zero); }
  public static void Down(byte vk, bool ext) { keybd_event(vk, (byte)MapVirtualKey(vk, 0), ext ? 1u : 0u, UIntPtr.Zero); }
  public static void Up(byte vk, bool ext) { keybd_event(vk, (byte)MapVirtualKey(vk, 0), (ext ? 1u : 0u) | 2u, UIntPtr.Zero); }
  public static void Click(int x, int y) { SetCursorPos(x, y); System.Threading.Thread.Sleep(150); mouse_event(2, 0, 0, 0, UIntPtr.Zero); System.Threading.Thread.Sleep(100); mouse_event(4, 0, 0, 0, UIntPtr.Zero); }
}
'@
function Focus($p, $x = 20, $y = 50) { $p.Refresh(); [KB]::SetWindowPos($p.MainWindowHandle, [IntPtr](-1), $x, $y, 0, 0, 0x41) | Out-Null; [KB]::SetForegroundWindow($p.MainWindowHandle) | Out-Null; Start-Sleep -Milliseconds 400 }
function Tap($vk, $n = 1, $ms = 300, $gap = 500, $ext = $false) { for ($i = 0; $i -lt $n; $i++) { [KB]::Tap([byte]$vk, $ms, $ext); Start-Sleep -Milliseconds $gap } }
function ShotWin($p, $path) { $p.Refresh(); $rc = New-Object KB+RECT; [KB]::GetWindowRect($p.MainWindowHandle, [ref]$rc) | Out-Null; $w = $rc.R - $rc.L; $h = $rc.B - $rc.T; $bmp = New-Object System.Drawing.Bitmap $w, $h; $g = [System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($rc.L, $rc.T, 0, 0, $bmp.Size); $bmp.Save($path); $bmp.Dispose() }
