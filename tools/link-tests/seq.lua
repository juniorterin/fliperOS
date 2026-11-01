local steps = dofile(os.getenv("SEQ_FILE"))
local frame = 0
local function field(name)
  for tag, port in pairs(manager.machine.ioport.ports) do
    for n, f in pairs(port.fields) do if n == name then return f end end
  end
end
local release = {}
emu.register_frame_done(function()
  frame = frame + 1
  for i, r in pairs(release) do
    if frame >= r.at then r.f:set_value(0); release[i] = nil end
  end
  for _, s in ipairs(steps) do
    if s[1] == frame then
      if s[2] == "press" then local f = field(s[3]); if f then f:set_value(1); table.insert(release, {at = frame + 6, f = f}) else print("NOFIELD", s[3]) end
      elseif s[2] == "on" then local f = field(s[3]); if f then f:set_value(1) else print("NOFIELD", s[3]) end
      elseif s[2] == "off" then local f = field(s[3]); if f then f:set_value(0) end
      elseif s[2] == "shot" then manager.machine.video:snapshot()
      elseif s[2] == "exit" then manager.machine:exit() end
    end
  end
end)
