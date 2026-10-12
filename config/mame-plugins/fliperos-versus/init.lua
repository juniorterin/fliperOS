-- FliperOS: o placar de uma partida versus, lido da memoria do jogo.
--
-- O jogo so desenha o placar na tela. Este plugin le a memoria do jogo e
-- escreve o que achou, uma linha "nome = valor" por mudanca, num arquivo que
-- o config/fliperos-versus (o LED do gabinete) acompanha:
-- fliperos_wins1, fliperos_wins2 (partidas ganhas desde que o jogo abriu),
-- fliperos_char1, fliperos_char2 (o personagem de cada lado),
-- fliperos_score1... O formato e o da saida de rede do MAME (mame_start,
-- mame_stop), mas nao passa por ela: no MAME de agora um script nao cria
-- saidas novas, so usa as que o jogo declara (visto no gabinete, com o
-- GroovyMAME 0.289; ate o 0.264 dava).
--
-- De onde vem os enderecos:
--
--   - os detectores do Fightcade (github.com/fightcadeorg/fightcade-detectors,
--     um <jogo>.inf por jogo, baixados pelo fliperos-versus fetch): onde a
--     partida comeca, onde cada lado ganha e o personagem de cada um. Sao
--     avaliados como no FBNeo do Fightcade (vid_overlay.cpp): uma condicao
--     vale depois de 30 quadros seguidos, e a vitoria so e procurada 300
--     quadros depois de a espera pelo comeco ter iniciado.
--   - /etc/fliperos/versus-games.conf (as linhas "mame"): valores lidos
--     direto, como os pontos de cada jogador.
--
-- Quem liga o plugin e o comando groovymame, so para um jogo que tem um dos
-- dois.
local exports = {
	name = 'fliperos-versus',
	version = '2',
	description = 'FliperOS versus score read from the game memory',
	license = 'GPL-3.0-or-later',
	author = { name = 'FliperOS' } }

local versus = exports

local HOME = os.getenv('HOME') or ''
local TABLES = { '/etc/fliperos/versus-games.conf', HOME .. '/config/versus-games.conf' }
local DETECTORS = os.getenv('VERSUS_DETECTORS') or (HOME .. '/.local/share/fliperos/versus-detectors')
-- O arquivo que o fliperos-versus acompanha (recomeca a cada jogo).
local FEED = os.getenv('VERSUS_FEED') or ((os.getenv('XDG_RUNTIME_DIR') or '/tmp') .. '/fliperos-versus.feed')
-- A cada quantos quadros os valores sao escritos (4 vezes por segundo).
local EVERY = 15
-- Os tempos do Fightcade (vid_overlay.cpp).
local DETECTOR_FRAMES = 30
local START_FRAMES = 300

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

-- Um detector do Fightcade: "alvo=nome,area,operacao,0xENDERECO,valor,bits".
-- "raw" e o endereco da CPU. As outras areas sao a memoria como o FBNeo a
-- guarda no PC, em palavras de 16 bits invertidas: o byte N da area e o
-- byte N xor 1 do 68000. So as areas de endereco conhecido entram: a RAM do
-- CPS (0xFF0000) e a do Neo Geo (0x100000).
local function detector_reader(space, area, ptr, bits, neogeo)
	local function word(a)
		return (space:read_u8(a) << 8) | space:read_u8(a + 1)
	end
	if area == 'raw' then
		local bytes = (bits == 32 and 4) or (bits == 16 and 2) or 1
		return function()
			local value = 0
			for i = 0, bytes - 1 do
				value = (value << 8) | space:read_u8(ptr + i)
			end
			return value
		end
	end
	local base = nil
	if area == 'CpsRamFF' then
		base = 0xFF0000
	elseif area == '68K RAM' and neogeo then
		base = 0x100000
	end
	if not base then
		return nil
	end
	if bits == 32 then
		local a = base + (ptr & ~3)
		return function() return (word(a + 2) << 16) | word(a) end
	elseif bits == 16 then
		local a = base + (ptr & ~1)
		return function() return word(a) end
	end
	local a = base + (ptr ~ 1)
	return function() return space:read_u8(a) end
end

