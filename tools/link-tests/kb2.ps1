Add-Type @'
using System; using System.Collections.Generic; using System.Runtime.InteropServices; using System.Text;
public class WF {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  public static List<IntPtr> ForPid(uint pid, string prefix) {
    var r = new List<IntPtr>();
    EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p); if (p == pid && IsWindowVisible(h)) { var sb = new StringBuilder(256); GetWindowText(h, sb, 256); if (sb.ToString().StartsWith(prefix)) r.Add(h); } return true; }, IntPtr.Zero);
    return r;
  }
}
'@
function GameWin($proc, $prefix = 'Supermodel -') { $l = [WF]::ForPid([uint32]$proc.Id, $prefix); if ($l.Count) { return $l[0] } else { return [IntPtr]::Zero } }
function ShotHandle($h, $path) { $rc = New-Object KB+RECT; [KB]::GetWindowRect($h, [ref]$rc) | Out-Null; $w = $rc.R - $rc.L; $hh = $rc.B - $rc.T; $bmp = New-Object System.Drawing.Bitmap $w, $hh; $g = [System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($rc.L, $rc.T, 0, 0, $bmp.Size); $bmp.Save($path); $bmp.Dispose() }
function FocusHandle($h, $x, $y) { [KB]::SetWindowPos($h, [IntPtr](-1), $x, $y, 0, 0, 0x41) | Out-Null; [KB]::SetForegroundWindow($h) | Out-Null; Start-Sleep -Milliseconds 400 }
