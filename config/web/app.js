// O painel web do FliperOS (config/fliperos-web): pede /api/status a cada
// segundo e desenha os cartoes. O historico do FPS (1 minuto) fica so aqui
// no navegador. Ingles ou portugues pelo idioma do navegador (o botao troca;
// a escolha fica no localStorage, quando ele existe).
"use strict";

const TEXT = {
  en: {
    login_text: "Sign in with the cabinet's user and password (the same as SSH and the network share).",
    user: "User", password: "Password", enter: "Sign in", logout: "Sign out",
    offline: "The cabinet is not answering. Retrying…", now_playing: "Now playing",
    nothing: "Nothing open", frontend: "Frontend", fps_note: "Last minute, from the OpenGL layer of the game.",
    video: "Video", memory: "Memory", storage: "Storage", network: "Network", volume: "Volume", mute: "Mute / unmute",
    processes: "Processes", logs: "Logs", refresh: "Refresh", wanted: "Asked in Video Setup", applied: "On screen now",
    monitor: "Monitor", frequency: "Frequency", resolution: "Resolution", connector: "Connector",
    orientation: "Orientation", mode: "Mode", hsync: "Horizontal", vsync: "Vertical", scan: "Scan",
    interlaced: "interlaced", progressive: "progressive", framebuffer: "Console framebuffer",
    no_output: "No active output found.", load: "load", used: "used", of: "of", swap: "Swap",
    down: "down", up: "up", signal: "signal", name: "Name", cpu: "CPU", mem: "Memory",
    busy: "busy", vram: "VRAM", clock: "clock", temp: "temperature", power: "power",
    filtering: "flicker filter on", core: "core", wrong: "Wrong user or password.",
    uptime: "up", not_installed: "No volume control.",
    games: "Games", search: "Search games", play: "Play", close_game: "Close the game",
    confirm_launch: "Close what is on the cabinet screen and open %s?", launching: "Opening %s on the cabinet…",
    confirm_close: "Close the game on the cabinet?", first: "Showing the first %n. Type to filter.",
    no_games: "No games in this folder.", count: "%n games",
    filter_all: "All games", favourites: "Favourites", favourite: "Favourite", favourited: "Favourite (remove)",
    g_file: "Set / file", g_year: "Year", g_maker: "Manufacturer", g_genre: "Genre", g_players: "Players",
    g_buttons: "Buttons", g_control: "Control", g_screen: "Screen", g_status: "Emulation", g_parent: "Clone of",
    g_series: "Series", g_played: "Played", g_played_n: "%n times, %t", g_title: "Full title", g_rating: "Rating",
    g_language: "Language", g_video: "Video (mp4)", g_loading: "Looking it up online…",
    g_offline: "Could not reach the game database (is the cabinet online?).", g_not_found: "Not in the Arcade Database.",
    pic_snap: "In game", pic_title: "Title", pic_marquee: "Marquee", pic_flyer: "Flyer", pic_cabinet: "Cabinet",
    pic_boxart: "Box",
    live: "Live screen", live_start: "Watch live", live_stop: "Stop", live_fps: "Frames per second",
    live_unmute: "Sound", live_mute: "Mute", live_full: "Full screen", live_install: "Install the live screen",
    live_installing: "Installing the live screen: the progress is in Files > Tasks.",
    live_install_note: "Downloads go2rtc and ffmpeg (about 70 MB, needs the internet).",
    live_turn_on: "Turn on", live_off_note: "The live screen is installed but off (Settings > Services > Live screen).",
    live_ready: "Ready: H.264 by %e.", live_hw: "the graphics card", live_no_audio: "no sound (Settings > Live screen sound)",
    live_connecting: "Connecting to the cabinet…", live_lost: "The connection dropped. Press Watch live again.",
    live_buffer: "%n ms in the buffer", shot_auto: "Every 10 s", live_obs_title: "Live screen in OBS", page_live: "Live",
    live_on_air: "Live", live_settings: "Streaming", live_service: "Service", live_encoder: "H.264",
    live_sound: "Sound", live_absent: "not installed", live_running: "running", live_stopped: "off",
    live_enc_hw: "graphics card (VA-API)", live_enc_sw: "software (x264)", live_audio_on: "on", live_audio_off: "off",
    live_turn_off: "Turn off", live_sound_on: "Turn the sound on", live_sound_off: "Turn the sound off",
    live_not_installed: "The live screen is not installed yet: Install, under Streaming (or Setup > System > Extras > Live screen).",
    live_settings_note: "ffmpeg only runs while someone watches (here or in OBS). The sound is a copy of the output on an ALSA loopback: games opened after turning it on get it.",
    sync_idle: "Watch live above to measure the stream delay: this then shows how many milliseconds to delay your camera and microphone in OBS so they line up with the game.",
    sync_on: "The game arrives here about <b>%v ms</b> late (its sound, <b>%a ms</b>). In OBS, delay the camera by <b>%v ms</b> (camera source: Filters > + > Render Delay) and the microphone by <b>%a ms</b> (Edit > Advanced Audio Properties > Sync Offset). Measured in this browser; OBS on the same PC gets about the same.",
    overlay_docs: "📖 How to set up the marquee (documentation)",
    overlay_games: "🎮 See the games with the versus scoreboard, by emulator (documentation)",
    live_net: "Network", live_net_wired: "cable", live_net_wifi: "Wi-Fi",
    live_net_tip_wifi: "The cabinet is on Wi-Fi. For a better stream, plug in a network cable: Wi-Fi loses packets and the picture can stall for a moment, mostly at 60 fps and in OBS.",
    live_net_tip: "Use a network cable instead of Wi-Fi for the best stream.",
    obs_open: "Open", obs_fps60: "60 (recommended)", obs_fps30: "30 (lighter)", obs_fps15: "15 (very light)",
    obs_fit: "Format", obs_fit_tube: "4:3 as on the tube (recommended)", obs_fit_fill: "Stretch to the whole source",
    obs_size: "Size in OBS", obs_size_1440: "1440 × 1080 (4:3, recommended)", obs_size_960: "960 × 720 (4:3, lighter)",
    obs_size_1920: "1920 × 1080 (16:9, black bars or stretched)", obs_sound: "With sound",
    obs_wh: "width %w, height %h", obs_step1: "In OBS: Sources > + > Browser, and paste the address above.",
    obs_step2: "Width and height:", obs_step3: "Tick Control audio via OBS for the sound. It reconnects by itself; the same key as the marquee (New address there changes both).",
    live_obs_off: "The address is ready, but the live screen is not running on the cabinet: turn it on under Streaming.",
    ovl_led: "LED dots", ovl_text: "Texts (name, high scores, achievements)",
    ovl_size_1280: "1280 × 320 (recommended)", ovl_size_1920: "1920 × 480", ovl_size_1024: "1024 × 256",
    ovl_obs: "In OBS: Sources > + > Browser, paste the address,",
    overlay: "Marquee for OBS", overlay_on: "Turn on the marquee page",
    overlay_note: "The marquee of the game on screen as a page for OBS: transparent background, the game's art (from ~/media), the high scores, the achievements and the versus score. No LED panel needed.",
    overlay_new: "New address", overlay_new_ask: "Make a new address? The old one stops working (update OBS).",
    copy: "Copy", copied: "Copied.",
    page_romfilter: "ROM filter",
    rf_intro: "The MAME ROM Cleaner filter, the same as in the Setup: what the Downloader takes from the torrents, or what goes from a romset folder to the emulator's folder.",
    rf_mode_dl: "Downloader filter", rf_mode_clean: "Clean a romset folder", rf_folder: "Romset folder",
    rf_no_folder: "No folder chosen", rf_choose: "Choose", rf_emulator: "Emulator (the MAME version of the romset)",
    rf_preset: "Preset", rf_games: "Games", rf_size: "Size", rf_data: "Data files:", rf_dest: "The games go to:",
    rf_dest_dl: "the Downloader's folder (Setup > Games > Downloader > Download folder)",
    rf_save: "Save the Downloader filter", rf_scan: "Preview", rf_custom: "Custom",
    rf_saved_now: "Downloader filter: %s", rf_not_saved: "The Downloader has no filter yet.",
    rf_all: "Mark all", rf_none: "Clear", rf_change: "Change", rf_done: "Done", rf_find: "Find",
    rf_g_games: "Which games", rf_g_play: "Players and controls", rf_g_screen: "Screen",
    rf_g_kind: "Categories and years", rf_g_hardware: "Hardware", rf_g_other: "Other",
    rf_s_all: "All", rf_s_buttons: "Buttons only", rf_s_any: "Any board", rf_s_n_of: "%n of %m",
    rf_n_marked: "%n of %m marked.", rf_none_means: "with none marked",
    rf_folder_help: "Open the folder with the romset (a disk, a USB drive, the network folder), then use it.",
    rf_no_subfolders: "No folders inside.", rf_use_this: "Use this folder",
    rf_pick_folder: "Choose the romset folder.", rf_counting: "Counting…", rf_from_torrent: "Counted on the ROM torrent's list.",
    rf_from_folder: "Counted on the folder.", rf_saving: "Saving…", rf_saved_toast: "Downloader filter saved.",
    rf_reading: "Reading the MAME XML and the folder… The first time with each MAME version takes about a minute.",
    rf_to: "The games go to:", rf_going: "Going", rf_sets_n: "%n sets", rf_in_folder: "In the folder",
    rf_needed: "Parents, BIOS, devices", rf_free: "Free space", rf_no_space: "not enough", rf_unknown: "Not in the XML (left alone)",
    rf_copy: "Copy them", rf_move: "Move them (out of the romset)", rf_nothing: "No game passed the filters.",
    rf_confirm_copy: "Copy the games that passed from %s?",
    rf_confirm_move: "Move the games that passed out of %s? They leave the romset.",
    page_downloads: "Downloads",
    page_frontend: "Frontend", page_files: "Files", page_settings: "Settings", page_status: "Status", page_terminal: "Terminal",
    settings: "Settings", settings_note: "Each change is saved and applied right away, through the Setup. Monitor, resolution and video driver stay in the Setup, on the cabinet screen.",
    saved: "Saved: %s", group_System: "System", group_Services: "Services", "group_480i games": "480i games", group_Colour: "Colour",
    downloads: "Downloads", dl_filter: "Filter (Setup > Games > Downloader):", dl_start: "Apply the filter and start",
    dl_note: "The filter is chosen on the ROM filter page (or in the Setup).", dl_roms: "ROM torrent", dl_chds: "CHD torrent", dl_none: "No link yet.",
    dl_add: "Add link", dl_default: "Use the link that comes with FliperOS", dl_paste: "magnet:?… (paste a link)", dl_remove: "Remove",
    dl_remove_ask: "Remove this torrent from the downloader?", dl_delete_ask: "Also delete what it already downloaded (not what reached the game folders)?",
    tasks: "Tasks", no_tasks: "Nothing running.", show_log: "Log", cancel: "Cancel", task_ok: "done", task_fail: "failed",
    trackball: "Trackball", ball_open: "Use the phone as a trackball", sensitivity: "Sensitivity", inertia: "Keeps rolling",
    ball_hint: "Roll with your finger (a quick flick keeps rolling; touch to stop it).", ball_on: "Connected: the cabinet sees a USB mouse.",
    btn_left: "Button 1", btn_middle: "3", btn_right: "Button 2",
    terminal: "Terminal", term_open: "Open the terminal", term_close: "Close", term_connecting: "Connecting…",
    term_on: "The cabinet's shell (zsh, user fliperos).", term_off: "Disconnected.",
    screen: "Screen", take_shot: "Take a screenshot", as_on_tube: "4:3, as on the tube", save_png: "Save PNG",
    shot_wait: "Taking the picture…", shot_from: "%w×%h, %s · %t", shot_x11: "desktop (X)", shot_gl: "OpenGL frame",
    download: "Download",
    files: "Files", up_folder: "Parent folder", upload: "Upload files", new_folder: "New folder", folder_name: "Name of the new folder:",
    confirm_delete: "Delete %s from the cabinet?", uploading: "Sending %s… %p%", uploaded: "Sent: %n file(s).",
    exists_overwrite: "%s already exists there. Replace it?", empty_folder: "Empty folder.", delete: "Delete",
    size: "Size", modified: "Modified", drop_hint: "You can also drop files on the list to send them to this folder.",
  },
  pt: {
    login_text: "Entre com o usuário e a senha do gabinete (os mesmos do SSH e da pasta de rede).",
    user: "Usuário", password: "Senha", enter: "Entrar", logout: "Sair",
    offline: "O gabinete não está respondendo. Tentando de novo…", now_playing: "Jogando agora",
    nothing: "Nada aberto", frontend: "Frontend", fps_note: "Último minuto, da camada OpenGL do jogo.",
    video: "Vídeo", memory: "Memória", storage: "Armazenamento", network: "Rede", volume: "Volume", mute: "Mudo / som",
    processes: "Processos", logs: "Logs", refresh: "Atualizar", wanted: "Pedido no Video Setup", applied: "Na tela agora",
    monitor: "Monitor", frequency: "Frequência", resolution: "Resolução", connector: "Conector",
    orientation: "Orientação", mode: "Modo", hsync: "Horizontal", vsync: "Vertical", scan: "Varredura",
    interlaced: "entrelaçado", progressive: "progressivo", framebuffer: "Framebuffer do console",
    no_output: "Nenhuma saída ativa.", load: "carga", used: "usado", of: "de", swap: "Swap",
    down: "desce", up: "sobe", signal: "sinal", name: "Nome", cpu: "CPU", mem: "Memória",
    busy: "uso", vram: "VRAM", clock: "clock", temp: "temperatura", power: "consumo",
    filtering: "filtro de flicker ligado", core: "core", wrong: "Usuário ou senha errados.",
    uptime: "ligado há", not_installed: "Sem controle de volume.",
    games: "Jogos", search: "Buscar jogos", play: "Jogar", close_game: "Fechar o jogo",
    confirm_launch: "Fechar o que está na tela do gabinete e abrir %s?", launching: "Abrindo %s no gabinete…",
    confirm_close: "Fechar o jogo no gabinete?", first: "Mostrando os primeiros %n. Digite para filtrar.",
    no_games: "Nenhum jogo nesta pasta.", count: "%n jogos",
    filter_all: "Todos os jogos", favourites: "Favoritos", favourite: "Favoritar", favourited: "Favorito (tirar)",
    g_file: "Set / arquivo", g_year: "Ano", g_maker: "Fabricante", g_genre: "Gênero", g_players: "Jogadores",
    g_buttons: "Botões", g_control: "Controle", g_screen: "Tela", g_status: "Emulação", g_parent: "Clone de",
    g_series: "Série", g_played: "Jogado", g_played_n: "%n vezes, %t", g_title: "Título completo", g_rating: "Nota",
    g_language: "Idioma", g_video: "Vídeo (mp4)", g_loading: "Buscando na internet…",
    g_offline: "Não deu para falar com a base de jogos (o gabinete está na internet?).", g_not_found: "Não está no Arcade Database.",
    pic_snap: "Jogando", pic_title: "Título", pic_marquee: "Letreiro", pic_flyer: "Flyer", pic_cabinet: "Gabinete",
    pic_boxart: "Capa",
    live: "Tela ao vivo", live_start: "Assistir ao vivo", live_stop: "Parar", live_fps: "Quadros por segundo",
    live_unmute: "Som", live_mute: "Mudo", live_full: "Tela cheia", live_install: "Instalar a tela ao vivo",
    live_installing: "Instalando a tela ao vivo: o andamento está em Arquivos > Tarefas.",
    live_install_note: "Baixa o go2rtc e o ffmpeg (uns 70 MB, precisa de internet).",
    live_turn_on: "Ligar", live_off_note: "A tela ao vivo está instalada, mas desligada (Configurações > Serviços > Live screen).",
    live_ready: "Pronta: H.264 %e.", live_hw: "pela placa de vídeo", live_no_audio: "sem som (Configurações > Live screen sound)",
    live_connecting: "Conectando ao gabinete…", live_lost: "A conexão caiu. Aperte Assistir ao vivo de novo.",
    live_buffer: "%n ms no buffer", shot_auto: "A cada 10 s", live_obs_title: "A tela ao vivo no OBS", page_live: "Ao vivo",
    live_on_air: "Ao vivo", live_settings: "Transmissão", live_service: "Serviço", live_encoder: "H.264",
    live_sound: "Som", live_absent: "não instalado", live_running: "no ar", live_stopped: "desligado",
    live_enc_hw: "placa de vídeo (VA-API)", live_enc_sw: "software (x264)", live_audio_on: "ligado", live_audio_off: "desligado",
    live_turn_off: "Desligar", live_sound_on: "Ligar o som", live_sound_off: "Desligar o som",
    live_not_installed: "A tela ao vivo ainda não está instalada: Instalar, em Transmissão (ou Setup > System > Extras > Live screen).",
    live_settings_note: "O ffmpeg só roda enquanto alguém assiste (aqui ou no OBS). O som é uma cópia da saída num loopback do ALSA: os jogos abertos depois de ligar já saem com ele.",
    sync_idle: "Assista ao vivo acima para medir o atraso da transmissão: aqui aparece quantos ms atrasar a câmera e o microfone no OBS para ficarem no tempo do jogo.",
    sync_on: "O jogo chega aqui com uns <b>%v ms</b> de atraso (o som dele, <b>%a ms</b>). No OBS, atrase a câmera em <b>%v ms</b> (na fonte da câmera: Filtros > + > Atraso de renderização) e o microfone em <b>%a ms</b> (Editar > Propriedades avançadas de áudio > Deslocamento de sincronização). Medido neste navegador; o OBS no mesmo PC fica quase igual.",
    overlay_docs: "📖 Como configurar o marquee (documentação)",
    overlay_games: "🎮 Ver os jogos com placar versus, por emulador (documentação)",
    live_net: "Rede", live_net_wired: "cabo", live_net_wifi: "Wi-Fi",
    live_net_tip_wifi: "O gabinete está no Wi-Fi. Para uma transmissão melhor, ligue um cabo de rede: o Wi-Fi perde pacotes e a imagem pode engasgar por um instante, mais ainda a 60 fps e no OBS.",
    live_net_tip: "Use a rede cabeada em vez do Wi-Fi para a melhor transmissão.",
    obs_open: "Abrir", obs_fps60: "60 (recomendado)", obs_fps30: "30 (mais leve)", obs_fps15: "15 (bem leve)",
    obs_fit: "Formato", obs_fit_tube: "4:3 como no tubo (recomendado)", obs_fit_fill: "Esticar para a fonte inteira",
    obs_size: "Tamanho no OBS", obs_size_1440: "1440 × 1080 (4:3, recomendado)", obs_size_960: "960 × 720 (4:3, mais leve)",
    obs_size_1920: "1920 × 1080 (16:9, com barras ou esticado)", obs_sound: "Com som",
    obs_wh: "largura %w, altura %h", obs_step1: "No OBS: Fontes > + > Navegador, e cole o endereço acima.",
    obs_step2: "Largura e altura:", obs_step3: "Marque Controlar áudio pelo OBS para o som. Ele reconecta sozinho; usa a mesma chave do marquee (Endereço novo lá troca as duas).",
    live_obs_off: "O endereço está pronto, mas a tela ao vivo não está no ar no gabinete: ligue em Transmissão.",
    ovl_led: "Pontos de LED", ovl_text: "Textos (nome, recordes, conquistas)",
    ovl_size_1280: "1280 × 320 (recomendado)", ovl_size_1920: "1920 × 480", ovl_size_1024: "1024 × 256",
    ovl_obs: "No OBS: Fontes > + > Navegador, cole o endereço,",
    overlay: "Marquee para o OBS", overlay_on: "Ligar a página do marquee",
    overlay_note: "O marquee do jogo na tela como página para o OBS: fundo transparente, a arte do jogo (de ~/media), os recordes, as conquistas e o placar versus. Não precisa de painel de LED.",
    overlay_new: "Endereço novo", overlay_new_ask: "Criar um endereço novo? O antigo para de funcionar (atualize o OBS).",
    copy: "Copiar", copied: "Copiado.",
    page_romfilter: "Filtro de ROMs",
    rf_intro: "O filtro do MAME ROM Cleaner, o mesmo do Setup: o que o Downloader baixa dos torrents, ou o que vai de uma pasta com um romset para a pasta do emulador.",
    rf_mode_dl: "Filtro do Downloader", rf_mode_clean: "Limpar uma pasta de romset", rf_folder: "Pasta do romset",
    rf_no_folder: "Nenhuma pasta escolhida", rf_choose: "Escolher", rf_emulator: "Emulador (a versão do MAME do romset)",
    rf_preset: "Preset", rf_games: "Jogos", rf_size: "Tamanho", rf_data: "Arquivos de dados:", rf_dest: "Os jogos vão para:",
    rf_dest_dl: "a pasta do Downloader (Setup > Games > Downloader > Download folder)",
    rf_save: "Gravar o filtro do Downloader", rf_scan: "Prévia", rf_custom: "Personalizado",
    rf_saved_now: "Filtro do Downloader: %s", rf_not_saved: "O Downloader ainda não tem filtro.",
    rf_all: "Marcar todas", rf_none: "Desmarcar", rf_change: "Trocar", rf_done: "Pronto", rf_find: "Procurar",
    rf_g_games: "Quais jogos", rf_g_play: "Jogadores e controles", rf_g_screen: "Tela",
    rf_g_kind: "Categorias e anos", rf_g_hardware: "Hardware", rf_g_other: "Outros",
    rf_s_all: "Todos", rf_s_buttons: "Só botões", rf_s_any: "Qualquer placa", rf_s_n_of: "%n de %m",
    rf_n_marked: "%n de %m marcadas.", rf_none_means: "com nenhuma marcada",
    rf_folder_help: "Abra a pasta com o romset (um disco, um pendrive, a pasta da rede) e use-a.",
    rf_no_subfolders: "Nenhuma pasta dentro.", rf_use_this: "Usar esta pasta",
    rf_pick_folder: "Escolha a pasta do romset.", rf_counting: "Contando…", rf_from_torrent: "Contado na lista do torrent de ROMs.",
    rf_from_folder: "Contado na pasta.", rf_saving: "Gravando…", rf_saved_toast: "Filtro do Downloader gravado.",
    rf_reading: "Lendo o XML do MAME e a pasta… A primeira vez com cada versão do MAME leva cerca de um minuto.",
    rf_to: "Os jogos vão para:", rf_going: "Vão", rf_sets_n: "%n sets", rf_in_folder: "Na pasta",
    rf_needed: "Pais, BIOS, dispositivos", rf_free: "Espaço livre", rf_no_space: "não cabe", rf_unknown: "Fora do XML (ficam)",
    rf_copy: "Copiar", rf_move: "Mover (sai do romset)", rf_nothing: "Nenhum jogo passou nos filtros.",
    rf_confirm_copy: "Copiar de %s os jogos que passaram?",
    rf_confirm_move: "Mover para fora de %s os jogos que passaram? Eles saem do romset.",
    page_downloads: "Downloads",
    page_frontend: "Frontend", page_files: "Arquivos", page_settings: "Configurações", page_status: "Status", page_terminal: "Terminal",
    settings: "Configurações", settings_note: "Cada mudança é gravada e aplicada na hora, pelo Setup. Monitor, resolução e driver de vídeo ficam no Setup, na tela do gabinete.",
    saved: "Gravado: %s", group_System: "Sistema", group_Services: "Serviços", "group_480i games": "Jogos 480i", group_Colour: "Cor",
    downloads: "Downloads", dl_filter: "Filtro (Setup > Games > Downloader):", dl_start: "Aplicar o filtro e começar",
    dl_note: "O filtro é escolhido na página Filtro de ROMs (ou no Setup).", dl_roms: "Torrent das ROMs", dl_chds: "Torrent dos CHDs", dl_none: "Sem link ainda.",
    dl_add: "Cadastrar link", dl_default: "Usar o link que vem no FliperOS", dl_paste: "magnet:?… (cole um link)", dl_remove: "Remover",
    dl_remove_ask: "Tirar este torrent do downloader?", dl_delete_ask: "Apagar também o que ele já baixou (não o que já chegou às pastas dos jogos)?",
    tasks: "Tarefas", no_tasks: "Nada rodando.", show_log: "Log", cancel: "Cancelar", task_ok: "pronto", task_fail: "falhou",
    trackball: "Trackball", ball_open: "Usar o celular como trackball", sensitivity: "Sensibilidade", inertia: "Continua rolando",
    ball_hint: "Role com o dedo (um giro rápido continua rolando; toque para parar).", ball_on: "Conectado: o gabinete vê um mouse USB.",
    btn_left: "Botão 1", btn_middle: "3", btn_right: "Botão 2",
    terminal: "Terminal", term_open: "Abrir o terminal", term_close: "Fechar", term_connecting: "Conectando…",
    term_on: "O shell do gabinete (zsh, usuário fliperos).", term_off: "Desconectado.",
    screen: "Tela", take_shot: "Tirar screenshot", as_on_tube: "4:3, como no tubo", save_png: "Salvar PNG",
    shot_wait: "Tirando a foto…", shot_from: "%w×%h, %s · %t", shot_x11: "desktop (X)", shot_gl: "quadro OpenGL",
    download: "Baixar",
    files: "Arquivos", up_folder: "Pasta de cima", upload: "Enviar arquivos", new_folder: "Nova pasta", folder_name: "Nome da pasta nova:",
    confirm_delete: "Apagar %s do gabinete?", uploading: "Enviando %s… %p%", uploaded: "Enviado(s): %n arquivo(s).",
    exists_overwrite: "%s já existe lá. Substituir?", empty_folder: "Pasta vazia.", delete: "Apagar",
    size: "Tamanho", modified: "Modificado", drop_hint: "Também dá para soltar arquivos na lista para enviá-los a esta pasta.",
  },
};

