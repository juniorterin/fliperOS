$sd = if ($env:LINK_TESTS_OUT) { $env:LINK_TESTS_OUT } else { Join-Path $env:TEMP 'link-tests' }; New-Item -ItemType Directory -Force $sd | Out-Null
$d = if ($env:SUPERMODEL_HOME) { $env:SUPERMODEL_HOME } else { 'C:\supermodel-win\app\supermodel-0.3a-20261025-git-1481545' }
New-Item -ItemType Directory -Force "$sd\solo3" | Out-Null
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public class SW3 { [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f); [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r); public struct RECT { public int L,T,R,B; } }
'@
$games = 'scud','daytona2','dirtdvls','harley','lemans24','skichamp','spikeout','srally2','von2','lostwsga'
$log = "$sd\solo3\results.txt"; "" | Set-Content $log
foreach ($g in $games) {
  foreach ($v in 'nonet','net') {
    $logf = "$sd\solo3\${g}_$v.log"; Remove-Item $logf -ErrorAction SilentlyContinue
    $a = "ROMs\$g.zip -window -window-pos=20,50 -res=496,384 -no-sound -show-fps -log-output=`"$logf`" -log-level=info"
    if ($v -eq 'net') { $a += ' -net -port-in=1970 -port-out=1971 -address-out=127.0.0.1' }
    $p = Start-Process "$d\supermodel.exe" -WorkingDirectory $d -PassThru -ArgumentList $a
    $titles = @()
    foreach ($t in 20,40,60) {
      Start-Sleep 20
      if ($p.HasExited) { $titles += "EXITED@$t"; break }
      $p.Refresh(); [SW3]::SetWindowPos($p.MainWindowHandle,[IntPtr](-1),20,50,0,0,0x41) | Out-Null; [SW3]::SetForegroundWindow($p.MainWindowHandle) | Out-Null; Start-Sleep -Milliseconds 600
      $rc = New-Object SW3+RECT; [SW3]::GetWindowRect($p.MainWindowHandle,[ref]$rc) | Out-Null
      $w = $rc.R-$rc.L; $h = $rc.B-$rc.T
      $bmp = New-Object System.Drawing.Bitmap $w,$h; $gr=[System.Drawing.Graphics]::FromImage($bmp); $gr.CopyFromScreen($rc.L,$rc.T,0,0,$bmp.Size); $bmp.Save("$sd\solo3\${g}_${v}_$t.png"); $bmp.Dispose()
      $titles += "$t=[$($p.MainWindowTitle)]"
    }
    $net = (Get-Content $logf -ErrorAction SilentlyContinue | Select-String -Pattern 'net|socket|connect|listen' -SimpleMatch:$false | Select-Object -First 3 | ForEach-Object { $_.Line.Trim() }) -join ' / '
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    "$g $v $($titles -join ' ') :: $net" | Add-Content $log
  }
}
"ALL DONE" | Add-Content $log
