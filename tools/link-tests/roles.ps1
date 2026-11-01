# Role setup helpers for Supermodel (dot-source kb.ps1 and kb2.ps1 first). SUPERMODEL_COPIES holds the copies A, B, C, D of the release (each with Config, Assets, NVRAM) and a shared roms folder
$script:SMBase = if ($env:SUPERMODEL_COPIES) { $env:SUPERMODEL_COPIES } else { 'C:\supermodel-win' }
function Start-SM($dir, $game, $x, $y, $pin, $pout, $addr = '127.0.0.1') {
  $a = "$script:SMBase\roms\$game.zip -window -window-pos=$x,$y -res=496,384 -no-sound -show-fps -net -port-in=$pin -port-out=$pout -address-out=$addr"
  return (Start-Process "$script:SMBase\$dir\supermodel.exe" -WorkingDirectory "$script:SMBase\$dir" -PassThru -ArgumentList $a)
}
function Close-SM($p) { $p.CloseMainWindow() | Out-Null; if (-not $p.WaitForExit(15000)) { Stop-Process -Id $p.Id -Force } }
# Scud Race: rows are constant (9). LinkTests presses of Test on Link ID, CarTests on Car Number.
function Set-ScudRole($dir, $linkTests, $carTests, $shot) {
  $p = Start-SM $dir 'scud' 20 50 1990 1991
  Start-Sleep 25; $h = GameWin $p; FocusHandle $h 20 50
  Tap 0x36 2 350 3000; Tap 0x35 8 300 500; Tap 0x36 1 350 2500
  Tap 0x35 1 300 700; if ($linkTests) { Tap 0x36 $linkTests 350 900 }
  Tap 0x35 1 300 700; if ($carTests) { Tap 0x36 $carTests 350 900 }
  Tap 0x35 7 300 500; Tap 0x36 1 350 2500
  Tap 0x35 4 300 500; Tap 0x36 1 350 14000
  ShotHandle $h $shot
  Close-SM $p
}
# Daytona USA 2: Master -> Slave with one Test; the list shrinks to 5 rows (Link ID, Car Number, Cabinet Type, Motor Power, Exit)
function Set-Daytona2Role($dir, $carTests, $shot) {
  $p = Start-SM $dir 'daytona2' 20 50 1990 1991
  Start-Sleep 25; $h = GameWin $p; FocusHandle $h 20 50
  Tap 0x36 4 350 3500                       # diag screen, net-check screen, test menu (cursor on Exit)
  Tap 0x35 8 300 500; Tap 0x36 1 350 2500   # Game Assignments
  Tap 0x35 1 300 700; Tap 0x36 1 350 1000   # Link ID: Master -> Slave
  Tap 0x35 1 300 700; if ($carTests) { Tap 0x36 $carTests 350 900 }
  Tap 0x35 3 300 500; Tap 0x36 1 350 2500   # Exit of the 5-row list
  Tap 0x35 5 300 500; Tap 0x36 1 350 12000  # Exit of the main menu
  Tap 0x31 1 350 9000                       # Start past the system check
  ShotHandle $h $shot
  Close-SM $p
}


# Dirt Devils: Communication Mode (SLAVE default) and Machine ID. The page fits the window, so the value can be checked.
function Set-DirtRole($dir, $idTests, $shot) {
  $p = Start-SM $dir 'dirtdvls' 20 50 1990 1991
  Start-Sleep 25; $h = GameWin $p; FocusHandle $h 20 50
  Tap 0x36 1 350 3500                       # test menu (cursor on Exit)
  Tap 0x35 7 300 500; Tap 0x36 1 350 2500   # Game Assignments (cursor on Exit)
  Tap 0x35 8 300 500                        # Machine ID
  if ($idTests) { Tap 0x36 $idTests 350 900 }
  ShotHandle $h $shot
  Tap 0x35 2 300 500; Tap 0x36 1 350 2500   # Exit to the main menu
  Tap 0x35 4 300 500; Tap 0x36 1 350 9000   # Exit the test mode
  Close-SM $p
}