let lang = "en";
try {
  lang = localStorage.getItem("fliperos-lang") || (navigator.language || "").slice(0, 2);
} catch (e) {
  lang = (navigator.language || "").slice(0, 2);
}
if (!TEXT[lang]) lang = "en";
const t = (key) => TEXT[lang][key] || TEXT.en[key] || key;
const $ = (id) => document.getElementById(id);

function translate() {
  document.documentElement.lang = lang === "pt" ? "pt-BR" : "en";
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
  document.querySelectorAll("[data-tp]").forEach((el) => { el.placeholder = t(el.dataset.tp); });
  $("lang").textContent = lang === "pt" ? "EN" : "PT";
  // O balao do atraso: sem medida, o convite (com medida ele se refaz a cada segundo).
  const sync = $("live-sync-text");
  if (sync && !sync.dataset.measured) sync.textContent = t("sync_idle");
}

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") node.className = v; else node.setAttribute(k, v);
  }
  for (const c of children) node.append(c instanceof Node ? c : document.createTextNode(c == null ? "" : String(c)));
  return node;
}

function bytes(n) {
  if (n == null) return "-";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return (n >= 100 || i === 0 ? n.toFixed(0) : n.toFixed(1)) + " " + units[i];
}
const rate = (bps) => bytes(bps) + "/s";

function meter(pct) {
  const bar = el("div", { class: "meter" + (pct > 90 ? " hot" : pct > 70 ? " warn" : "") }, el("div"));
  bar.firstChild.style.width = Math.max(0, Math.min(100, pct || 0)) + "%";
  return bar;
}

function duration(s) {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return (d ? d + "d " : "") + (d || h ? h + "h " : "") + m + "min";
}

async function api(path, options) {
  const opts = Object.assign({ credentials: "same-origin", headers: {} }, options || {});
  if (opts.method === "POST") {
    opts.headers["Content-Type"] = "application/json";
    opts.headers["X-FliperOS"] = "1";
  }
  const res = await fetch(path, opts);
  if (res.status === 401) { showLogin(); throw new Error("login"); }
  return res;
}

// ── Login ────────────────────────────────────────────────────────

function showLogin() {
  $("app").hidden = true;
  $("login").hidden = false;
  stop();
  $("password").focus();
}

$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("login-error").textContent = "";
  const res = await fetch("/api/login", {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-FliperOS": "1" },
    body: JSON.stringify({ user: $("user").value, password: $("password").value }),
  });
  if (res.ok) {
    $("password").value = "";
    start();
  } else {
    const data = await res.json().catch(() => ({}));
    $("login-error").textContent = res.status === 401 ? t("wrong") : data.error || res.statusText;
  }
});

$("logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" }).catch(() => {});
  showLogin();
});

$("lang").addEventListener("click", () => {
  lang = lang === "pt" ? "en" : "pt";
  try { localStorage.setItem("fliperos-lang", lang); } catch (e) { /* sem armazenamento */ }
  translate();
  if (last) render(last);
  renderFilters();
  renderGames();
  renderRomFilter();
  loadSettings().catch(() => {});
});

// ── O FPS do ultimo minuto ───────────────────────────────────────

const fpsHistory = [];
function drawFps() {
  const canvas = $("fps-chart"), ctx = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * ratio; canvas.height = h * ratio;
  ctx.scale(ratio, ratio);
  ctx.clearRect(0, 0, w, h);
  const css = getComputedStyle(document.documentElement);
  const top = Math.max(60, ...fpsHistory.map((p) => p || 0)) * 1.1;
  ctx.strokeStyle = css.getPropertyValue("--line");
  ctx.setLineDash([3, 3]);
  const y60 = h - (60 / top) * h;
  ctx.beginPath(); ctx.moveTo(0, y60); ctx.lineTo(w, y60); ctx.stroke();
  ctx.setLineDash([]);
  ctx.strokeStyle = css.getPropertyValue("--green");
  ctx.lineWidth = 2;
  ctx.beginPath();
  let pen = false;
  fpsHistory.forEach((v, i) => {
    const x = (i / 59) * w;
    if (v == null) { pen = false; return; }
    const y = h - (v / top) * h;
    if (pen) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    pen = true;
  });
  ctx.stroke();
}

// ── Os cartoes ───────────────────────────────────────────────────

