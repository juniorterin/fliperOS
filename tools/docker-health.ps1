# Saude do Docker Desktop neste Windows, antes de um job pesado (ISO,
# kernel, pacotes, suites de teste) ou de reiniciar o Docker:
#
#   powershell -NoProfile -File tools\docker-health.ps1
#
# O Docker cai quando o Windows fica sem memoria comprometida (commit): os
# programas recebem errno 1455 ("arquivo de paginacao muito pequeno") e o
# motor do WSL para. Em 2026-10-16 o commit estava em 127,8 de 127,9 GB com
# so ~21 GB de RAM em uso: memoria reservada de VMs derrubadas a forca, que
# so volta reiniciando o Windows. Reiniciar o Docker ou rodar wsl --shutdown
# nessa hora so piora (outra VM, mais memoria presa).
#
# Saida 0: pode usar. 1: commit acima de 85% (nao comece job pesado; feche
# programas ou reinicie o Windows). 2: o Docker nao responde.
$m = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$os = Get-CimInstance Win32_OperatingSystem
$pct = [math]::Round(100 * $m.CommittedBytes / $m.CommitLimit)
$uptime = (Get-Date) - $os.LastBootUpTime
"Commit:   {0:N1} de {1:N1} GB ({2}%)" -f ($m.CommittedBytes / 1GB), ($m.CommitLimit / 1GB), $pct
"RAM:      {0:N1} GB livres de {1:N1} GB" -f ($os.FreePhysicalMemory / 1MB), ($os.TotalVisibleMemorySize / 1MB)
"Windows:  ligado ha {0} dias e {1} h" -f $uptime.Days, $uptime.Hours
$vm = Get-CimInstance Win32_PerfFormattedData_VidPerfProvider_HyperVVMVidPartition -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -ne '_Total' }
foreach ($v in $vm) { "VM:       {0:N1} GB ({1})" -f ($v.PhysicalPagesAllocated * 4KB / 1GB), $v.Name }

$job = Start-Job { docker ps --format '{{.Names}}  {{.Status}}' 2>&1 }
if (Wait-Job $job -Timeout 30) {
  $out = Receive-Job $job
  if ($LASTEXITCODE -ne 0 -and ($out -join ' ') -match 'error|cannot|failed') { $docker = $null } else { $docker = $out }
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
  "AVISO: o Docker nao responde com memoria sobrando. Uma sessao so reinicia o Docker, e uma vez (Quit pela bandeja e abrir de novo)."
  exit 2
}
exit 0
