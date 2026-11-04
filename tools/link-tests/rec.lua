-- Aperta botoes e grava a tela de um jogo em PNG, quadro a quadro, sem janela.
-- REC_FILE: um arquivo Lua que devolve {press = {{quadro, "Campo"}, ...},
-- shots = {de, ate, a_cada}, exit = quadro}. Os PNG vao para o
-- -snapshot_directory (use -snapname "%g/%i"). Usado pelo ssf2tb-tournament.sh.
local plan = dofile(os.getenv("REC_FILE"))
local frame = 0
local release = {}
local function field(name)
  for _, port in pairs(manager.machine.ioport.ports) do
    for n, f in pairs(port.fields) do if n == name then return f end end
  end
end
emu.register_frame_done(function()
  frame = frame + 1
  for i, r in pairs(release) do
    if frame >= r.at then r.f:set_value(0); release[i] = nil end
  end
  for _, p in ipairs(plan.press or {}) do
    if p[1] == frame then
      local f = field(p[2])
      if f then f:set_value(1); table.insert(release, {at = frame + 8, f = f}) else print("NOFIELD", p[2]) end
    end
  end
  local s = plan.shots
  if s and frame >= s[1] and frame <= s[2] and (frame - s[1]) % s[3] == 0 then manager.machine.video:snapshot() end
  if plan.exit and frame >= plan.exit then manager.machine:exit() end
end)