let last = null;
function render(s) {
  last = s;
  $("version").textContent = s.version ? "v" + s.version : "";
  const ips = Object.values(s.network || {}).flatMap((n) => n.ipv4 || []);
  $("host").textContent = [s.host, ips.join(", "), s.uptime ? t("uptime") + " " + duration(s.uptime) : ""]
    .filter(Boolean).join(" · ");

  // Jogando agora.
  const game = s.running && s.running.game, front = s.running && s.running.frontend;
  $("game").textContent = game ? (game.file || game.program) : t("nothing");
  const fps = s.fps;
  $("game-detail").textContent = game
    ? [game.program, fps && fps.core ? t("core") + " " + fps.core : "", fps && fps.filtering ? t("filtering") : ""]
      .filter(Boolean).join(" · ")
    : "";
  $("frontend").textContent = front ? t("frontend") + ": " + front.program : "";
  $("close-game").hidden = !game;
  $("fps").textContent = fps ? fps.fps.toFixed(1) : "-";
  fpsHistory.push(fps ? fps.fps : null);
  while (fpsHistory.length > 60) fpsHistory.shift();
  drawFps();

  // Video: o pedido e o aplicado.
  const v = s.video || {}, w = v.wanted || {};
  const table = $("video-table");
  table.replaceChildren();
  const add = (k, val) => table.append(el("tr", {}, el("th", {}, t(k)), el("td", {}, val || "-")));
  table.append(el("tr", {}, el("th", { colspan: "2", class: "vid-part" }, t("wanted"))));
  add("monitor", w.monitor); add("frequency", w.frequency); add("resolution", w.boot_resolution);
  add("connector", w.connector); add("orientation", w.orientation);
  table.append(el("tr", {}, el("th", { colspan: "2", class: "vid-part" }, t("applied"))));
  const active = (v.outputs || []).filter((o) => o.active);
  $("modelines").replaceChildren();
  if (!active.length) add("mode", t("no_output"));
  for (const o of active) {
    add("connector", o.connector + " (" + o.card.replace("/dev/dri/", "") + ")");
    add("mode", o.width + "x" + o.height);
    add("hsync", o.horizontal_khz + " kHz");
    add("vsync", o.vertical_hz + " Hz");
    add("scan", o.interlaced ? t("interlaced") : t("progressive"));
    $("modelines").append(el("div", { class: "modeline" }, o.connector + ": Modeline " + o.modeline));
  }
  if (v.framebuffer) add("framebuffer", v.framebuffer);

  // CPU.
  const cpu = s.cpu || {};
  $("cpu-total").textContent = (cpu.total ?? 0).toFixed(0) + "%";
  $("cpu-bar").style.width = (cpu.total || 0) + "%";
  $("load").textContent = t("load") + " " + (s.load || []).join(" ");
  $("cores").replaceChildren(...(cpu.cores || []).map((c, i) =>
    el("div", { class: "core" }, "#" + i + " " + c.toFixed(0) + "%", meter(c))));
  $("temps").replaceChildren(...(s.temperatures || []).filter((x) => !/amdgpu|radeon|nouveau/.test(x.sensor))
    .slice(0, 6).map((x) => el("div", {}, el("span", {}, x.sensor + (x.label ? " " + x.label : "")),
      el("span", {}, x.celsius + " °C"))));

  // GPU.
  $("gpus").replaceChildren(...(Array.isArray(s.gpus) ? s.gpus : []).map((g) => {
    const lines = [el("div", { class: "row" }, el("span", {}, g.name || g.slot), el("span", { class: "tag" }, g.driver))];
    if (g.busy != null) lines.push(el("div", { class: "dim" }, t("busy") + " " + g.busy + "%"), meter(g.busy));
    const facts = [];
    if (g.vram_total) facts.push(t("vram") + " " + bytes(g.vram_used) + " " + t("of") + " " + bytes(g.vram_total));
    if (g.clock) facts.push(t("clock") + " " + g.clock);
    if (g.celsius != null) facts.push(t("temp") + " " + g.celsius + " °C");
    if (g.watts != null) facts.push(t("power") + " " + g.watts + " W");
    if (facts.length) lines.push(el("div", { class: "dim" }, facts.join(" · ")));
    return el("div", { class: "item" }, ...lines);
  }));

  // Memoria.
  const m = s.memory || {};
  $("memory").replaceChildren(
    el("div", { class: "row" }, el("span", {}, bytes(m.used) + " " + t("of") + " " + bytes(m.total)),
      el("span", { class: "dim" }, m.total ? Math.round((100 * m.used) / m.total) + "%" : "")),
    meter(m.total ? (100 * m.used) / m.total : 0),
    m.swap_total ? el("div", { class: "dim" }, t("swap") + " " + bytes(m.swap_used) + " " + t("of") + " " + bytes(m.swap_total)) : "");
  // Armazenamento: cada disco montado.
  $("disks").replaceChildren(...(Array.isArray(s.disks) ? s.disks : []).map((d) => el("div", { class: "item" },
    el("div", { class: "row" }, el("span", {}, d.mount), el("span", { class: "dim" }, bytes(d.used) + " / " + bytes(d.total))),
    meter(d.total ? (100 * d.used) / d.total : 0))));

  // Rede.
  const net = Object.entries(s.network || {});
  $("network").replaceChildren(...net.map(([name, n]) => el("div", { class: "item" },
    el("div", { class: "row" }, el("span", {}, name), el("span", { class: "dim" }, (n.ipv4 || []).join(", "))),
    el("div", { class: "dim" }, "↓ " + rate(n.rx_bps) + " · ↑ " + rate(n.tx_bps)))),
  s.wifi ? el("div", { class: "dim" }, "Wi-Fi " + s.wifi.ssid + " · " + t("signal") + " " + s.wifi.signal + "%") : "");

  // Volume.
  const vol = s.volume && s.volume.percent;
  $("vol-value").textContent = vol == null ? "-" : vol + "%";
  if (vol != null && document.activeElement !== $("vol")) $("vol").value = vol;
  $("vol").disabled = vol == null;
  muteButton(s.volume && s.volume.muted);

  renderProcesses(s.processes || []);
}

// ── Processos ────────────────────────────────────────────────────
// A tabela tem colunas de largura fixa e as mesmas linhas a cada segundo
// (so o texto muda): o layout nao pula quando um nome comprido aparece ou
// some. O nome que nao cabe termina em "…" e, de tempos em tempos, rola
// como um letreiro ate o fim e volta (banner()).

const PROC_ROWS = 15;
let procCells = null;
let lastProcesses = [];
// A ordem: a coluna e o sentido (o clique no cabecalho troca; no mesmo
// cabecalho, inverte). Lembrada no navegador, quando da.
const PROC_COLUMNS = [
  { key: "pid", label: () => "PID", num: false, first: "asc" },
  { key: "name", label: () => t("name"), num: false, first: "asc" },
  { key: "cpu", label: () => t("cpu"), num: true, first: "desc" },
  { key: "mem_mb", label: () => t("mem"), num: true, first: "desc" },
];
let procSort = { key: "cpu", dir: "desc" };
try {
  const saved = JSON.parse(localStorage.getItem("fliperos-proc-sort") || "null");
  if (saved && PROC_COLUMNS.some((c) => c.key === saved.key) && (saved.dir === "asc" || saved.dir === "desc")) {
    procSort = saved;
  }
} catch (e) { /* sem armazenamento */ }

function sortProcesses(list) {
  const { key, dir } = procSort, sign = dir === "asc" ? 1 : -1;
  return list.slice().sort((a, b) => {
    const x = a[key], y = b[key];
    const order = typeof x === "string" ? x.localeCompare(y, undefined, { sensitivity: "base" }) : x - y;
    // Empate: o que mais usa CPU, depois o PID (a ordem nao fica pulando).
    return sign * order || b.cpu - a.cpu || a.pid - b.pid;
  });
}

function procHeader() {
  return el("tr", {}, ...PROC_COLUMNS.map((c) => {
    const active = procSort.key === c.key;
    const arrow = active ? (procSort.dir === "asc" ? " ▲" : " ▼") : "";
    const button = el("button", { type: "button", class: "sort" }, c.label() + arrow);
    button.addEventListener("click", () => {
      procSort = active ? { key: c.key, dir: procSort.dir === "asc" ? "desc" : "asc" } : { key: c.key, dir: c.first };
      try { localStorage.setItem("fliperos-proc-sort", JSON.stringify(procSort)); } catch (e) { /* sem armazenamento */ }
      $("procs").tHead.replaceChildren(procHeader());
      renderProcesses(lastProcesses);
    });
    const th = el("th", { class: c.num ? "num" : "", scope: "col" }, button);
    th.setAttribute("aria-sort", active ? (procSort.dir === "asc" ? "ascending" : "descending") : "none");
    return th;
  }));
}

function procTable() {
  const table = $("procs");
  const head = procHeader();
  const body = el("tbody");
  procCells = [];
  for (let i = 0; i < PROC_ROWS; i++) {
    const text = el("span");
    const cells = { pid: el("td"), name: el("td", { class: "name" }, el("span", { class: "clip" }, text)), text,
      cpu: el("td", { class: "num" }), mem: el("td", { class: "num" }) };
    cells.row = el("tr", {}, cells.pid, cells.name, cells.cpu, cells.mem);
    body.append(cells.row);
    procCells.push(cells);
  }
  table.replaceChildren(el("colgroup", {}, el("col", { class: "c-pid" }), el("col"), el("col", { class: "c-cpu" }),
    el("col", { class: "c-mem" })), el("thead", {}, head), body);
}

function setText(node, value) {
  if (node.textContent !== value) node.textContent = value;
}

function renderProcesses(all) {
  lastProcesses = all;
  const list = sortProcesses(all);
  if (!procCells || procCells.lang !== lang) {
    procTable();
    procCells.lang = lang;
  }
  procCells.forEach((cells, i) => {
    const p = list[i];
    cells.row.hidden = !p;
    if (!p) return;
    setText(cells.pid, String(p.pid));
    if (cells.text.textContent !== p.name) {
      // Outro nome nesta linha: o letreiro recomeca do inicio.
      cells.name.classList.remove("rolling");
      cells.text.textContent = p.name;
      cells.name.title = p.name;
    }
    setText(cells.cpu, p.cpu.toFixed(1) + "%");
    setText(cells.mem, p.mem_mb + " MB");
  });
}

