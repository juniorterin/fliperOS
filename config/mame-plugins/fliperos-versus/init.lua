-- FliperOS: o placar de uma partida versus como saidas do MAME.
--
-- O jogo so desenha o placar na tela. Este plugin le os valores da memoria
-- do jogo, nos enderecos de /etc/fliperos/versus-games.conf (as linhas
-- "mame"), e os publica como saidas: fliperos_score1, fliperos_score2,
-- fliperos_rounds1... Com "-output network" elas saem pela porta 8000 junto
-- das outras saidas do jogo, e o config/fliperos-versus (o LED do gabinete),
-- o Hook Of The Reaper ou uma placa as leem dali.
--
-- Quem liga o plugin e o comando groovymame, so para um jogo da tabela.
local exports = {
	name = 'fliperos-versus',
	version = '1',
	description = 'FliperOS versus score as outputs',
	license = 'GPL-3.0-or-later',
	author = { name = 'FliperOS' } }

local versus = exports

local TABLES = { '/etc/fliperos/versus-games.conf', (os.getenv('HOME') or '') .. '/config/versus-games.conf' }
-- A cada quantos quadros a memoria e lida (4 vezes por segundo a 60 Hz).
local EVERY = 15
-- Os primeiros quadros sem publicar nada: o MAME so manda uma saida quando
-- ela muda, e quem le a porta 8000 ainda esta conectando. O que saisse antes
-- se perderia ate o valor mudar de novo.
local WAIT = 180

-- Le as linhas "mame" e "clone" de um arquivo. Um jogo num arquivo lido
-- depois troca o mesmo jogo dos anteriores.
local function read_table(path, games, clones)
	local file = io.open(path, 'r')
	if not file then
		return
	end
	local seen = {}
	for line in file:lines() do
		line = line:gsub('#.*', '')
		local words = {}
		for word in line:gmatch('%S+') do
			words[#words + 1] = word
		end
		if words[1] == 'clone' and words[3] then
			clones[words[2]] = words[3]
		elseif words[1] == 'mame' and words[6] then
			local game = words[2]
			if not seen[game] then
				games[game] = {}
				seen[game] = true
			end
			local format, mult = words[6]:match('^(%a+)%*(%d+)$')
			games[game][#games[game] + 1] = {
				field = words[3], address = tonumber(words[4]), bytes = tonumber(words[5]),
				format = format or words[6], mult = tonumber(mult) or 1, cpu = words[7] or ':maincpu' }
		end
	end
	file:close()
end

-- Os bytes (o mais significativo primeiro) como numero.
local function decode(bytes, format)
	local value = 0
	if format == 'bcd' or format == 'bcdle' then
		for _, b in ipairs(bytes) do
			local high, low = b >> 4, b & 15
			if high > 9 or low > 9 then
				return nil
			end
			value = value * 100 + high * 10 + low
		end
	else
		for _, b in ipairs(bytes) do
			value = (value << 8) | b
		end
	end
	return value
end

function versus.startplugin()
	local fields = nil
	local last = {}
	local frame = 0

	local function start()
		local games, clones = {}, {}
		for _, path in ipairs(TABLES) do
			read_table(path, games, clones)
		end
		local game = emu.romname()
		local hops = 0
		while not games[game] and clones[game] and hops < 8 do
			game = clones[game]
			hops = hops + 1
		end
		-- Um clone fora da tabela usa as linhas do pai que o proprio MAME conhece.
		if not games[game] then
			local parent = manager.machine.system.parent
			if parent and parent ~= '0' then
				game = parent
			end
		end
		fields = games[game]
		last = {}
		frame = 0
		if fields then
			for _, f in ipairs(fields) do
				local device = manager.machine.devices[f.cpu]
				f.space = device and device.spaces['program']
				if not f.address or not f.bytes or not f.space then
					emu.print_error(string.format('fliperos-versus: %s: bad line for %s', emu.romname(), f.field))
					f.space = nil
				end
			end
		end
	end

	local function tick()
		if not fields then
			return
		end
		frame = frame + 1
		if frame < WAIT or frame % EVERY ~= 0 then
			return
		end
		for _, f in ipairs(fields) do
			if f.space then
				local bytes = {}
				for i = 0, f.bytes - 1 do
					bytes[#bytes + 1] = f.space:read_u8(f.address + i)
				end
				if f.format == 'bcdle' or f.format == 'binle' then
					local reversed = {}
					for i = #bytes, 1, -1 do
						reversed[#reversed + 1] = bytes[i]
					end
					bytes = reversed
				end
				local value = decode(bytes, f.format)
				if value then
					value = value * f.mult
					if last[f.field] ~= value then
						last[f.field] = value
						manager.machine.output:set_value('fliperos_' .. f.field, value)
					end
				end
			end
		end
	end

	-- As referencias ficam guardadas: sem elas o MAME solta os avisos.
	versus.on_start = emu.add_machine_reset_notifier(start)
	versus.on_frame = emu.add_machine_frame_notifier(tick)
end

return exports
