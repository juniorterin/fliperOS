# Saude do Docker Desktop neste Windows, antes de um job pesado (ISO,
# kernel, pacotes, suites de teste) ou de reiniciar o Docker:
#
#   powershell -NoProfile -File tools\docker-health.ps1
#
# O Docker cai quando o Windows fica sem memoria comprometida (commit): os
# programas recebem errno 1455 ("arquivo de paginacao muito pequeno") e o
# motor do WSL para. Em 2026-10-16 o commit estava em 127,8 de 127,9 GB com
# so ~21 GB de RAM em uso, ~84 GB sem dono visivel: o servico RunSwUSB da
# Realtek (C:\Windows\runSW.exe, de um adaptador Wi-Fi USB) vazando handles,
# 432 mil em 16 dias. Um vazamento assim aparece aqui como o processo com
# handles demais. Reiniciar o Docker ou rodar wsl --shutdown nao devolve
# essa memoria; parar o processo que vaza (ou reiniciar o Windows) devolve.
#
# Outra queda, com memoria sobrando: o proprio WSL trava (2026-11-13, tres vezes).
# Ou o servico inteiro (wsl -l -v nunca volta), ou so a VM do Docker (a distro
# docker-desktop aparece Running mas nao executa nada). Os travamentos antigos
# vieram segundos depois de o PC voltar da suspensao. Reabrir o Docker nao
# resolve; so reiniciar o servico do WSL (admin) ou o Windows.
#
# Saida 0: pode usar. 1: commit acima de 85% (nao comece job pesado; feche
# programas ou reinicie o Windows). 2: o Docker nao responde, o WSL sim
# (reiniciar o Docker uma vez pode resolver). 3: o WSL travou (reiniciar o
# Docker nao resolve; pergunte ao usuario).
$m = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$os = Get-CimInstance Win32_OperatingSystem
$pct = [math]::Round(100 * $m.CommittedBytes / $m.CommitLimit)
$uptime = (Get-Date) - $os.LastBootUpTime
"Commit:   {0:N1} de {1:N1} GB ({2}%)" -f ($m.CommittedBytes / 1GB), ($m.CommitLimit / 1GB), $pct
"RAM:      {0:N1} GB livres de {1:N1} GB" -f ($os.FreePhysicalMemory / 1MB), ($os.TotalVisibleMemorySize / 1MB)
"Windows:  ligado ha {0} dias e {1} h" -f $uptime.Days, $uptime.Hours
# Vazamento de handles: um processo normal tem ate alguns milhares.
$leak = Get-Process | Where-Object { $_.HandleCount -gt 100000 } | Sort-Object HandleCount -Descending
foreach ($p in $leak) { "VAZANDO:  {0} (PID {1}) com {2:N0} handles: pare esse processo/servico" -f $p.Name, $p.Id, $p.HandleCount }
$vm = Get-CimInstance Win32_PerfFormattedData_VidPerfProvider_HyperVVMVidPartition -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -ne '_Total' }
foreach ($v in $vm) { "VM:       {0:N1} GB ({1})" -f ($v.PhysicalPagesAllocated * 4KB / 1GB), $v.Name }

# O codigo de saida vem de dentro do job: o $LASTEXITCODE daqui e de outro
# comando. Sem container rodando a saida e vazia, e isso e "ok", nao "nao responde".
$job = Start-Job {
  $o = docker ps --format '{{.Names}}  {{.Status}}' 2>&1
  [pscustomobject]@{ Code = $LASTEXITCODE; Out = @($o | ForEach-Object { "$_" }) }
}
if (Wait-Job $job -Timeout 30) {
  $r = Receive-Job $job
  if ($r.Code -ne 0) { $docker = $null } else { $docker = @($r.Out) }
} else {
  Stop-Job $job
  $docker = $null
}
if ($null -eq $docker) {
  "Docker:   NAO RESPONDE"
} else {
  "Docker:   ok, {0} container(s) rodando" -f @($docker | Where-Object { $_ }).Count
  $docker | Where-Object { $_ } | ForEach-Object { "          $_" }
}

if ($pct -ge 85) {
  "AVISO: commit em $pct%. Nao comece job pesado nem reinicie o Docker; feche programas ou reinicie o Windows."
  exit 1
}
if ($null -eq $docker) {
  # Roda um wsl.exe com limite de tempo: travado, ele nunca volta. A saida vem
  # em UTF-16, com NULs no meio. $null = nao respondeu.
  function Invoke-WslTimed([string[]]$wslArgs, [int]$sec) {
    $j = Start-Job { param($a) $o = & wsl.exe @a 2>&1; [pscustomobject]@{ Code = $LASTEXITCODE; Out = (@($o | ForEach-Object { "$_" }) -join "`n") -replace "`0", '' } } -ArgumentList (,$wslArgs)
    if (Wait-Job $j -Timeout $sec) { $r = Receive-Job $j; Remove-Job $j -Force; return $r }
    Stop-Job $j; Remove-Job $j -Force; return $null
  }
  $resume = Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-Power-Troubleshooter'; Id = 1 } -MaxEvents 1 -ErrorAction SilentlyContinue
  if ($resume -and $resume.TimeCreated -gt $os.LastBootUpTime) {
    $ago = (Get-Date) - $resume.TimeCreated
    "Suspensao: o PC voltou da suspensao ha {0} h {1} min" -f [int][math]::Floor($ago.TotalHours), $ago.Minutes
  }
  $wslState = 'ok'
  $list = Invoke-WslTimed @('-l', '-v') 20
  if ($null -eq $list) {
    $wslState = 'servico'
    "WSL:      TRAVADO (wsl -l -v nao responde)"
  } elseif ($list.Out -match '(?m)docker-desktop\s+Running') {
    # So testa a VM se ela ja esta ligada: com ela parada, o teste a ligaria.
    if ($null -eq (Invoke-WslTimed @('-d', 'docker-desktop', '-e', 'true') 20)) {
      $wslState = 'vm'
      "WSL:      a VM do Docker (docker-desktop) TRAVOU: aparece Running mas nao executa nada"
    } else { "WSL:      ok, VM do Docker ligada e respondendo" }
  } else {
    "WSL:      ok, VM do Docker desligada (Docker Desktop fechado ou parando?)"
  }
  if ($wslState -ne 'ok') {
    "AVISO: o WSL travou. Reiniciar o Docker NAO resolve. Pergunte ao usuario: reiniciar o servico do WSL como admin (taskkill /F no wslservice.exe, Start-Service WslService, depois abrir o Docker Desktop; derruba as distros WSL de todas as sessoes) ou reiniciar o Windows."
    exit 3
  }
  "AVISO: o Docker nao responde com memoria sobrando. Uma sessao so reinicia o Docker, e uma vez (Quit pela bandeja e abrir de novo)."
  exit 2
}
exit 0