// banner: os nomes que nao cabem rolam ate o fim (devagar, uns 40 px por
// segundo, parando nas pontas) e voltam ao "…".
function banner() {
  // Sem animacao pedida pelo sistema: fica so o "…" (o title tem o nome).
  if (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  for (const cells of procCells || []) {
    const clip = cells.name.firstChild;
    if (cells.row.hidden || cells.name.classList.contains("rolling")) continue;
    const extra = clip.scrollWidth - clip.clientWidth;
    if (extra <= 2) continue;
    cells.text.style.setProperty("--shift", -extra + "px");
    cells.text.style.setProperty("--time", Math.max(3, extra / 40 + 2) + "s");
    cells.name.classList.add("rolling");
  }
}
document.addEventListener("animationend", (event) => {
  const cell = event.target.closest && event.target.closest("td.name");
  if (cell) cell.classList.remove("rolling");
});
setInterval(banner, 5000);

// ── Volume e logs ────────────────────────────────────────────────

async function volume(body) {
  const res = await api("/api/volume", { method: "POST", body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (data.percent != null) { $("vol").value = data.percent; $("vol-value").textContent = data.percent + "%"; }
  muteButton(data.muted);
}
// O botao Mudo fica marcado enquanto o som esta mudo (pelas teclas do
// gabinete tambem: o status traz o estado do mixer).
function muteButton(muted) {
  $("vol-mute").setAttribute("aria-pressed", String(!!muted));
  $("vol-mute").classList.toggle("on", !!muted);
}
$("vol-up").addEventListener("click", () => volume({ action: "up" }));
$("vol-down").addEventListener("click", () => volume({ action: "down" }));
$("vol-mute").addEventListener("click", () => volume({ action: "mute" }));
$("vol").addEventListener("change", () => volume({ set: Number($("vol").value) }));

async function loadLogs() {
  const res = await api("/api/logs");
  const data = await res.json();
  const select = $("log-name"), keep = select.value;
  select.replaceChildren(...data.logs.map((n) => el("option", { value: n }, n)));
  if (data.logs.includes(keep)) select.value = keep;
  await showLog();
}
async function showLog() {
  const name = $("log-name").value;
  if (!name) { $("log-text").textContent = ""; return; }
  const res = await api("/api/log?name=" + encodeURIComponent(name) + "&lines=300");
  const data = await res.json();
  const pre = $("log-text");
  pre.textContent = data.text || "";
  pre.scrollTop = pre.scrollHeight;
}
$("log-name").addEventListener("change", showLog);
$("log-refresh").addEventListener("click", showLog);

// ── Jogos: abrir e fechar no gabinete ────────────────────────────
// As pastas com jogos (as mesmas dos frontends). A lista e a do Attract-Mode
// Plus (o nome de verdade, o ano, o fabricante), com os filtros da tela dele
// no fim da busca. Cada jogo abre (um por vez) com as informacoes: as da
// romlist e as da internet (/api/gameinfo: o Arcade Database nos arcades, o
// libretro-thumbnails nos consoles), que o navegador guarda. No fim, Jogar
// (fecha o que esta na tela; quando o jogo fecha, volta o que estava) e
// Favoritar (os favoritos do frontend).

const GAMES_SHOWN = 300;
const INFO_KEY = "fliperos-info:";
const INFO_DAYS = 30;
let allGames = [], gameFilters = [], openGame = null;

function toast(text) {
  const box = el("div", { class: "toast", role: "status" }, text);
  document.body.append(box);
  setTimeout(() => box.remove(), 4000);
}

async function loadSystems() {
  const res = await api("/api/systems");
  const data = await res.json();
  const select = $("system");
  let keep = select.value;
  try { keep = keep || localStorage.getItem("fliperos-system") || ""; } catch (e) { /* sem armazenamento */ }
  const rows = (data.systems || []).filter((s) => s.games > 0);
  select.replaceChildren(...rows.map((s) => el("option", { value: s.key }, s.name + " (" + s.games + ")")));
  if (rows.some((s) => s.key === keep)) select.value = keep;
  await loadGames();
}

async function loadGames() {
  const key = $("system").value;
  openGame = null;
  if (!key) { allGames = []; gameFilters = []; renderFilters(); renderGames(); return; }
  try { localStorage.setItem("fliperos-system", key); } catch (e) { /* sem armazenamento */ }
  const res = await api("/api/games?system=" + encodeURIComponent(key));
  const data = await res.json();
  allGames = data.games || [];
  gameFilters = data.filters || [];
  renderFilters();
  renderGames();
}

// Os filtros da tela do Attract-Mode, como ele os aplica: as regras na
// ordem; uma regra que falha tira o jogo, uma excecao que bate o poe de
// volta. Com uma regex (um caractere especial no valor), equals e a palavra
// inteira; sem, a comparacao ignora maiusculas.
const NUMERIC_OPS = { greater_than: (a, b) => a > b, less_than: (a, b) => a < b,
  greater_than_or_equal: (a, b) => a >= b, less_than_or_equal: (a, b) => a <= b };

function ruleMatches(rule, game) {
  const target = String(game[rule.field] == null ? "" : game[rule.field]), what = rule.what || "";
  if (NUMERIC_OPS[rule.op]) return NUMERIC_OPS[rule.op](parseFloat(target) || 0, parseFloat(what) || 0);
  if (rule.rex === undefined) {
    rule.rex = null;
    if (/[.+*?^$()[\]{}|\\]/.test(what)) {
      try { rule.rex = [new RegExp("^(?:" + what + ")$", "i"), new RegExp(what, "i")]; } catch (e) { /* literal */ }
    }
  }
  const low = target.toLowerCase(), w = what.toLowerCase(), rex = rule.rex;
  switch (rule.op) {
    case "equals": return !target ? !what : rex ? rex[0].test(target) : low === w;
    case "not_equals": return !target ? !!what : rex ? !rex[0].test(target) : low !== w;
    case "contains": return !!target && (rex ? rex[1].test(target) : low.includes(w));
    case "not_contains": return !target || (rex ? !rex[1].test(target) : !low.includes(w));
    default: return true;
  }
}

function compareValues(a, b) {
  const x = a == null ? "" : String(a), y = b == null ? "" : String(b);
  const nx = Number(x), ny = Number(y);
  if (x !== "" && y !== "" && !isNaN(nx) && !isNaN(ny)) return nx - ny;
  return x.localeCompare(y, undefined, { sensitivity: "base" });
}

function applyFilter(list, filter) {
  if (!filter) return list;
  let out = list.filter((game) => {
    for (const rule of filter.rules || []) {
      if (ruleMatches(rule, game) === !!rule.exception) return !!rule.exception;
    }
    return true;
  });
  if (filter.sort_by) out = out.slice().sort((a, b) => compareValues(a[filter.sort_by], b[filter.sort_by]));
  if (filter.reverse) out.reverse();
  if (filter.limit > 0) out = out.slice(0, filter.limit);
  else if (filter.limit < 0) out = out.slice(filter.limit);
  return out;
}

const FAV_FILTER = { name: "__fav", rules: [{ field: "Favourite", op: "equals", what: "1" }] };

function filterOptions() {
  // Os da tela (sem tela, todos os jogos) e os favoritos, se a tela nao os tem.
  const rows = gameFilters.map((f) => ({ value: f.name, label: f.name, filter: f }));
  if (!rows.length) rows.push({ value: "__all", label: t("filter_all"), filter: null });
  if (!gameFilters.some((f) => (f.rules || []).some((r) => r.field === "Favourite"))) {
    rows.push({ value: "__fav", label: "★ " + t("favourites"), filter: FAV_FILTER });
  }
  return rows;
}

function renderFilters() {
  const select = $("game-filter");
  let keep = select.value;
  try { keep = localStorage.getItem("fliperos-filter") || keep; } catch (e) { /* sem armazenamento */ }
  const rows = filterOptions();
  select.replaceChildren(...rows.map((r) => el("option", { value: r.value }, r.label)));
  select.value = rows.some((r) => r.value === keep) ? keep : rows[0].value;
}

function currentFilter() {
  const row = filterOptions().find((r) => r.value === $("game-filter").value);
  return row ? row.filter : null;
}

function renderGames() {
  const query = $("game-search").value.trim().toLowerCase();
  let found = applyFilter(allGames, currentFilter());
  if (query) {
    found = found.filter((g) => (g.Title || "").toLowerCase().includes(query) || g.Name.toLowerCase().includes(query));
  }
  const shown = found.slice(0, GAMES_SHOWN);
  $("games").replaceChildren(...shown.map(gameItem));
  $("games-note").textContent = !allGames.length ? t("no_games")
    : found.length > GAMES_SHOWN ? t("first").replace("%n", GAMES_SHOWN)
      : t("count").replace("%n", found.length);
}

function gameItem(game) {
  const open = openGame === game.Name;
  const head = el("button", { type: "button", class: "game-head", "aria-expanded": String(open) },
    el("span", { class: "star", "aria-label": game.Favourite ? t("favourites") : "" }, game.Favourite ? "★" : ""),
    el("span", { class: "title", title: game.Title || game.Name }, game.Title || game.Name),
    el("span", { class: "meta" }, [game.Year, game.Manufacturer].filter(Boolean).join(" · ")),
    el("span", { class: "chev", "aria-hidden": "true" }, "▸"));
  const li = el("li", {}, head);
  head.addEventListener("click", () => toggleGame(game, li));
  if (open) li.append(gameBody(game));
  return li;
}

function toggleGame(game, li) {
  const list = $("games");
  list.querySelectorAll(".game-body").forEach((b) => b.remove());
  list.querySelectorAll('.game-head[aria-expanded="true"]').forEach((h) => h.setAttribute("aria-expanded", "false"));
  if (openGame === game.Name) { openGame = null; return; }
  openGame = game.Name;
  li.firstChild.setAttribute("aria-expanded", "true");
  li.append(gameBody(game));
  li.scrollIntoView({ block: "nearest" });
}

function factList() {
  const dl = el("dl", { class: "facts" });
  dl.add = (label, value) => {
    if (value == null || value === "" || dl.querySelector('[data-k="' + label + '"]')) return;
    dl.append(el("div", { "data-k": label }, el("dt", {}, t(label)), el("dd", {}, value)));
  };
  return dl;
}

function gameBody(game) {
  const facts = factList();
  facts.add("g_file", game.file || game.Name);
  facts.add("g_year", game.Year);
  facts.add("g_maker", game.Manufacturer);
  facts.add("g_genre", game.Category);
  facts.add("g_players", game.Players);
  facts.add("g_buttons", game.Buttons);
  facts.add("g_control", game.Control);
  facts.add("g_screen", game.Rotation ? game.Rotation + "°" : "");
  facts.add("g_status", game.Status);
  facts.add("g_parent", game.CloneOf);
  facts.add("g_series", game.Series);
  if (game.PlayedCount) {
    facts.add("g_played", t("g_played_n").replace("%n", game.PlayedCount).replace("%t", duration(game.PlayedTime || 0)));
  }
  const online = el("div", { class: "game-online" }, el("p", { class: "dim" }, t("g_loading")));
  const play = el("button", { type: "button", "data-icon": "▶" }, t("play"));
  play.addEventListener("click", () => playGame(game));
  const fav = el("button", { type: "button", class: "ghost fav" + (game.Favourite ? " on" : ""),
    "aria-pressed": String(!!game.Favourite) }, (game.Favourite ? "★ " : "☆ ") + t(game.Favourite ? "favourited" : "favourite"));
  fav.addEventListener("click", () => toggleFavourite(game));
  const body = el("div", { class: "game-body" }, facts, online, el("div", { class: "game-actions" }, play, fav));
  gameInfo(game).then((data) => showOnline(online, facts, data))
    .catch(() => online.replaceChildren(el("p", { class: "dim" }, t("g_offline"))));
  return body;
}

// As informacoes da internet: do localStorage quando ja vieram (30 dias).
async function gameInfo(game) {
  const system = $("system").value, key = INFO_KEY + system + ":" + game.Name;
  try {
    const hit = JSON.parse(localStorage.getItem(key) || "null");
    if (hit && Date.now() - hit.t < INFO_DAYS * 86400000) return hit.d;
  } catch (e) { /* sem armazenamento */ }
  const res = await api("/api/gameinfo?system=" + encodeURIComponent(system) + "&game=" + encodeURIComponent(game.Name));
  if (!res.ok) throw new Error(res.statusText);
  const data = await res.json();
  cacheInfo(key, data);
  return data;
}

function cacheInfo(key, data) {
  const value = JSON.stringify({ t: Date.now(), d: data });
  for (let tries = 0; tries < 2; tries++) {
    try { localStorage.setItem(key, value); return; } catch (e) {
      // Cheio: sai a metade mais antiga das informacoes guardadas.
      try {
        const old = Object.keys(localStorage).filter((k) => k.startsWith(INFO_KEY))
          .map((k) => [k, (JSON.parse(localStorage.getItem(k)) || {}).t || 0]).sort((a, b) => a[1] - b[1]);
        if (!old.length) return;
        old.slice(0, Math.ceil(old.length / 2)).forEach(([k]) => localStorage.removeItem(k));
      } catch (e2) { return; }
    }
  }
}

function pictures(list) {
  // As imagens que existem (a que nao carrega sai); cada uma abre inteira.
  const box = el("div", { class: "pics" });
  for (const p of list) {
    const img = el("img", { src: p.url, alt: t(p.label), loading: "lazy", referrerpolicy: "no-referrer" });
    const fig = el("figure", {}, el("a", { href: p.url, target: "_blank", rel: "noopener noreferrer" }, img),
      el("figcaption", {}, t(p.label)));
    img.addEventListener("error", () => { fig.remove(); if (!box.children.length) box.remove(); });
    box.append(fig);
  }
  return box;
}

function showOnline(online, facts, data) {
  const parts = [];
  if (data.images) {
    parts.push(pictures(data.images.map((i) => ({ url: i.url, label: "pic_" + i.kind }))));
  }
  const info = data.info;
  if (data.source === "Arcade Database" && !info) parts.push(el("p", { class: "dim" }, t("g_not_found")));
  if (info) {
    parts.push(pictures([["url_image_ingame", "pic_snap"], ["url_image_title", "pic_title"],
      ["url_image_marquee", "pic_marquee"], ["url_image_flyer", "pic_flyer"], ["url_image_cabinet", "pic_cabinet"]]
      .filter(([k]) => info[k]).map(([k, label]) => ({ url: info[k], label }))));
    facts.add("g_title", info.title);
    facts.add("g_genre", info.genre);
    facts.add("g_series", info.serie);
    facts.add("g_players", info.nplayers || info.players);
    facts.add("g_buttons", info.input_buttons);
    facts.add("g_control", info.input_controls);
    facts.add("g_screen", [info.screen_orientation, info.screen_resolution].filter(Boolean).join(", "));
    facts.add("g_status", info.status);
    facts.add("g_rating", info.rate ? info.rate + "/100" : "");
    facts.add("g_language", info.languages);
    // Os botoes do jogador 1, com a cor e o que fazem.
    const keys = (info.buttons_colors || "").split(";").map((s) => s.split(":"))
      .filter((p) => p.length >= 3 && p[0].startsWith("P1_") && p[2]);
    if (keys.length) {
      parts.push(el("div", { class: "controls" }, ...keys.map(([, color, label]) => {
        const dot = el("i");
        dot.style.background = /^[a-z]+$/i.test(color) ? color : "transparent";
        return el("span", { class: "tag" }, dot, label);
      })));
    }
    if (info.history) {
      parts.push(el("pre", { class: "history" }, info.history.trim()));
    }
    const links = el("div", { class: "links" });
    if (info.url) links.append(el("a", { class: "ghost-link", href: info.url, target: "_blank", rel: "noopener" }, "Arcade Database"));
    if (info.url_video_shortplay) links.append(el("a", { class: "ghost-link", href: info.url_video_shortplay, target: "_blank", rel: "noopener" }, t("g_video")));
    if (info.youtube_video_id) {
      links.append(el("a", { class: "ghost-link", target: "_blank", rel: "noopener",
        href: "https://www.youtube.com/watch?v=" + encodeURIComponent(info.youtube_video_id) }, "YouTube"));
    }
    if (info.history_copyright_short) links.append(el("span", { class: "dim" }, info.history_copyright_short));
    parts.push(links);
  }
  online.replaceChildren(...parts);
}

async function playGame(game) {
  const name = game.Title || game.Name;
  if (!confirm(t("confirm_launch").replace("%s", name))) return;
  const res = await api("/api/launch", { method: "POST", body: JSON.stringify({ system: $("system").value, game: game.Name }) });
  const data = await res.json().catch(() => ({}));
  toast(res.ok ? t("launching").replace("%s", name) : data.error || res.statusText);
}

async function toggleFavourite(game) {
  const res = await api("/api/favourite", { method: "POST",
    body: JSON.stringify({ system: $("system").value, game: game.Name, on: !game.Favourite }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { toast(data.error || res.statusText); return; }
  if (data.favourite) game.Favourite = "1"; else delete game.Favourite;
  renderGames();
}

$("system").addEventListener("change", () => loadGames().catch(() => {}));
$("game-search").addEventListener("input", renderGames);
$("game-filter").addEventListener("change", () => {
  try { localStorage.setItem("fliperos-filter", $("game-filter").value); } catch (e) { /* sem armazenamento */ }
  renderGames();
});
$("close-game").addEventListener("click", async () => {
  if (!confirm(t("confirm_close"))) return;
  await api("/api/close", { method: "POST", body: "{}" }).catch(() => {});
});

// ── Configuracoes ────────────────────────────────────────────────
// Os ajustes do Setup que podem mudar daqui (fliperos-setup --settings):
// cada mudanca grava na hora. Os grupos abertos ficam abertos.

const openGroups = new Set(["System"]);

async function loadSettings() {
  const res = await api("/api/settings");
  const rows = (await res.json()).settings || [];
  const groups = new Map();
  for (const row of rows) {
    if (!groups.has(row.group)) groups.set(row.group, []);
    groups.get(row.group).push(row);
  }
  const boxes = [];
  for (const [group, items] of groups) {
    const details = el("details", {}, el("summary", {}, t("group_" + group)));
    if (openGroups.has(group)) details.open = true;
    details.addEventListener("toggle", () => {
      details.open ? openGroups.add(group) : openGroups.delete(group);
    });
    for (const row of items) details.append(settingRow(row));
    boxes.push(details);
  }
  $("settings").replaceChildren(...boxes);
}

function settingRow(row) {
  const id = "set-" + row.key.replace(/[^a-z0-9]/gi, "-");
  let control;
  if (row.type === "action") {
    // Um botao (o voltar ao padrao das cores): depois dele, os outros
    // ajustes do grupo mudaram, e a lista volta do Setup.
    const button = el("button", { id, type: "button", class: "ghost" }, row.label);
    button.addEventListener("click", async () => {
      if (!confirm(row.help)) return;
      button.disabled = true;
      try {
        const res = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: row.key, value: "1" }) });
        const data = await res.json().catch(() => ({}));
        toast(res.ok ? t("saved").replace("%s", row.label) : (data.error || res.statusText));
        await loadSettings();
      } finally {
        button.disabled = false;
      }
    });
    return el("div", { class: "setting" }, button, el("div", { class: "dim" }, row.help));
  }
  if (row.type === "choice") {
    control = el("select", { id }, ...row.options.map((o) => el("option", { value: o.value }, o.label)));
    control.value = row.value;
  } else {
    // Os numeros (a calibracao de cor): um slider com o valor ao lado, que
    // anda junto; grava ao soltar.
    control = el("input", { id, type: "range", min: String(row.min), max: String(row.max),
      step: String(row.step || 1), value: row.value });
  }
  const about = el("div", { class: "dim" }, row.help);
  let shown = null;
  // Os sliders gravam tambem enquanto andam (um a cada 300 ms): a cor muda
  // na tela do jogo com o dedo ainda no slider. Eles nao ficam desligados
  // enquanto gravam, senao o arrasto parava.
  let timer = null, busy = false;
  if (row.type === "number") {
    shown = el("output", { for: id, class: "slider-value" }, prettyNumber(row.key, row.value));
    control.addEventListener("input", () => {
      shown.textContent = prettyNumber(row.key, control.value);
      clearTimeout(timer);
      timer = setTimeout(() => { if (!busy) save(true); }, 300);
    });
  }
  control.addEventListener("change", () => { clearTimeout(timer); save(false); });
  async function save(dragging) {
    const number = row.type === "number";
    if (!number) control.disabled = true;
    busy = true;
    try {
      const res = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: row.key, value: control.value }) });
      const data = await res.json().catch(() => ({}));
      if (dragging) return;
      if (res.ok && data.setting) {
        control.value = data.setting.value;
        about.textContent = data.setting.help;
        row.value = data.setting.value;
        toast(t("saved").replace("%s", row.label));
      } else {
        control.value = row.value;
        toast(data.error || res.statusText);
      }
      if (shown) shown.textContent = prettyNumber(row.key, control.value);
    } finally {
      busy = false;
      control.disabled = false;
    }
  }
  const field = shown ? el("div", { class: "slider" }, control, shown) : control;
  return el("div", { class: "setting" }, el("label", { for: id }, row.label), field, about);
}

// prettyNumber: o valor como o Setup mostra (1.00, 6500 K, 100%, +5).
function prettyNumber(key, value) {
  const v = Number(value);
  if (/gamma$/.test(key)) return (v / 100).toFixed(2);
  if (/temperature$/.test(key)) return v + " K";
  if (/(contrast|gain|saturation)$/.test(key)) return v + "%";
  if (/hue$/.test(key)) return v + "°";
  return v > 0 ? "+" + v : String(v);
}

