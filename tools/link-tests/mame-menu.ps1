$sd = if ($env:LINK_TESTS_OUT) { $env:LINK_TESTS_OUT } else { Join-Path $env:TEMP 'link-tests' }; New-Item -ItemType Directory -Force $sd | Out-Null
$m = if ($env:MAME_HOME) { $env:MAME_HOME } else { 'C:\mame0289\mame' }; $r = if ($env:LINK_TESTS_ROMS) { $env:LINK_TESTS_ROMS } else { 'C:\roms' }
New-Item -ItemType Directory -Force "$sd\mex" | Out-Null
Add-Type @'
using System; using System.Runtime.InteropServices;
public class MZ {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  public static void Click(int x, int y) { SetCursorPos(x,y); System.Threading.Thread.Sleep(150); mouse_event(2,0,0,0,UIntPtr.Zero); System.Threading.Thread.Sleep(120); mouse_event(4,0,0,0,UIntPtr.Zero); }
}
'@
$seq = "return {`n {700, 'on', 'Service Mode'},`n {1000, 'shot'}, {1020, 'press', 'Service 1'}, {1100, 'shot'}, {1120, 'press', 'Service 1'}, {1200, 'shot'},`n {1300, 'exit'},`n}"
Set-Content "$sd\mex_seq.lua" $seq -Encoding ascii
$env:SEQ_FILE = "$sd\mex_seq.lua"
foreach ($g in 'vr','f1lap','orunners','radr','scross','gunbustr') {
  $dir = "mex_$g"; Remove-Item "$m\$dir" -Recurse -Force -ErrorAction SilentlyContinue
  $p = Start-Process "$m\mame.exe" -WorkingDirectory $m -PassThru -ArgumentList "$g -rompath `"$r`" -window -skip_gameinfo -sound none -nothrottle -cfg_directory $dir\cfg -nvram_directory $dir\nv -snapshot_directory `"$sd\mex\${g}`" -autoboot_script `"$sd\seq.lua`""
  foreach ($t in 1..4) {
    Start-Sleep 3
    if ($p.HasExited) { break }
    $p.Refresh()
    if ($p.MainWindowHandle -ne 0) { [MZ]::SetWindowPos($p.MainWindowHandle,[IntPtr](-1),20,50,980,760,0x40) | Out-Null; [MZ]::Click(500,400) }
  }
  if (-not $p.WaitForExit(150000)) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
}
"ALL DONE" | Set-Content "$sd\mex\done.txt"
