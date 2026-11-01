$sd = if ($env:LINK_TESTS_OUT) { $env:LINK_TESTS_OUT } else { Join-Path $env:TEMP 'link-tests' }; New-Item -ItemType Directory -Force $sd | Out-Null
$w = if ($env:SM2_HOME) { $env:SM2_HOME } else { 'C:\sm2-emu-win' }; $exe = "$w\app\sm2-emu-v0.9.56-windows-x86_64\sm2-emu.exe"; $r = if ($env:LINK_TESTS_ROMS) { $env:LINK_TESTS_ROMS } else { 'C:\roms' }
New-Item -ItemType Directory -Force "$sd\solo2" | Out-Null
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public class SW { [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f); }
'@
$games = 'daytona','srallyc','indy500','manxtt','motoraid','desert','overrev','stcc','sgt24h','waverunr','segawski','von'
$log = "$sd\solo2\results.txt"; "" | Set-Content $log
foreach ($g in $games) {
  foreach ($v in 'off','on') {
    $cfg = "$w\s2_${g}_$v"; Remove-Item $cfg -Recurse -Force -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force "$cfg\cfg","$cfg\nv" | Out-Null
    $en = if ($v -eq 'on') { 'true' } else { 'false' }
    "[network]`r`nlink_enabled = $en`r`nlink_local_ip = 127.0.0.1`r`nlink_port = 15112`r`nlink_next_ip = 127.0.0.1`r`nlink_next_port = 15113`r`nlink_cabinet_index = 0`r`n" | Set-Content -Encoding ascii "$cfg\cfg\sm2-emu.ini"
    $p = Start-Process $exe -WorkingDirectory "$w\app" -PassThru -ArgumentList "--config","$cfg\cfg","--nvram","$cfg\nv","--graphics-backend","software","--log-level","info","--game",$g,"$r\$g.zip" -RedirectStandardError "$cfg\err.log" -RedirectStandardOutput "$cfg\out.log"
    $titles = @()
    foreach ($t in 20,40,60) {
      Start-Sleep -Seconds ($(if ($t -eq 20) { 20 } else { 20 }))
      if ($p.HasExited) { $titles += "EXITED@$t"; break }
      $p.Refresh()
      [SW]::SetWindowPos($p.MainWindowHandle,[IntPtr](-1),20,50,1010,830,0x40) | Out-Null; [SW]::SetForegroundWindow($p.MainWindowHandle) | Out-Null; Start-Sleep -Milliseconds 800
      $b=[System.Windows.Forms.SystemInformation]::VirtualScreen; $bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height; $gr=[System.Drawing.Graphics]::FromImage($bmp); $gr.CopyFromScreen($b.Left,$b.Top,0,0,$bmp.Size)
      $crop=$bmp.Clone((New-Object System.Drawing.Rectangle 28,90,990,740),$bmp.PixelFormat); $crop.Save("$sd\solo2\${g}_${v}_$t.png"); $bmp.Dispose(); $crop.Dispose()
      $p.Refresh(); $titles += "$t=[$($p.MainWindowTitle -replace '^.*\[Software\] . ','')]"
    }
    $err = (Get-Content "$cfg\err.log" -ErrorAction SilentlyContinue | Select-String 'ERROR|error|missing|cannot' | Select-Object -First 2 | ForEach-Object { $_.Line }) -join ' / '
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    "$g $v $($titles -join ' ') $err" | Add-Content $log
  }
}
"ALL DONE" | Add-Content $log