-- Le o <jogo>.inf: { start = {...}, player1 = {...}, player2 = {...},
-- char1 = detector, char2 = detector }, ou nil se falta o arquivo ou uma
-- area dele nao e conhecida.
local function read_detector(game, space, neogeo)
	local file = io.open(DETECTORS .. '/' .. game .. '.inf', 'r')
	if not file then
		return nil
	end
	local set = { start = {}, player1 = {}, player2 = {} }
	local ok = true
	for line in file:lines() do
		line = line:gsub('\r', '')
		local target, area, op, ptr, value, bits =
			line:match('^(%w+)=[^,]*,([^,]+),([^,]+),0[xX](%x+),(%-?%d+),(%d+)')
		if target then
			local reader = detector_reader(space, area, tonumber(ptr, 16), tonumber(bits), neogeo)
			local detector = { read = reader, op = op, value = tonumber(value), frames = 0, start = 0, current = 0 }
			if target == 'char1' or target == 'char2' then
				set[target] = reader and detector or nil
			elseif set[target] then
				if not reader then
					ok = false
				end
				set[target][#set[target] + 1] = detector
			end
		end
	end
	file:close()
	if not ok or #set.start == 0 or #set.player1 == 0 or #set.player2 == 0 then
		return nil
	end
	return set
end

-- Detector::Update do Fightcade: "eq" e o valor igual ao do arquivo; "gts" e
-- o valor maior que o guardado quando a partida comecou.
local function update_detector(d, start_detected)
	d.current = d.read()
	if start_detected then
		d.start = d.current
	end
	local found = false
	if d.op == 'eq' then
		found = d.current == d.value
	elseif d.op == 'gts' then
		found = (not start_detected) and d.current > d.start
	end
	d.frames = found and d.frames + 1 or 0
end

local function detected(list)
	for _, d in ipairs(list) do
		if d.frames >= DETECTOR_FRAMES then
			return true
		end
	end
	return false
end

function versus.startplugin()
	local fields = nil
	local detectors = nil
	local last = {}
	local frame = 0
	local wins = { 0, 0 }
	local waiting_start = true
	local frame_start = 0

	-- Uma linha no arquivo, ja gravada (o leitor a ve na hora).
	local feed = nil
	local function line(text)
		if feed then
			feed:write(text, '\n')
			feed:flush()
		end
	end

	local function publish(name, value)
		if last[name] ~= value then
			last[name] = value
			line(string.format('fliperos_%s = %d', name, value))
		end
	end

	local function stop()
		line('mame_stop = 1')
		if feed then
			feed:close()
			feed = nil
		end
	end

	local function start()
		local games, clones = {}, {}
		for _, path in ipairs(TABLES) do
			read_table(path, games, clones)
		end
		local rom = emu.romname()
		local parent = manager.machine.system.parent
		if parent == '0' or parent == '' then
			parent = nil
		end
		local game = rom
		local hops = 0
		while not games[game] and clones[game] and hops < 8 do
			game = clones[game]
			hops = hops + 1
		end
		-- Um clone fora da tabela usa as linhas do pai que o proprio MAME conhece.
		if not games[game] and parent then
			game = parent
		end
		fields = games[game]
		last = {}
		frame = 0
		wins = { 0, 0 }
		waiting_start = true
		frame_start = 0
		detectors = nil
		local counted = false
		if fields then
			for _, f in ipairs(fields) do
				local device = manager.machine.devices[f.cpu]
				f.space = device and device.spaces['program']
				if not f.address or not f.bytes or not f.space then
					emu.print_error(string.format('fliperos-versus: %s: bad line for %s', rom, f.field))
					f.space = nil
				end
				if f.field:match('^wins') or f.field:match('^rounds') then
					counted = true
				end
			end
		end
		-- As vitorias pelo detector do Fightcade, se a tabela nao as tem.
		if not counted then
			local cpu = manager.machine.devices[':maincpu']
			local space = cpu and cpu.spaces['program']
			if space then
				local neogeo = (manager.machine.system.source_file or ''):find('neogeo', 1, true) ~= nil
				detectors = read_detector(rom, space, neogeo)
				if not detectors and clones[rom] then
					detectors = read_detector(clones[rom], space, neogeo)
				end
				if not detectors and parent then
					detectors = read_detector(parent, space, neogeo)
				end
			end
		end
		-- O arquivo recomeca a cada jogo (e a cada reset da maquina).
		if feed then
			feed:close()
			feed = nil
		end
		if fields or detectors then
			feed = io.open(FEED, 'w')
			line('mame_start = ' .. rom)
		end
	end

	-- GameDetector::Update e UpdateDetectors do Fightcade, a cada quadro.
	local function detect()
		for _, d in ipairs(detectors.start) do
			update_detector(d, false)
		end
		local start_detected = detected(detectors.start)
		for _, d in ipairs(detectors.player1) do
			update_detector(d, start_detected)
		end
		for _, d in ipairs(detectors.player2) do
			update_detector(d, start_detected)
		end
		if detectors.char1 then
			update_detector(detectors.char1, start_detected)
		end
		if detectors.char2 then
			update_detector(detectors.char2, start_detected)
		end
		if waiting_start then
			if start_detected then
				waiting_start = false
			end
		elseif frame - frame_start > START_FRAMES then
			local won = false
			if detected(detectors.player1) then
				wins[1] = wins[1] + 1
				won = true
			end
			if detected(detectors.player2) then
				wins[2] = wins[2] + 1
				won = true
			end
			if won then
				waiting_start = true
				frame_start = frame
			end
		end
	end

	local function tick()
		if not fields and not detectors then
			return
		end
		frame = frame + 1
		if detectors then
			detect()
		end
		if frame % EVERY ~= 0 then
			return
		end
		if detectors then
			publish('wins1', wins[1])
			publish('wins2', wins[2])
			if detectors.char1 then
				publish('char1', detectors.char1.current)
			end
			if detectors.char2 then
				publish('char2', detectors.char2.current)
			end
		end
		for _, f in ipairs(fields or {}) do
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
					publish(f.field, value * f.mult)
				end
			end
		end
	end

	-- As referencias ficam guardadas: sem elas o MAME solta os avisos.
	versus.on_start = emu.add_machine_reset_notifier(start)
	versus.on_frame = emu.add_machine_frame_notifier(tick)
	versus.on_stop = emu.add_machine_stop_notifier(stop)
end

return exports