// ── Downloads e tarefas ──────────────────────────────────────────
// O Downloader do Setup (o filtro do MAME ROM Cleaner escolhe o que baixar
// dos torrents): o andamento, os links e o comecar. O que leva minutos vira
// uma tarefa, com a etapa, a porcentagem e o log.

let dlState = {}, openLogs = new Set();

async function loadDownloader() {
  const res = await api("/api/downloader");
  dlState = await res.json();
  const pct = Number(dlState.pct || 0);
  $("dl-text").textContent = dlState.line || "";
  $("dl-pct").textContent = dlState.state === "downloading" ? pct + "%" : "";
  $("dl-bar").style.width = pct + "%";
  $("dl-filter").textContent = dlState.filter || "-";
  if (document.activeElement && document.activeElement.closest(".dl-kind")) return;
  $("dl-kinds").replaceChildren(...["roms", "chds"].map((kind) => {
    const name = dlState[kind + "_name"];
    const box = el("div", { class: "dl-kind" }, el("strong", {}, t("dl_" + kind)),
      el("div", { class: name ? "" : "dim" }, name ? name + " · " + (dlState[kind + "_sets"] || 0) + " sets" : t("dl_none")));
    if (name) {
      const remove = el("button", { type: "button", class: "ghost danger", "data-icon": "🗑" }, t("dl_remove"));
      remove.addEventListener("click", async () => {
        if (!confirm(t("dl_remove_ask"))) return;
        const del = confirm(t("dl_delete_ask"));
        await api("/api/downloader", { method: "POST", body: JSON.stringify({ action: "remove", kind, delete: del }) });
        loadDownloader();
      });
      box.append(remove);
    } else {
      const input = el("input", { type: "text", placeholder: t("dl_paste"), autocomplete: "off" });
      const add = el("button", { type: "button", "data-icon": "🔗" }, t("dl_add"));
      add.addEventListener("click", () => downloaderTask({ action: "add", kind, magnet: input.value.trim() }));
      box.append(el("div", { class: "row" }, input, add));
      if (dlState["default_" + kind]) {
        const def = el("button", { type: "button", class: "ghost", "data-icon": "⭐" }, t("dl_default"));
        def.addEventListener("click", () => downloaderTask({ action: "add", kind }));
        box.append(def);
      }
    }
    return box;
  }));
}

async function downloaderTask(body) {
  const res = await api("/api/downloader", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) toast((await res.json().catch(() => ({}))).error || res.statusText);
  loadTasks();
  loadDownloader();
}
$("dl-start").addEventListener("click", () => downloaderTask({ action: "start" }));

async function loadTasks() {
  const res = await api("/api/tasks");
  const tasks = (await res.json()).tasks || [];
  const list = $("tasks");
  if (!tasks.length) { list.replaceChildren(el("li", { class: "dim" }, t("no_tasks"))); return; }
  const rows = [];
  for (const task of tasks) {
    const state = task.running ? (task.pct != null ? task.pct + "%" : "…")
      : task.rc === 0 ? "✓ " + t("task_ok") : "✗ " + t("task_fail") + " (" + task.rc + ")";
    const head = el("div", { class: "row" }, el("strong", {}, task.name),
      el("span", { class: task.running ? "dim" : task.rc === 0 ? "ok" : "fail" }, state));
    const item = el("li", {}, head);
    if (task.running) item.append(meter(task.pct || 0));
    const detail = task.error || task.step || task.last;
    if (detail) item.append(el("div", { class: "dim" }, detail));
    const actions = el("div", { class: "row" });
    const logButton = el("button", { type: "button", class: "ghost", "data-icon": "📜" }, t("show_log"));
    logButton.addEventListener("click", () => {
      openLogs.has(task.id) ? openLogs.delete(task.id) : openLogs.add(task.id);
      loadTasks();
    });
    actions.append(logButton);
    if (task.running) {
      const cancel = el("button", { type: "button", class: "ghost danger", "data-icon": "✖" }, t("cancel"));
      cancel.addEventListener("click", async () => {
        await api("/api/task/cancel", { method: "POST", body: JSON.stringify({ id: task.id }) });
        loadTasks();
      });
      actions.append(cancel);
    }
    item.append(actions);
    if (openLogs.has(task.id)) {
      const r = await api("/api/task?id=" + task.id);
      const pre = el("pre", { class: "log" }, (await r.json()).log || "");
      item.append(pre);
      requestAnimationFrame(() => { pre.scrollTop = pre.scrollHeight; });
    }
    rows.push(item);
  }
  list.replaceChildren(...rows);
}

// ── Trackball: o celular como mouse do gabinete ──────────────────
// O dedo na area rola a bola: os movimentos vao pelo WebSocket
// /api/trackball, juntados a cada quadro da tela. Soltando depois de um
// giro rapido, a bola continua rolando e freia aos poucos, como um trackball
// de fliperama; um toque a segura.

let ball = null, ballSend = { x: 0, y: 0 }, ballVel = { x: 0, y: 0 }, ballLast = null, ballSpin = 0;

function ballWs(msg) {
  if (ball && ball.readyState === 1) ball.send(JSON.stringify(msg));
}

function ballFlush() {
  const dx = Math.trunc(ballSend.x), dy = Math.trunc(ballSend.y);
  if (dx || dy) {
    ballWs({ m: [dx, dy] });
    ballSend.x -= dx;
    ballSend.y -= dy;
  }
}

function ballFrame(time) {
  // A inercia: anda com a velocidade e freia (a cada 16 ms, 6%).
  if (ballSpin && !ballLast) {
    const dt = Math.min(50, time - ballSpin);
    ballSpin = time;
    ballSend.x += ballVel.x * dt;
    ballSend.y += ballVel.y * dt;
    const friction = Math.pow(0.94, dt / 16);
    ballVel.x *= friction;
    ballVel.y *= friction;
    if (Math.abs(ballVel.x) + Math.abs(ballVel.y) < 0.01) ballSpin = 0;
  }
  ballFlush();
  if (ball) requestAnimationFrame(ballFrame);
}

function openBall() {
  const scheme = location.protocol === "https:" ? "wss://" : "ws://";
  ball = new WebSocket(scheme + location.host + "/api/trackball");
  ball.onopen = () => {
    $("ball").hidden = false;
    $("ball-open").hidden = true;
    $("ball-note").textContent = t("ball_on");
    requestAnimationFrame(ballFrame);
  };
  ball.onclose = () => {
    $("ball").hidden = true;
    $("ball-open").hidden = false;
    $("ball-note").textContent = t("term_off");
    ball = null;
  };
}

$("ball-open").addEventListener("click", openBall);
const pad = $("ball-pad");
pad.addEventListener("pointerdown", (ev) => {
  pad.setPointerCapture(ev.pointerId);
  pad.classList.add("active");
  ballSpin = 0;
  ballVel = { x: 0, y: 0 };
  ballLast = { x: ev.clientX, y: ev.clientY, t: ev.timeStamp };
});
pad.addEventListener("pointermove", (ev) => {
  if (!ballLast) return;
  const sens = Number($("ball-sens").value);
  const dx = (ev.clientX - ballLast.x) * sens, dy = (ev.clientY - ballLast.y) * sens;
  const dt = Math.max(1, ev.timeStamp - ballLast.t);
  ballSend.x += dx;
  ballSend.y += dy;
  // A velocidade (por ms), suavizada: e a que a bola leva ao soltar.
  ballVel.x = 0.6 * (dx / dt) + 0.4 * ballVel.x;
  ballVel.y = 0.6 * (dy / dt) + 0.4 * ballVel.y;
  ballLast = { x: ev.clientX, y: ev.clientY, t: ev.timeStamp };
});
function padUp(ev) {
  if (!ballLast) return;
  // Parado antes de soltar (mais de 60 ms): sem inercia.
  const still = ev.timeStamp - ballLast.t > 60;
  ballLast = null;
  pad.classList.remove("active");
  if ($("ball-spin").checked && !still) ballSpin = performance.now();
}
pad.addEventListener("pointerup", padUp);
pad.addEventListener("pointercancel", padUp);
pad.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  ballWs({ m: [0, 0], w: ev.deltaY > 0 ? -1 : 1 });
}, { passive: false });
document.querySelectorAll(".ball-buttons button").forEach((button) => {
  const name = button.dataset.button;
  const up = () => {
    if (!button.classList.contains("down")) return;
    button.classList.remove("down");
    ballWs({ b: [name, 0] });
  };
  button.addEventListener("pointerdown", (ev) => {
    button.setPointerCapture(ev.pointerId);
    button.classList.add("down");
    ballWs({ b: [name, 1] });
  });
  button.addEventListener("pointerup", up);
  button.addEventListener("pointercancel", up);
  button.addEventListener("contextmenu", (ev) => ev.preventDefault());
});

// ── Terminal ─────────────────────────────────────────────────────
// O shell do gabinete pelo WebSocket /api/terminal, desenhado pelo xterm.js
// (carregado so quando o terminal abre). Teclas vao como binario; o tamanho,
// como texto {"resize": [colunas, linhas]}.

let term = null, termSocket = null, termFit = null;

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector('script[src="' + src + '"]')) return resolve();
    const s = el("script", { src });
    s.onload = resolve;
    s.onerror = () => reject(new Error(src));
    document.head.append(s);
  });
}

async function openTerminal() {
  $("term-note").textContent = t("term_connecting");
  if (!document.querySelector('link[href="xterm.css"]')) {
    document.head.append(el("link", { rel: "stylesheet", href: "xterm.css" }));
  }
  await loadScript("xterm.js");
  await loadScript("xterm-addon-fit.js");
  const box = $("term");
  box.hidden = false;
  if (!term) {
    term = new window.Terminal({
      cursorBlink: true, fontSize: 14, scrollback: 5000,
      fontFamily: '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace',
      theme: { background: "#191a21", foreground: "#f8f8f2", cursor: "#f8f8f2", selectionBackground: "#44475a",
        black: "#21222c", red: "#ff5555", green: "#50fa7b", yellow: "#f1fa8c", blue: "#bd93f9", magenta: "#ff79c6",
        cyan: "#8be9fd", white: "#f8f8f2", brightBlack: "#6272a4", brightRed: "#ff6e6e", brightGreen: "#69ff94",
        brightYellow: "#ffffa5", brightBlue: "#d6acff", brightMagenta: "#ff92df", brightCyan: "#a4ffff",
        brightWhite: "#ffffff" },
    });
    termFit = new window.FitAddon.FitAddon();
    term.loadAddon(termFit);
    term.open(box);
    term.onData((data) => {
      if (termSocket && termSocket.readyState === 1) termSocket.send(new TextEncoder().encode(data));
    });
    term.onResize(({ cols, rows }) => {
      if (termSocket && termSocket.readyState === 1) termSocket.send(JSON.stringify({ resize: [cols, rows] }));
    });
    new ResizeObserver(() => { if (!box.hidden) termFit.fit(); }).observe(box);
  }
  termFit.fit();
  const scheme = location.protocol === "https:" ? "wss://" : "ws://";
  termSocket = new WebSocket(scheme + location.host + "/api/terminal");
  termSocket.binaryType = "arraybuffer";
  termSocket.onopen = () => {
    $("term-note").textContent = t("term_on");
    $("term-open").hidden = true;
    $("term-close").hidden = false;
    termSocket.send(JSON.stringify({ resize: [term.cols, term.rows] }));
    term.focus();
  };
  termSocket.onmessage = (ev) => term.write(new Uint8Array(ev.data));
  termSocket.onclose = () => {
    $("term-note").textContent = t("term_off");
    $("term-open").hidden = false;
    $("term-close").hidden = true;
    termSocket = null;
  };
}

$("term-open").addEventListener("click", () => openTerminal().catch((e) => { $("term-note").textContent = String(e); }));
$("term-close").addEventListener("click", () => { if (termSocket) termSocket.close(); });

// ── Tela: o screenshot ───────────────────────────────────────────
// O PNG do que esta na tela do gabinete (/api/screenshot): o quadro do jogo
// ou do frontend pela camada OpenGL, o desktop pelo X. Em 4:3 como no tubo,
// ou do tamanho do quadro (um 2560x240 fica largo).

let shotUrl = null, shotBusy = false;
// Com "a cada 10 s" marcado, a foto se refaz sozinha enquanto a pagina
// Frontend ou Status esta aberta e a aba visivel.
setInterval(() => {
  if ($("shot-auto").checked && !shotBusy && document.visibilityState === "visible" &&
      (page === "frontend" || page === "status") && !$("app").hidden) takeShot();
}, 10000);
$("shot-take").addEventListener("click", () => takeShot());
async function takeShot() {
  if (shotBusy) return;
  shotBusy = true;
  $("shot-take").disabled = true;
  $("shot-note").textContent = t("shot_wait");
  try {
    const res = await api("/api/screenshot");
    if (!res.ok) {
      $("shot-note").textContent = (await res.json().catch(() => ({}))).error || res.statusText;
      return;
    }
    const blob = await res.blob();
    if (shotUrl) URL.revokeObjectURL(shotUrl);
    shotUrl = URL.createObjectURL(blob);
    const img = $("shot");
    img.onload = () => {
      const source = res.headers.get("X-Shot-Source") === "x11" ? t("shot_x11") : t("shot_gl");
      $("shot-note").textContent = t("shot_from").replace("%w", img.naturalWidth).replace("%h", img.naturalHeight)
        .replace("%s", source).replace("%t", new Date().toLocaleTimeString(lang === "pt" ? "pt-BR" : "en"));
    };
    img.src = shotUrl;
    img.hidden = false;
    const save = $("shot-save");
    save.href = shotUrl;
    save.download = "fliperos-" + new Date().toISOString().replace(/[:.]/g, "-") + ".png";
    save.hidden = false;
  } catch (e) {
    if (e.message !== "login") $("shot-note").textContent = String(e);
  } finally {
    $("shot-take").disabled = false;
    shotBusy = false;
  }
}
$("shot-tube").addEventListener("change", () => $("shot").classList.toggle("tube", $("shot-tube").checked));

// ── Ao vivo: a tela do gabinete (WebRTC) ─────────────────────────
// O go2rtc do gabinete (config/fliperos-stream) manda o que esta no tubo em
// H.264 (e o som em Opus, se ligado). A oferta vai pelo painel
// (/api/stream/offer); o video chega direto, pela rede local. Sem STUN: as
// duas pontas estao na mesma rede. O som comeca mudo (o navegador so toca
// som depois de um clique). Sair da pagina para a transmissao: o ffmpeg do
// gabinete so roda enquanto alguem assiste.

let live = null, liveStats = null, liveStatus = null, liveObsPath = "";

// O endereco da tela para o OBS, montado pelas escolhas do cartao: quadros,
// formato (4:3 como no tubo ou esticado), som; o tamanho e o que digitar no
// OBS. As escolhas ficam no navegador.
const OBS_OPTS = ["obs-fps", "obs-fit", "obs-size", "obs-sound", "ovl-led", "ovl-text", "ovl-size"];

function obsSaved() {
  try {
    const saved = JSON.parse(localStorage.getItem("fliperos-obs") || "{}");
    for (const id of OBS_OPTS) {
      if (!(id in saved)) continue;
      if ($(id).type === "checkbox") $(id).checked = !!saved[id]; else $(id).value = saved[id];
    }
  } catch (e) { /* sem armazenamento */ }
}

