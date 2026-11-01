$sd = if ($env:LINK_TESTS_OUT) { $env:LINK_TESTS_OUT } else { Join-Path $env:TEMP 'link-tests' }; New-Item -ItemType Directory -Force $sd | Out-Null
$w = if ($env:SM2_HOME) { $env:SM2_HOME } else { 'C:\sm2-emu-win' }; $exe = "$w\app\sm2-emu-v0.9.56-windows-x86_64\sm2-emu.exe"; $r = if ($env:LINK_TESTS_ROMS) { $env:LINK_TESTS_ROMS } else { 'C:\roms' }
New-Item -ItemType Directory -Force "$sd\menu3" | Out-Null
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public class MM { [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
 [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra); [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint type);
 public static void Tap(byte vk, int ms) { byte sc=(byte)MapVirtualKey(vk,0); keybd_event(vk,sc,0,UIntPtr.Zero); System.Threading.Thread.Sleep(ms); keybd_event(vk,sc,2,UIntPtr.Zero); } }
'@
function Shot($name) { $b=[System.Windows.Forms.SystemInformation]::VirtualScreen; $bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height; $gr=[System.Drawing.Graphics]::FromImage($bmp); $gr.CopyFromScreen($b.Left,$b.Top,0,0,$bmp.Size); $crop=$bmp.Clone((New-Object System.Drawing.Rectangle 28,90,990,740),$bmp.PixelFormat); $crop.Save("$sd\menu3\$name.png"); $bmp.Dispose(); $crop.Dispose() }
function T($vk,$n=1,$ms=250) { for($i=0;$i -lt $n;$i++){ [MM]::Tap($vk,$ms); Start-Sleep -Milliseconds 350 } }
# game, kind: A = service(9)xN then test(0); B = VR1(B)xN then start(1)
$plan = @(
 @('indy500','A',7), @('motoraid','A',7), @('stcc','A',7), @('waverunr','A',7), @('segawski','A',7), @('von','A',7), @('overrev','A',7),
 @('desert','B',7), @('sgt24h','A',8), @('srallyc','S',0))
foreach ($e in $plan) {
  $g=$e[0]; $k=$e[1]; $n=$e[2]
  $cfg = "$w\m3_$g"; Remove-Item $cfg -Recurse -Force -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force "$cfg\cfg","$cfg\nv" | Out-Null
  $p = Start-Process $exe -WorkingDirectory "$w\app" -PassThru -ArgumentList "--config","$cfg\cfg","--nvram","$cfg\nv","--graphics-backend","software","--game",$g,"$r\$g.zip" -RedirectStandardError "$cfg\err.log" -RedirectStandardOutput "$cfg\out.log"
  Start-Sleep 28
  $p.Refresh(); [MM]::SetWindowPos($p.MainWindowHandle,[IntPtr](-1),20,50,1010,830,0x40) | Out-Null; [MM]::SetForegroundWindow($p.MainWindowHandle) | Out-Null; Start-Sleep 1
  if ($k -eq 'S') { [MM]::Tap(0x30,700); Start-Sleep 4; Shot "${g}_a"; [MM]::Tap(0x39,700); Start-Sleep 3; Shot "${g}_b" }
  else {
    [MM]::Tap(0x30,250); Start-Sleep 3
    if ($k -eq 'A') { T 0x39 $n } else { T 0x42 $n }
    Shot "${g}_cursor"
    if ($k -eq 'A') { [MM]::Tap(0x30,250) } else { [MM]::Tap(0x31,250) }
    Start-Sleep 3; Shot "${g}_page"
  }
  if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
}
"ALL DONE" | Set-Content "$sd\menu3\done.txt"
