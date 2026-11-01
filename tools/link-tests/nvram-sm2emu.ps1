# Makes the SM2-Emu NVRAM of Daytona USA for cabinets 1 to 8: cabinet 1 stays master, the others become slaves with their car
# number (Link ID and Car Number in the test menu's Game Assignments). Each file is then checked by starting the game with the
# link on and taking a capture of the network screen. Needs kb.ps1 next to it. The key counts depend on the game's menu.
$sd = if ($env:LINK_TESTS_OUT) { $env:LINK_TESTS_OUT } else { Join-Path $env:TEMP 'link-tests' }
. "$PSScriptRoot\kb.ps1"
$w = if ($env:SM2_HOME) { $env:SM2_HOME } else { 'C:\sm2-emu-win' }
$exe = "$w\app\sm2-emu-v0.9.56-windows-x86_64\sm2-emu.exe"
$rom = Join-Path $(if ($env:LINK_TESTS_ROMS) { $env:LINK_TESTS_ROMS } else { 'C:\roms' }) 'daytona.zip'
$out = "$sd\nvram\sm2emu\daytona"; New-Item -ItemType Directory -Force $out | Out-Null
$log = "$sd\nvram\sm2log.txt"; "" | Set-Content $log
function Note($m) { "$(Get-Date -Format HH:mm:ss) $m" | Add-Content $log }
Stop-Process -Name sm2-emu -Force -ErrorAction SilentlyContinue
function Start-Sm2($tag, $linkOn) {
  $cfg = "$w\nv_$tag\cfg"; New-Item -ItemType Directory -Force $cfg | Out-Null
  $en = if ($linkOn) { 'true' } else { 'false' }
  "[network]`r`nlink_enabled = $en`r`nlink_local_ip = 127.0.0.1`r`nlink_port = 15112`r`nlink_next_ip = 127.0.0.1`r`nlink_next_port = 15113`r`n" | Set-Content -Encoding ascii "$cfg\sm2-emu.ini"
  return (Start-Process $exe -WorkingDirectory "$w\app" -PassThru -ArgumentList "--config","$cfg","--nvram","$w\nv_$tag\save","--graphics-backend","software","--game","daytona",$rom)
}
function Quit-Sm2($p) { Focus $p; Tap 0x78 1 250 3000; if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
function Shot-Sm2($p, $path) { $p.Refresh(); ShotWin $p $path }
foreach ($car in 1..8) {
  $tag = "car$car"; Remove-Item "$w\nv_$tag" -Recurse -Force -ErrorAction SilentlyContinue
  $p = Start-Sm2 $tag $false
  Start-Sleep 28; Focus $p 20 50
  if ($car -gt 1) {
    Tap 0x30 1 300 3000                       # Test
    Tap 0xBC 9 150 350; Tap 0x31 1 250 2500   # Green up x9 to GAME SYSTEM, Start
    Tap 0xBC 8 150 350                        # up x8 to LINK ID
    Tap 0x4E 2 150 400                        # Blue x2: MASTER -> SINGLE -> SLAVE
    Tap 0x42 1 150 400                        # Red: CAR NUMBER
    Tap 0x4D ($car - 1) 150 400               # Yellow: car 1 -> N
    Tap 0x42 7 150 350; Tap 0x31 1 250 2500   # Red x7 to EXIT, Start
    Tap 0x42 9 150 350; Tap 0x31 1 250 6000   # leave the test menu
  } else { Start-Sleep 12 }
  Quit-Sm2 $p
  $nv = Get-ChildItem "$w\nv_$tag\save" -Filter 'daytona.*' -ErrorAction SilentlyContinue
  foreach ($f in $nv) { Copy-Item $f.FullName "$out\cabinet$car.$($f.Extension.TrimStart('.'))" -Force }
  Note "car $car saved: $(($nv | ForEach-Object Name) -join ',')"
  # check: relaunch with the link on and read the network screen
  $p = Start-Sm2 $tag $true; Start-Sleep 38; Focus $p 20 50; Shot-Sm2 $p "$sd\nvram\sm2_check_$car.png"; Quit-Sm2 $p
}
Note "ALL DONE"