function obsSave() {
  const saved = {};
  for (const id of OBS_OPTS) saved[id] = $(id).type === "checkbox" ? $(id).checked : $(id).value;
  try { localStorage.setItem("fliperos-obs", JSON.stringify(saved)); } catch (e) { /* sem armazenamento */ }
}

function sizeText(value) {
  const [w, h] = value.split("x");
  return t("obs_wh").replace("%w", w).replace("%h", h);
}

function liveObsUrl() {
  $("obs-wh").textContent = sizeText($("obs-size").value);
  if (!liveObsPath) return;
  let url = location.origin + liveObsPath + "&fps=" + $("obs-fps").value;
  if ($("obs-fit").value) url += "&fit=" + $("obs-fit").value;
  if (!$("obs-sound").checked) url += "&muted=1";
  $("live-url").value = url;
  $("live-open").href = url;
}

function liveFact(id, text, cls) {
  const dd = $(id);
  dd.textContent = text;
  dd.className = cls || "";
}

function liveIdle() {
  // O palco sem video: o que falta para assistir, ou o botao grande.
  const s = liveStatus || {};
  const ready = s.installed && s.active;
  $("live-idle").hidden = !!live;
  $("live-play").hidden = !ready;
  $("live-idle-text").textContent = !s.installed ? t("live_not_installed") : !s.active ? t("live_off_note")
    : t("live_ready").replace("%e", s.encoder === "vaapi" ? t("live_hw") : "x264");
  $("live-start").hidden = !!live || !ready;
}

async function loadLive() {
  const res = await api("/api/stream");
  liveStatus = await res.json();
  const s = liveStatus, setup = $("live-setup");
  liveFact("live-service", !s.installed ? t("live_absent") : s.active ? t("live_running") : t("live_stopped"),
    s.installed && s.active ? "on" : "off");
  liveFact("live-encoder", !s.installed ? "-" : s.encoder === "vaapi" ? t("live_enc_hw") : t("live_enc_sw"));
  liveFact("live-audio", s.audio ? t("live_audio_on") : t("live_audio_off"), s.audio ? "on" : "off");
  // A rede da rota padrao: no Wi-Fi a recomendacao do cabo em destaque.
  liveFact("live-net", s.link === "wifi" ? t("live_net_wifi") : s.link === "wired" ? t("live_net_wired") : "-",
    s.link === "wifi" ? "off" : s.link === "wired" ? "on" : "");
  $("live-net-tip").textContent = t(s.link === "wifi" ? "live_net_tip_wifi" : "live_net_tip");
  $("live-net-tip").classList.toggle("warn", s.link === "wifi");
  setup.replaceChildren();
  if (!s.installed) {
    const install = el("button", { type: "button", "data-icon": "⬇" }, t("live_install"));
    install.addEventListener("click", async () => {
      const r = await api("/api/stream/install", { method: "POST", body: "{}" });
      const data = await r.json().catch(() => ({}));
      toast(r.ok ? t("live_installing") : data.error || r.statusText);
    });
    setup.append(install);
  } else {
    // Ligar ou desligar o servico (Setup > System > Services > Live screen).
    const svc = el("button", { type: "button", class: s.active ? "ghost" : "", "data-icon": "🔌" },
      t(s.active ? "live_turn_off" : "live_turn_on"));
    svc.addEventListener("click", async () => {
      if (s.active) liveStop();
      await api("/api/settings", { method: "POST",
        body: JSON.stringify({ key: "service.stream", value: s.active ? "off" : "boot" }) });
      setTimeout(() => loadLive().catch(() => {}), 2500);
    });
    // O som: a copia no loopback do ALSA (Settings > Live screen sound).
    const sound = el("button", { type: "button", class: "ghost", "data-icon": s.audio ? "🔇" : "🔊" },
      t(s.audio ? "live_sound_off" : "live_sound_on"));
    sound.addEventListener("click", async () => {
      sound.disabled = true;
      const r = await api("/api/settings", { method: "POST",
        body: JSON.stringify({ key: "stream_audio", value: s.audio ? "off" : "on" }) });
      if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText);
      loadLive().catch(() => {});
    });
    setup.append(svc, sound);
  }
  // O endereco sempre a vista; sem a tela ao vivo no ar, o aviso do porque.
  const r = await api("/api/overlay");
  liveObsPath = (await r.json()).live;
  liveObsUrl();
  $("live-obs-off").hidden = s.installed && s.active;
  liveIdle();
}

function liveIce(pc) {
  // As candidatas da rede local saem em instantes; sem esperar mais que 2 s.
  if (pc.iceGatheringState === "complete") return Promise.resolve();
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, 2000);
    pc.addEventListener("icegatheringstatechange", () => {
      if (pc.iceGatheringState === "complete") { clearTimeout(timer); resolve(); }
    });
  });
}

async function liveStart() {
  liveStop();
  const video = $("live"), fps = Number($("live-fps").value);
  $("live-note").textContent = t("live_connecting");
  const pc = new RTCPeerConnection({ iceServers: [] });
  live = pc;
  liveIdle();
  $("live-idle-text").textContent = t("live_connecting");
  $("live-idle").hidden = false;
  $("live-play").hidden = true;
  const stream = new MediaStream();
  pc.addTransceiver("video", { direction: "recvonly" });
  pc.addTransceiver("audio", { direction: "recvonly" });
  // Com som desde o comeco (o Assistir e um clique, o navegador deixa); se o
  // navegador recusar mesmo assim, comeca mudo e o botao mostra.
  video.muted = false;
  liveMuteButton();
  pc.ontrack = (ev) => {
    stream.addTrack(ev.track);
    video.srcObject = stream;
    video.play().catch(() => { video.muted = true; liveMuteButton(); video.play().catch(() => {}); });
    if (ev.track.kind === "audio") $("live-sound").hidden = false;
  };
  video.onplaying = () => { if (live === pc) $("live-idle").hidden = true; };
  pc.onconnectionstatechange = () => {
    if (live !== pc) return;
    if (pc.connectionState === "failed" || pc.connectionState === "disconnected") {
      liveStop(true);
      $("live-note").textContent = t("live_lost");
    }
  };
  try {
    await pc.setLocalDescription(await pc.createOffer());
    await liveIce(pc);
    const res = await api("/api/stream/offer", { method: "POST", body: JSON.stringify({ fps, sdp: pc.localDescription.sdp }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    if (live !== pc) return;
    await pc.setRemoteDescription({ type: "answer", sdp: data.sdp });
  } catch (e) {
    if (live === pc) liveStop(true);
    if (e.message !== "login") $("live-note").textContent = String(e.message || e);
    return;
  }
  $("live-stop").hidden = false;
  $("live-full").hidden = false;
  $("live-badge").hidden = false;
  liveStats = setInterval(() => liveShowStats(pc), 1000);
}

// O balao do atraso para o OBS: sem medida, o convite a assistir aqui.
let liveSyncSamples = [], liveSyncPrev = {};
function liveSync(video, audio) {
  const p = $("live-sync-text");
  if (video == null) {
    liveSyncSamples = [];
    delete p.dataset.measured;
    p.textContent = t("sync_idle");
    return;
  }
  p.dataset.measured = "1";
  liveSyncSamples = liveSyncSamples.concat([[video, audio]]).slice(-10);
  const mean = (i) => Math.round(liveSyncSamples.reduce((sum, s) => sum + s[i], 0) / liveSyncSamples.length / 10) * 10;
  p.innerHTML = t("sync_on").replaceAll("%v", String(mean(0))).replaceAll("%a", String(mean(1)));
}

async function liveShowStats(pc) {
  // O que chega: o tamanho, os quadros por segundo e o atraso do buffer.
  if (live !== pc) return;
  let text = "", video = null, audio = null, rtt = 0;
  const fps = Number($("live-fps").value);
  // O atraso do ultimo segundo (a diferenca entre duas leituras): a media da
  // sessao toda carregava o comeco, quando o Chrome ainda acerta a sincronia
  // da imagem com o som.
  const prev = liveSyncPrev.pc === pc ? liveSyncPrev : {};
  const now = { pc };
  const recent = (key, sum, n) => {
    now[key] = [sum, n];
    const [sum0, n0] = prev[key] || [0, 0];
    return n > n0 ? (1000 * (sum - sum0)) / (n - n0) : null;
  };
  const stats = await pc.getStats();
  stats.forEach((s) => {
    if (s.type === "inbound-rtp" && s.kind === "video") {
      const delay = s.jitterBufferEmittedCount ? Math.round((1000 * s.jitterBufferDelay) / s.jitterBufferEmittedCount) : null;
      text = (s.frameWidth ? s.frameWidth + "×" + s.frameHeight + " · " : "") + Math.round(s.framesPerSecond || 0) + " fps"
        + (delay != null ? " · " + t("live_buffer").replace("%n", delay) : "");
      const buffer = recent("vjb", s.jitterBufferDelay || 0, s.jitterBufferEmittedCount || 0);
      const decode = recent("vdec", s.totalDecodeTime || 0, s.framesDecoded || 0);
      if (buffer != null) video = buffer + (decode || 0);
    }
    if (s.type === "inbound-rtp" && s.kind === "audio") {
      audio = recent("ajb", s.jitterBufferDelay || 0, s.jitterBufferEmittedCount || 0);
    }
    if (s.type === "candidate-pair" && s.nominated && s.currentRoundTripTime) rtt = s.currentRoundTripTime * 1000;
  });
  liveSyncPrev = now;
  if (text) $("live-note").textContent = text;
  // O atraso todo: o do navegador (buffer e decodificacao), meia volta da
  // rede e o do gabinete. A imagem: a captura e o x264 sem quadros B, uns 2
  // quadros. O som: o periodo do loopback (1024 amostras a 48 kHz, 21 ms) e o
  // quadro do Opus (10 ms).
  if (video != null) {
    const v = video + rtt / 2 + 2000 / fps;
    liveSync(v, audio != null ? audio + rtt / 2 + 31 : v);
  }
}

function liveStop(keepNote) {
  if (liveStats) clearInterval(liveStats);
  liveStats = null;
  if (live) live.close();
  live = null;
  const video = $("live");
  video.srcObject = null;
  video.muted = true;
  $("live-pixels").hidden = true;
  liveSync(null);
  $("live-sound").hidden = true;
  $("live-sound").dataset.icon = "🔇";
  $("live-sound").textContent = t("live_unmute");
  $("live-stop").hidden = true;
  $("live-full").hidden = true;
  $("live-badge").hidden = true;
  if (!keepNote) $("live-note").textContent = "";
  liveIdle();
}

// Os pixels nitidos: cada quadro do video (640x480) copiado no canvas por
// cima, que a pagina aumenta sem suavizar (o Chrome sempre suaviza o <video>).
(() => {
  const video = $("live"), canvas = $("live-pixels"), ctx = canvas.getContext("2d", { alpha: false });
  const next = () => video.requestVideoFrameCallback ? video.requestVideoFrameCallback(draw) : requestAnimationFrame(draw);
  const draw = () => {
    const w = video.videoWidth, h = video.videoHeight;
    if (w && live) {
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      ctx.drawImage(video, 0, 0, w, h);
      canvas.hidden = false;
    }
    next();
  };
  next();
})();

$("live-start").addEventListener("click", () => liveStart());
$("live-play").addEventListener("click", () => liveStart());
$("live-stop").addEventListener("click", () => liveStop());
$("live-fps").addEventListener("change", () => { if (live) liveStart(); });
obsSaved();
for (const id of ["obs-fps", "obs-fit", "obs-size", "obs-sound"]) {
  $(id).addEventListener("change", () => { obsSave(); liveObsUrl(); });
}
for (const id of ["ovl-led", "ovl-text", "ovl-size"]) {
  $(id).addEventListener("change", () => { obsSave(); overlayUrl(); });
}
$("live-tube").addEventListener("change", () => $("live-stage").classList.toggle("tube", $("live-tube").checked));
// O botao do som mostra o que um clique faz (mudo: "Ligar o som").
function liveMuteButton() {
  const muted = $("live").muted;
  $("live-sound").dataset.icon = muted ? "🔇" : "🔊";
  $("live-sound").textContent = t(muted ? "live_unmute" : "live_mute");
}

$("live-sound").addEventListener("click", () => {
  $("live").muted = !$("live").muted;
  liveMuteButton();
});
$("live-full").addEventListener("click", () => { $("live-stage").requestFullscreen().catch(() => {}); });
$("live-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("live-url").value); } catch (e) {
    $("live-url").select();
    document.execCommand("copy");
  }
  toast(t("copied"));
});

// ── Marquee para o OBS ───────────────────────────────────────────
// Ligado aqui (ou no Setup), o marquee do jogo na tela vira uma pagina
// (/overlay/marquee) para o Browser Source do OBS: fundo transparente, a
// arte do jogo, os recordes, as conquistas e o placar versus. O endereco
// tem uma chave (o OBS nao faz login); uma chave nova invalida a antiga.

async function loadOverlay() {
  const res = await api("/api/overlay");
  showOverlay(await res.json());
}

let ovlData = null;

function showOverlay(data) {
  ovlData = data;
  $("ovl-on").checked = !!data.enabled;
  $("ovl-box").hidden = !data.enabled;
  overlayUrl();
}

// O endereco do marquee com as escolhas (os pontos de LED, os textos); a
// previa segue o mesmo endereco.
function overlayUrl() {
  $("ovl-wh").textContent = sizeText($("ovl-size").value);
  if (!ovlData) return;
  let url = location.origin + ovlData.path;
  if ($("ovl-led").checked) url += "&led=1";
  if (!$("ovl-text").checked) url += "&text=0";
  $("ovl-url").value = url;
  $("ovl-open").href = url;
  const preview = $("ovl-preview");
  if (ovlData.enabled && preview.dataset.src !== url) {
    preview.src = url;
    preview.dataset.src = url;
  } else if (!ovlData.enabled && preview.dataset.src) {
    preview.removeAttribute("src");
    delete preview.dataset.src;
  }
}

$("ovl-on").addEventListener("change", async () => {
  const value = $("ovl-on").checked ? "on" : "off";
  const res = await api("/api/settings", { method: "POST", body: JSON.stringify({ key: "marquee_overlay", value }) });
  if (!res.ok) toast((await res.json().catch(() => ({}))).error || res.statusText);
  loadOverlay().catch(() => {});
});
$("ovl-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("ovl-url").value); toast(t("copied")); } catch (e) {
    $("ovl-url").select();
    document.execCommand("copy");
    toast(t("copied"));
  }
});
$("ovl-new").addEventListener("click", async () => {
  if (!confirm(t("overlay_new_ask"))) return;
  const res = await api("/api/overlay", { method: "POST", body: JSON.stringify({ action: "newkey" }) });
  const data = await res.json();
  showOverlay(data);
  liveObsPath = data.live || liveObsPath;
  liveObsUrl();
});

// ── Arquivos: as pastas do gabinete ──────────────────────────────
// roms, bios, media e splashscreen de ~: entrar nas pastas, baixar,
// enviar (um de cada vez, com o progresso; tambem soltando na lista), criar
// pasta e apagar.

let fileRoot = "roms", filePath = "";

function filesQuery(path) {
  return "root=" + encodeURIComponent(fileRoot) + "&path=" + encodeURIComponent(path);
}
const joinPath = (...parts) => parts.filter(Boolean).join("/");

function stamp(seconds) {
  const d = new Date(seconds * 1000);
  return d.toLocaleDateString(lang === "pt" ? "pt-BR" : "en") + " " +
    d.toLocaleTimeString(lang === "pt" ? "pt-BR" : "en", { hour: "2-digit", minute: "2-digit" });
}

