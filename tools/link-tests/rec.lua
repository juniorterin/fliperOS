-- Aperta botoes e grava a tela de um jogo em PNG, quadro a quadro, sem janela.
-- REC_FILE: um arquivo Lua que devolve {press = {{quadro, "Campo"}, ...},
-- set = {{quadro, "Campo", valor}, ...}, shots = {de, ate, a_cada}, exit = quadro}.
-- press aperta e solta 8 quadros depois; set deixa o valor (um pedal, o
-- volante: o valor da faixa da porta, 0x20 a 0xe0 no Daytona). anchor =
-- {cpu = tag, bytes = {{endereco, valor}, ...}, frames = N} conta os quadros a
-- partir de quando todos esses bytes tem esses valores por N quadros seguidos
-- (o link pronto; N porque o teste de memoria do boot tambem os escreve); antes
-- disso, preshots = N grava uma tela a cada N quadros. Cada tela gravada
-- imprime "SHOT quadro" (negativo antes da ancora). Os PNG vao para o
-- -snapshot_directory (use -snapname "%g/%i"). Usado pelo ssf2tb-tournament.sh
-- e pelo daytona-link.sh.
local plan = dofile(os.getenv("REC_FILE"))
local frame = 0
local raw = 0
local anchored = plan.anchor == nil
local steady = 0
local release = {}
local function field(name)
  for _, port in pairs(manager.machine.ioport.ports) do
    for n, f in pairs(port.fields) do if n == name then return f end end
  end
end
local function shot(n)
  manager.machine.video:snapshot()
  print("SHOT " .. n)
end
emu.register_frame_done(function()
  raw = raw + 1
  if not anchored then
    local a = plan.anchor
    local space = manager.machine.devices[a.cpu].spaces["program"]
    local all = true
    for _, b in ipairs(a.bytes) do
      if space:read_u8(b[1]) ~= b[2] then all = false end
    end
    steady = all and steady + 1 or 0
    if steady >= (a.frames or 1) then
      anchored = true
      print("ANCHOR " .. raw)
    else
      if plan.preshots and raw % plan.preshots == 0 then shot(-raw) end
      return
    end
  end
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
  for _, p in ipairs(plan.set or {}) do
    if p[1] == frame then
      local f = field(p[2])
      if f then f:set_value(p[3]) else print("NOFIELD", p[2]) end
    end
  end
  local s = plan.shots
  if s and frame >= s[1] and frame <= s[2] and (frame - s[1]) % s[3] == 0 then shot(frame) end
  if plan.exit and frame >= plan.exit then manager.machine:exit() end
end)
