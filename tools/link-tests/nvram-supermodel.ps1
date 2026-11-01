# Collects the Supermodel NVRAM of every cabinet number: Scud Race and Daytona USA 2 (1 to 8), Dirt Devils (1 to 4).
# Cabinets 1 to 4 are the files the four-copy ring tests left in the copies A to D (see docs/research/linked-cabinets.md);
# cabinets 5 to 8 are made here by raising the car number in the test menu. scud_car4.nv is the Scud Race file of car 4 saved
# from copy D before this script runs, in $sd\sm3. Needs kb.ps1, kb2.ps1 and roles.ps1 next to it.
$sd = if ($env:LINK_TESTS_OUT) { $env:LINK_TESTS_OUT } else { Join-Path $env:TEMP 'link-tests' }
. "$PSScriptRoot\kb.ps1"; . "$PSScriptRoot\kb2.ps1"; . "$PSScriptRoot\roles.ps1"
$out = "$sd\nvram\supermodel"; New-Item -ItemType Directory -Force "$out\scud","$out\daytona2","$out\dirtdvls" | Out-Null
$log = "$sd\nvram\log.txt"; "" | Set-Content $log
function Note($m) { "$(Get-Date -Format HH:mm:ss) $m" | Add-Content $log }
Stop-Process -Name supermodel -Force -ErrorAction SilentlyContinue; Start-Sleep 2
$B = $script:SMBase
function Save($src, $dst) { if (Test-Path $src) { Copy-Item $src $dst -Force; Note "saved $dst" } else { Note "MISSING $src" } }

# ---------- Scud Race ----------
Remove-Item "$B\A\NVRAM\scudau.nv" -ErrorAction SilentlyContinue
Set-ScudRole 'A' 0 0 "$sd\nvram\scud_1.png"; Save "$B\A\NVRAM\scudau.nv" "$out\scud\cabinet1.nv"
Save "$B\B\NVRAM\scudau.nv" "$out\scud\cabinet2.nv"
Save "$B\C\NVRAM\scudau.nv" "$out\scud\cabinet3.nv"
Save "$sd\sm3\scud_car4.nv" "$out\scud\cabinet4.nv"; Copy-Item "$sd\sm3\scud_car4.nv" "$B\D\NVRAM\scudau.nv" -Force
foreach ($k in 5..8) { Set-ScudRole 'D' 0 1 "$sd\nvram\scud_$k.png"; Save "$B\D\NVRAM\scudau.nv" "$out\scud\cabinet$k.nv" }

# ---------- Daytona USA 2 ----------
function Save-D2Defaults($dir, $shot) {
  $p = Start-SM $dir 'daytona2' 20 50 1990 1991
  Start-Sleep 25; $h = GameWin $p; FocusHandle $h 20 50
  Tap 0x36 4 350 3500                       # diag, net-check, test menu (cursor on Exit)
  Tap 0x36 1 350 12000                      # leave straight away: writes the defaults
  Tap 0x31 1 350 9000; ShotHandle $h $shot; Close-SM $p
}
function Set-D2Car($dir, $carTests, $shot) {   # already a slave: rows = Link ID, Car Number, Cabinet Type, Motor Power, Exit
  $p = Start-SM $dir 'daytona2' 20 50 1990 1991
  Start-Sleep 25; $h = GameWin $p; FocusHandle $h 20 50
  Tap 0x36 4 350 3500
  Tap 0x35 8 300 500; Tap 0x36 1 350 2500
  Tap 0x35 2 300 700; if ($carTests) { Tap 0x36 $carTests 350 900 }
  Tap 0x35 3 300 500; Tap 0x36 1 350 2500
  Tap 0x35 5 300 500; Tap 0x36 1 350 12000
  Tap 0x31 1 350 9000; ShotHandle $h $shot; Close-SM $p
}
Remove-Item "$B\A\NVRAM\daytona2.nv","$B\B\NVRAM\daytona2.nv" -ErrorAction SilentlyContinue
Save-D2Defaults 'A' "$sd\nvram\d2_1.png"; Save "$B\A\NVRAM\daytona2.nv" "$out\daytona2\cabinet1.nv"
Set-Daytona2Role 'B' 1 "$sd\nvram\d2_2.png"; Save "$B\B\NVRAM\daytona2.nv" "$out\daytona2\cabinet2.nv"
Save "$B\C\NVRAM\daytona2.nv" "$out\daytona2\cabinet3.nv"
Save "$B\D\NVRAM\daytona2.nv" "$out\daytona2\cabinet4.nv"
foreach ($k in 5..8) { Set-D2Car 'D' 1 "$sd\nvram\d2_$k.png"; Save "$B\D\NVRAM\daytona2.nv" "$out\daytona2\cabinet$k.nv" }

# ---------- Dirt Devils (master id 1 in B, slave ids 2..4 in A, C, D) ----------
Save "$B\B\NVRAM\dirtdvlsau.nv" "$out\dirtdvls\cabinet1.nv"
Save "$B\A\NVRAM\dirtdvlsau.nv" "$out\dirtdvls\cabinet2.nv"
Save "$B\C\NVRAM\dirtdvlsau.nv" "$out\dirtdvls\cabinet3.nv"
Save "$B\D\NVRAM\dirtdvlsau.nv" "$out\dirtdvls\cabinet4.nv"
Note "ALL DONE"