async function loadFiles(path) {
  const res = await api("/api/files?" + filesQuery(path == null ? filePath : path));
  if (!res.ok) { filePath = ""; return; }
  const data = await res.json();
  fileRoot = data.root;
  filePath = data.path;
  const select = $("file-root");
  if (select.options.length !== data.roots.length) {
    select.replaceChildren(...data.roots.map((r) => el("option", { value: r }, "~/" + r)));
  }
  select.value = fileRoot;
  // O caminho: cada pedaco leva de volta a ele.
  const parts = filePath ? filePath.split("/") : [];
  const crumbs = [el("button", { type: "button", "data-icon": "🏠" }, "~/" + fileRoot)];
  crumbs[0].addEventListener("click", () => loadFiles(""));
  parts.forEach((part, i) => {
    const b = el("button", { type: "button" }, part);
    b.addEventListener("click", () => loadFiles(parts.slice(0, i + 1).join("/")));
    crumbs.push(el("span", {}, "/"), b);
  });
  $("crumbs").replaceChildren(...crumbs);

  const table = $("files");
  const head = el("tr", {}, el("th", {}, t("name")), el("th", { class: "num" }, t("size")),
    el("th", { class: "fdate" }, t("modified")), el("th", {}, ""));
  const rows = data.entries.map((e) => {
    const target = joinPath(filePath, e.name);
    let link;
    if (e.dir) {
      link = el("button", { type: "button", title: e.name }, "📁 " + e.name);
      link.addEventListener("click", () => loadFiles(target));
    } else {
      link = el("a", { href: "/api/download?" + filesQuery(target), title: e.name, download: e.name }, "📄 " + e.name);
    }
    const del = el("button", { type: "button", class: "del icon-only", "data-icon": "🗑",
      "aria-label": t("delete") + " " + e.name, title: t("delete") });
    del.addEventListener("click", async () => {
      if (!confirm(t("confirm_delete").replace("%s", e.name))) return;
      const r = await api("/api/delete", { method: "POST", body: JSON.stringify({ root: fileRoot, path: target }) });
      if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText);
      loadFiles();
    });
    // Os arquivos tambem com o botao de baixar (o nome ja baixa).
    const actions = el("td", { class: "fact" });
    if (!e.dir) {
      actions.append(el("a", { href: "/api/download?" + filesQuery(target), download: e.name, class: "dl icon-only",
        "data-icon": "⬇", "aria-label": t("download") + " " + e.name, title: t("download") }));
    }
    actions.append(del);
    return el("tr", {}, el("td", { class: "fname" }, link), el("td", { class: "num" }, e.dir ? "" : bytes(e.size)),
      el("td", { class: "fdate" }, stamp(e.mtime)), actions);
  });
  if (!rows.length) rows.push(el("tr", {}, el("td", { colspan: "4", class: "dim" }, t("empty_folder"))));
  // Dentro de uma pasta, ".." no topo volta para a de cima.
  if (filePath) {
    const up = el("button", { type: "button", title: t("up_folder") }, "📁 ..");
    up.addEventListener("click", () => loadFiles(filePath.split("/").slice(0, -1).join("/")));
    rows.unshift(el("tr", {}, el("td", { class: "fname" }, up), el("td"), el("td", { class: "fdate" }), el("td")));
  }
  table.replaceChildren(el("colgroup", {}, el("col"), el("col", { class: "c-size" }), el("col", { class: "c-date" }),
    el("col", { class: "c-del" })), el("thead", {}, head), el("tbody", {}, ...rows));
}

// sendFile: um arquivo pelo XMLHttpRequest (o fetch nao da o progresso do
// envio). Resolve com o status.
function sendFile(file, overwrite) {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload?" + filesQuery(filePath) + "&name=" + encodeURIComponent(file.name) +
      (overwrite ? "&overwrite=1" : ""));
    xhr.setRequestHeader("X-FliperOS", "1");
    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) {
        $("upload-status").textContent = t("uploading").replace("%s", file.name)
          .replace("%p", Math.round((100 * ev.loaded) / ev.total));
      }
    };
    xhr.onload = () => resolve(xhr.status);
    xhr.onerror = () => resolve(0);
    xhr.send(file);
  });
}

async function uploadFiles(files) {
  let sent = 0;
  for (const file of files) {
    let status = await sendFile(file, false);
    if (status === 409 && confirm(t("exists_overwrite").replace("%s", file.name))) status = await sendFile(file, true);
    if (status === 401) { showLogin(); return; }
    if (status === 200) sent++;
    else if (status !== 409) toast(file.name + ": " + (status || "network error"));
  }
  $("upload-status").textContent = t("uploaded").replace("%n", sent);
  loadFiles();
}

$("file-root").addEventListener("change", () => { fileRoot = $("file-root").value; loadFiles(""); });
$("file-input").addEventListener("change", () => {
  const files = Array.from($("file-input").files);
  $("file-input").value = "";
  if (files.length) uploadFiles(files);
});
$("file-mkdir").addEventListener("click", async () => {
  const name = prompt(t("folder_name"));
  if (!name) return;
  const r = await api("/api/mkdir", { method: "POST", body: JSON.stringify({ root: fileRoot, path: filePath, name }) });
  if (!r.ok) toast((await r.json().catch(() => ({}))).error || r.statusText);
  loadFiles();
});
const drop = $("file-drop");
drop.addEventListener("dragover", (ev) => { ev.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (ev) => {
  ev.preventDefault();
  drop.classList.remove("over");
  const files = Array.from(ev.dataTransfer.files || []);
  if (files.length) uploadFiles(files);
});

// ── ROM filter ───────────────────────────────────────────────────
// O filtro do MAME ROM Cleaner (os parametros, os presets e as opcoes vem do
// Setup: /api/romfilter, fliperos-setup --romfilter). Dois usos: o filtro
// do Downloader (o que ele baixa dos torrents; Save o grava) ou limpar uma
// pasta com um romset (a previa e copiar ou mover para a pasta do emulador,
// como tarefa). Como o painel de azulejos do Setup: cada parametro e um
// azulejo com o valor e um desenho pequeno; o de duas opcoes troca no
// clique, os outros abrem as opcoes num dialogo. O placar conta os jogos e
// o tamanho do que passa, a cada mudanca; so vale a ultima contagem.

const rf = { mode: "downloader", target: "", folder: "", info: null, values: {}, base: {}, preset: "cabinet",
  seq: 0, timer: null, loaded: false, task: null, items: [], dirPath: "" };

// Os grupos dos azulejos (as chaves do Setup; uma nova cai em Outros).
const RF_GROUPS = [
  ["rf_g_games", ["arcade", "status", "clones", "region", "bootlegs", "prototypes", "mature", "chd", "vector"]],
  ["rf_g_play", ["players", "buttons", "controls", "modes"]],
  ["rf_g_screen", ["orientation", "lines"]],
  ["rf_g_kind", ["genres", "decades"]],
  ["rf_g_hardware", ["hardware", "systems"]],
];

function rfParams() {
  return rf.info ? rf.info.params.filter((p) => p.visible) : [];
}

function rfPresetValues(name) {
  const preset = rf.info && rf.info.presets.find((p) => p.value === name);
  return preset ? Object.assign({}, preset.values) : {};
}

async function loadRomFilter(target, keep) {
  const query = "target=" + encodeURIComponent(target || rf.target || "groovymame") +
    (rf.mode === "cleaner" && rf.folder ? "&folder=" + encodeURIComponent(rf.folder) : "");
  const res = await api("/api/romfilter?" + query);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { $("rf-note").textContent = data.error || res.statusText; return; }
  const saved = data.saved;
  // A primeira vez no Downloader: o emulador do filtro salvo.
  if (!rf.loaded && rf.mode === "downloader" && saved && saved.target && saved.target !== (target || "groovymame") &&
      data.targets.some((x) => x.value === saved.target)) {
    rf.loaded = true;
    return loadRomFilter(saved.target);
  }
  rf.info = data;
  rf.target = target || rf.target || "groovymame";
  if (keep) {
    // A pasta mudou, o emulador nao: os valores ficam.
  } else if (rf.mode === "downloader" && saved && saved.target === rf.target) {
    rf.preset = saved.preset || "custom";
    rf.values = {};
    for (const p of data.params) rf.values[p.key] = saved[p.key] != null ? saved[p.key] : "";
    rf.base = Object.assign({}, rf.values);
  } else {
    // O MAME 2010 comeca so com a placa do PlayStation, como no Setup.
    rf.preset = rf.target === "mame2010" ? "psx" : "cabinet";
    rf.values = rfPresetValues(rf.preset);
    rf.base = Object.assign({}, rf.values);
  }
  rf.loaded = true;
  renderRomFilter();
  rfCount();
}

function renderRomFilter() {
  const info = rf.info;
  if (!info) return;
  document.querySelectorAll(".rf-tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.mode === rf.mode)));
  $("rf-source").hidden = rf.mode !== "cleaner";
  $("rf-folder").textContent = rf.folder || t("rf_no_folder");
  $("rf-folder").classList.toggle("empty", !rf.folder);
  $("rf-browse").textContent = rf.folder ? t("rf_change") : t("rf_choose");
  $("rf-target").replaceChildren(...info.targets.map((x) => el("option", { value: x.value }, x.label)));
  $("rf-target").value = rf.target;
  const presets = info.presets.map((p) => el("option", { value: p.value }, p.label));
  presets.push(el("option", { value: "custom" }, t("rf_custom")));
  $("rf-preset").replaceChildren(...presets);
  $("rf-preset").value = rf.preset;
  $("rf-data").textContent = info.data || "-";
  $("rf-dest").textContent = rf.mode === "downloader" ? t("rf_dest_dl") : (info.dest ? info.dest.label : "-");
  $("rf-save").hidden = rf.mode !== "downloader";
  $("rf-scan").hidden = rf.mode !== "cleaner";
  $("rf-scan").disabled = !rf.folder;
  $("rf-note").textContent = rf.mode === "downloader"
    ? (info.saved_label ? t("rf_saved_now").replace("%s", info.saved_label) : t("rf_not_saved")) : "";
  renderBoard();
}

function renderBoard() {
  const byKey = new Map(rfParams().map((p) => [p.key, p]));
  const groups = RF_GROUPS.map(([label, keys]) => [label, keys.filter((k) => byKey.has(k))]);
  const rest = [...byKey.keys()].filter((k) => !RF_GROUPS.some(([, keys]) => keys.includes(k)));
  if (rest.length) groups.push(["rf_g_other", rest]);
  $("rf-board").replaceChildren(...groups.filter(([, keys]) => keys.length).map(([label, keys]) =>
    el("section", { class: "rf-group" }, el("h3", {}, t(label)),
      el("div", { class: "rf-tiles" }, ...keys.map((k) => rfTile(byKey.get(k)))))));
}

// O rotulo curto de uma opcao (sem o parentese: "Low (up to 288 lines...)").
const rfNum = (n) => Number(n).toLocaleString(lang === "pt" ? "pt-BR" : "en");
const rfShort = (o) => o.label.replace(/\s*\(.*\)\s*$/, "");

function rfEmptyText(p) {
  return t(p.key === "controls" ? "rf_s_buttons" : p.key === "hardware" ? "rf_s_any" : "rf_s_all");
}

function rfSummary(p, value) {
  if (p.type === "radio") {
    const o = p.options.find((x) => x.value === value);
    return o ? rfShort(o) : value || "-";
  }
  const set = new Set((value || "").split(","));
  const picked = p.options.filter((o) => set.has(o.value));
  if (!picked.length) return rfEmptyText(p);
  if (picked.length === p.options.length) return t("rf_s_all");
  if (picked.length <= 2) return picked.map(rfShort).join(", ");
  return t("rf_s_n_of").replace("%n", picked.length).replace("%m", p.options.length);
}

function rfVisual(p, value) {
  const opts = p.options.map((o) => o.value);
  if (p.type === "radio" && opts.length > 2 && opts.every((v) => /^\d+$/.test(v))) {
    // Jogadores e botoes: as figuras acesas ate o numero (Any: todas).
    const max = Math.max(...opts.map(Number)), n = Number(value) || max;
    const box = el("span", { class: "rf-pips" + (p.key === "players" ? " people" : ""), "aria-hidden": "true" });
    for (let i = 1; i <= max; i++) box.append(el("i", { class: i <= n ? "on" : "" }));
    return box;
  }
  if (p.key === "status") {
    const n = opts.indexOf(value) + 1, box = el("span", { class: "rf-lamps", "aria-hidden": "true" });
    for (let i = 1; i <= opts.length; i++) box.append(el("i", { class: i <= n ? "on l" + i : "" }));
    return box;
  }
  if (p.type === "radio" && opts.length === 2 && (opts.includes("yes") || opts.includes("no"))) {
    return el("span", { class: "rf-switch" + (value === "yes" ? " on" : ""), "aria-hidden": "true" }, el("i"));
  }
  if (p.type === "check" && opts.length <= 6) {
    const set = new Set((value || "").split(",")), all = !value && p.key !== "controls" && p.key !== "hardware";
    const box = el("span", { class: "rf-blocks " + p.key, "aria-hidden": "true" });
    for (const o of p.options) box.append(el("i", { class: all || set.has(o.value) ? "on" : "" }));
    return box;
  }
  return null;
}

function rfTile(p) {
  const value = rf.values[p.key] || "";
  const toggle = p.type === "radio" && p.options.length === 2;
  const attrs = { type: "button", class: "rf-tile" + ((rf.base[p.key] || "") !== value ? " changed" : ""), title: p.help };
  if (!toggle) attrs["aria-haspopup"] = "dialog";
  // Sem desenho, uma linha a mais: o que esta marcado, ou o que o parametro faz.
  let visual = rfVisual(p, value);
  if (!visual) {
    const set = new Set(value.split(","));
    const picked = p.type === "check" ? p.options.filter((o) => set.has(o.value)).map(rfShort) : [];
    const detail = picked.length && picked.length < p.options.length ? picked.join(", ") : p.help;
    visual = el("span", { class: "rf-tile-detail" }, detail);
  }
  const tile = el("button", attrs, el("span", { class: "rf-tile-title" }, p.title),
    el("span", { class: "rf-tile-value" }, rfSummary(p, value)), visual);
  tile.addEventListener("click", () => {
    if (!toggle) { rfEdit(p); return; }
    rf.values[p.key] = (p.options.find((o) => o.value !== value) || p.options[0]).value;
    rfChanged();
  });
  return tile;
}

function rfChanged() {
  rf.preset = "custom";
  $("rf-preset").value = "custom";
  rfHidePreview();
  renderBoard();
  rfCount();
}

// O dialogo das opcoes: as de uma escolha fecham ao escolher; as de varias
// ficam abertas (o placar conta atras), com busca nas listas longas.
function rfDialog(title, help) {
  $("rf-dlg-title").textContent = title;
  $("rf-dlg-help").textContent = help || "";
  $("rf-dlg-help").hidden = !help;
  return $("rf-dialog");
}

function rfEdit(p) {
  const dlg = rfDialog(p.title, p.help);
  const body = $("rf-dlg-body");
  $("rf-dlg-foot").replaceChildren(el("button", { value: "close" }, t("rf_done")));
  if (p.type === "radio") {
    body.replaceChildren(el("div", { class: "rf-choices", role: "listbox", "aria-label": p.title },
      ...p.options.map((o) => {
        const b = el("button", { type: "button", class: "rf-choice", role: "option",
          "aria-selected": String(o.value === (rf.values[p.key] || "")) }, o.label);
        b.addEventListener("click", () => { rf.values[p.key] = o.value; dlg.close(); rfChanged(); });
        return b;
      })));
  } else {
    const picked = new Set((rf.values[p.key] || "").split(",").filter(Boolean));
    const chips = el("div", { class: "chips" }), hint = el("p", { class: "dim" });
    const note = () => {
      hint.textContent = picked.size ? t("rf_n_marked").replace("%n", picked.size).replace("%m", p.options.length)
        : rfEmptyText(p) + " · " + t("rf_none_means");
    };
    const save = () => {
      rf.values[p.key] = p.options.map((o) => o.value).filter((v) => picked.has(v)).join(",");
      note();
      rfChanged();
    };
    const draw = () => chips.replaceChildren(...p.options.map((o) => {
      const c = el("button", { type: "button", "aria-pressed": String(picked.has(o.value)) }, o.label);
      c.addEventListener("click", () => {
        if (picked.has(o.value)) picked.delete(o.value); else picked.add(o.value);
        c.setAttribute("aria-pressed", String(picked.has(o.value)));
        save();
      });
      return c;
    }));
    const tools = el("div", { class: "chip-tools" });
    if (p.options.length > 12) {
      const search = el("input", { type: "search", placeholder: t("rf_find"), "aria-label": t("rf_find") });
      // Enter no campo nao fecha o dialogo (o form dele e method=dialog).
      search.addEventListener("keydown", (ev) => { if (ev.key === "Enter") ev.preventDefault(); });
      search.addEventListener("input", () => {
        const q = search.value.trim().toLowerCase();
        chips.querySelectorAll("button").forEach((c) => { c.hidden = !!q && !c.textContent.toLowerCase().includes(q); });
      });
      tools.append(search);
    }
    const all = el("button", { type: "button", class: "ghost" }, t("rf_all"));
    const none = el("button", { type: "button", class: "ghost" }, t("rf_none"));
    all.addEventListener("click", () => { p.options.forEach((o) => picked.add(o.value)); draw(); save(); });
    none.addEventListener("click", () => { picked.clear(); draw(); save(); });
    tools.append(all, none);
    draw();
    note();
    body.replaceChildren(tools, chips, hint);
  }
  dlg.showModal();
}

// As pastas, no mesmo dialogo: os lugares de sempre, depois a arvore.
async function rfDirs(path) {
  const dlg = rfDialog(t("rf_folder"), t("rf_folder_help"));
  const body = $("rf-dlg-body"), foot = $("rf-dlg-foot");
  const res = await api("/api/dirs?path=" + encodeURIComponent(path || ""));
  const data = await res.json().catch(() => ({}));
  const cancel = el("button", { value: "close", class: "ghost" }, t("cancel"));
  if (!res.ok) {
    body.replaceChildren(el("p", { class: "error" }, data.error || res.statusText));
    foot.replaceChildren(cancel);
  } else {
    rf.dirPath = data.path;
    const list = el("div", { class: "rf-dirs" });
    const go = (label, to) => {
      const b = el("button", { type: "button", title: to }, label);
      b.addEventListener("click", () => rfDirs(to).catch(() => {}));
      list.append(b);
    };
    if (!data.path) {
      data.places.forEach((place) => go("💾 " + place, place));
      go("📁 /", "/");
    } else {
      go("⬆ ..", data.parent);
      data.dirs.forEach((name) => go("📁 " + name, (data.path === "/" ? "" : data.path) + "/" + name));
      if (!data.dirs.length) list.append(el("p", { class: "dim" }, t("rf_no_subfolders")));
    }
    body.replaceChildren(...(data.path ? [el("p", { class: "rf-path" }, data.path)] : []), list);
    const use = el("button", { type: "button", "data-icon": "✔" }, t("rf_use_this"));
    use.disabled = !data.path;
    use.addEventListener("click", () => {
      rf.folder = data.path;
      dlg.close();
      rfHidePreview();
      rfPickFolder().catch(() => {});
    });
    foot.replaceChildren(cancel, use);
  }
  if (!dlg.open) dlg.showModal();
}

async function rfPickFolder() {
  // O emulador provavel pelo nome da pasta (como no Setup), e o filtro dele.
  await loadRomFilter(rf.target, true);
  const guess = rf.info && rf.info.default_target;
  if (guess && guess !== rf.target) await loadRomFilter(guess);
}

function rfBody(extra) {
  return JSON.stringify(Object.assign({ target: rf.target, folder: rf.mode === "cleaner" ? rf.folder : "",
    values: rf.values }, extra || {}));
}

function rfCount() {
  clearTimeout(rf.timer);
  const score = document.querySelector(".rf-score");
  if (rf.mode === "cleaner" && !rf.folder) {
    score.classList.remove("busy");
    $("rf-games").textContent = "-"; $("rf-size").textContent = "-";
    $("rf-count-note").textContent = t("rf_pick_folder");
    return;
  }
  score.classList.add("busy");
  $("rf-count-note").textContent = t("rf_counting");
  rf.timer = setTimeout(async () => {
    const seq = ++rf.seq;
    const res = await api("/api/romfilter/count", { method: "POST", body: rfBody() }).catch(() => null);
    if (seq !== rf.seq || !res || res.status === 409) return;
    const data = await res.json().catch(() => ({}));
    score.classList.remove("busy");
    if (res.ok) {
      $("rf-games").textContent = data.games != null ? rfNum(data.games) : "-";
      $("rf-size").textContent = data.bytes != null ? bytes(Number(data.bytes)) : "-";
      $("rf-count-note").textContent = rf.mode === "downloader" ? t("rf_from_torrent") : t("rf_from_folder");
    } else {
      $("rf-games").textContent = "-"; $("rf-size").textContent = "-";
      $("rf-count-note").textContent = data.error || res.statusText;
    }
  }, 450);
}

async function rfSave() {
  $("rf-note").textContent = t("rf_saving");
  const res = await api("/api/romfilter/save", { method: "POST", body: rfBody({ preset: rf.preset }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { $("rf-note").textContent = data.error || res.statusText; return; }
  if (rf.info) rf.info.saved_label = data.saved || "";
  rf.base = Object.assign({}, rf.values);
  $("rf-note").textContent = t("rf_saved_now").replace("%s", data.saved || "");
  renderBoard();
  toast(t("rf_saved_toast"));
}

function rfHidePreview() {
  const card = $("rf-preview");
  card.setAttribute("data-off", "");
  card.hidden = true;
}

function rfStat(label, value, bad) {
  return el("div", { class: "rf-stat" + (bad ? " bad" : "") }, el("small", {}, label), el("strong", {}, value));
}

function rfRows(query) {
  const q = (query || "").trim().toLowerCase();
  const rows = rf.items.filter((i) => !q || i.name.toLowerCase().includes(q) || i.title.toLowerCase().includes(q));
  const shown = rows.slice(0, 1500);
  const body = el("tbody", {}, ...shown.map((i) => el("tr", {}, el("td", { title: i.name }, i.name),
    el("td", { title: i.title }, i.title))));
  if (rows.length > shown.length) {
    body.append(el("tr", {}, el("td", { colspan: "2", class: "dim" }, t("first").replace("%n", shown.length))));
  }
  return el("table", {}, body);
}

async function rfScan() {
  const card = $("rf-preview"), box = $("rf-preview-body");
  card.removeAttribute("data-off");
  card.hidden = false;
  box.replaceChildren(el("p", { class: "dim" }, t("rf_reading")));
  card.scrollIntoView({ behavior: "smooth", block: "start" });
  const res = await api("/api/romfilter/scan", { method: "POST", body: rfBody() });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { box.replaceChildren(el("p", { class: "error" }, data.error || res.statusText)); return; }
  const s = data.summary || {};
  rf.items = data.items || [];
  const tooBig = (s.move_bytes || 0) > (s.free_bytes || 0);
  const stats = el("div", { class: "rf-stats" },
    rfStat(t("rf_going"), t("rf_sets_n").replace("%n", rfNum(s.move || 0))),
    rfStat(t("rf_size"), bytes(s.move_bytes || 0)),
    rfStat(t("rf_free"), bytes(s.free_bytes || 0) + (tooBig ? " · " + t("rf_no_space") : ""), tooBig),
    rfStat(t("rf_in_folder"), t("rf_sets_n").replace("%n", rfNum(s.sets || 0))),
    rfStat(t("rf_needed"), String(s.needed || 0)));
  if (s.unknown) stats.append(rfStat(t("rf_unknown"), String(s.unknown)));
  const parts = [stats, el("p", { class: "rf-meta" }, t("rf_to") + " ", el("span", { id: "rf-prev-dest" }, s.dest_label || "-"))];
  if (rf.items.length) {
    const search = el("input", { type: "search", placeholder: t("search"), "aria-label": t("search") });
    const list = el("div", { class: "rf-list" }, rfRows(""));
    search.addEventListener("input", () => list.replaceChildren(rfRows(search.value)));
    parts.push(search, list);
  }
  const actions = el("div", { class: "rf-score-actions" });
  if (s.move > 0) {
    const copy = el("button", { type: "button", "data-icon": "📋" }, t("rf_copy"));
    copy.disabled = tooBig;
    copy.addEventListener("click", () => rfRun("copy"));
    actions.append(copy);
    if (rf.info && rf.info.writable) {
      const move = el("button", { type: "button", class: "ghost", "data-icon": "✂" }, t("rf_move"));
      move.addEventListener("click", () => rfRun("move"));
      actions.append(move);
    }
  } else {
    actions.append(el("span", { class: "dim" }, t("rf_nothing")));
  }
  parts.push(actions, el("div", { id: "rf-run", class: "rf-run", role: "status" }));
  box.replaceChildren(...parts);
}

async function rfRun(transfer) {
  const what = transfer === "move" ? t("rf_confirm_move") : t("rf_confirm_copy");
  if (!confirm(what.replace("%s", rf.folder))) return;
  const res = await api("/api/romfilter/run", { method: "POST", body: rfBody({ transfer }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { toast(data.error || res.statusText); return; }
  rf.task = data.id;
  rfFollow();
}

async function rfFollow() {
  // O andamento da tarefa aqui mesmo (ela tambem aparece em Arquivos > Tarefas).
  const box = $("rf-run");
  if (!rf.task || !box) return;
  const res = await api("/api/task?id=" + rf.task).catch(() => null);
  if (!res || !res.ok) return;
  const task = await res.json();
  const text = task.running ? (task.step || "…") + (task.pct != null ? " · " + task.pct + "%" : "")
    : task.rc === 0 ? "✓ " + (task.last || t("task_ok")) : "✗ " + (task.error || t("task_fail"));
  box.replaceChildren(...(task.running ? [meter(task.pct || 0)] : []),
    el("span", { class: task.running ? "dim" : task.rc === 0 ? "ok" : "error" }, text));
  if (task.running) setTimeout(rfFollow, 1500); else rf.task = null;
}

document.querySelectorAll(".rf-tabs button").forEach((b) => b.addEventListener("click", () => {
  if (rf.mode === b.dataset.mode) return;
  rf.mode = b.dataset.mode;
  rfHidePreview();
  loadRomFilter(rf.target).catch(() => {});
}));
$("rf-target").addEventListener("change", () => { rfHidePreview(); loadRomFilter($("rf-target").value).catch(() => {}); });
$("rf-preset").addEventListener("change", () => {
  const name = $("rf-preset").value;
  if (name === "custom") return;
  rf.preset = name;
  rf.values = rfPresetValues(name);
  rf.base = Object.assign({}, rf.values);
  rfHidePreview();
  renderBoard();
  rfCount();
});
$("rf-browse").addEventListener("click", () => {
  rfDirs(rf.folder ? rf.folder.split("/").slice(0, -1).join("/") || "/" : "").catch(() => {});
});
$("rf-dialog").addEventListener("click", (ev) => { if (ev.target === $("rf-dialog")) $("rf-dialog").close(); });
$("rf-save").addEventListener("click", () => rfSave().catch(() => {}));
$("rf-scan").addEventListener("click", () => rfScan().catch(() => {}));

// ── O laco ───────────────────────────────────────────────────────

let timer = null;
// ── As paginas ───────────────────────────────────────────────────
// Frontend, Ao vivo, Filtro de ROMs, Downloads, Arquivos, Configuracoes, Status
// e Terminal: o endereco (#files)
// escolhe; sem ele, a ultima aberta (lembrada no navegador, quando da).

const PAGES = ["frontend", "live", "romfilter", "downloads", "files", "settings", "status", "terminal"];
let page = "frontend";

function showPage(name) {
  if (!PAGES.includes(name)) name = "frontend";
  page = name;
  // O CSS arruma cada pagina (o Status em seis colunas no desktop).
  document.querySelector("main").dataset.page = name;
  // Um cartao pode estar em mais de uma pagina (data-page="frontend status":
  // o jogo aberto e a tela tambem no topo do Status); data-off, desligado por
  // enquanto (o trackball).
  document.querySelectorAll("main > section[data-page]").forEach((s) => {
    s.hidden = !s.dataset.page.split(" ").includes(name) || s.hasAttribute("data-off");
  });
  document.querySelectorAll(".pages a").forEach((a) => {
    if (a.dataset.page === name) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  try { localStorage.setItem("fliperos-page", name); } catch (e) { /* sem armazenamento */ }
  // O que cada pagina busca ao aparecer.
  if (name === "files") {
    loadFiles().catch(() => {});
    loadTasks().catch(() => {});
  } else if (name === "downloads") {
    loadDownloader().catch(() => {});
    loadTasks().catch(() => {});
  } else if (name === "settings") {
    loadSettings().catch(() => {});
  } else if (name === "romfilter") {
    if (!rf.loaded) loadRomFilter("").catch(() => {});
  } else if (name === "status") {
    loadLogs().catch(() => {});
  } else if (name === "terminal" && termFit) {
    requestAnimationFrame(() => termFit.fit());
  }
  if (name === "frontend" || name === "status") drawFps();
  if (name === "live") {
    loadLive().catch(() => {});
    loadOverlay().catch(() => {});
  } else if (live) {
    // Fora da pagina Ao vivo a transmissao para: o ffmpeg do gabinete so
    // roda enquanto alguem assiste.
    liveStop();
  }
}

window.addEventListener("hashchange", () => showPage(location.hash.slice(1)));

function firstPage() {
  let saved = "";
  try { saved = localStorage.getItem("fliperos-page") || ""; } catch (e) { /* sem armazenamento */ }
  return location.hash.slice(1) || saved || "frontend";
}

let ticks = 0;
async function tick() {
  try {
    const res = await api("/api/status");
    render(await res.json());
    $("offline").hidden = true;
    // Os downloads e as tarefas, a cada 3 s, com a pagina deles aberta.
    if (ticks++ % 3 === 0 && (page === "downloads" || page === "files")) {
      if (page === "downloads") loadDownloader().catch(() => {});
      loadTasks().catch(() => {});
    }
  } catch (e) {
    if (e.message !== "login") $("offline").hidden = false;
  }
}
function start() {
  $("login").hidden = true;
  $("app").hidden = false;
  stop();
  tick();
  loadSystems().catch(() => {});
  loadFiles("").catch(() => {});
  showPage(firstPage());
  timer = setInterval(tick, 1000);
}
function stop() {
  if (timer) clearInterval(timer);
  timer = null;
}

translate();
fetch("/api/me", { credentials: "same-origin" }).then((res) => (res.ok ? start() : showLogin())).catch(showLogin);
