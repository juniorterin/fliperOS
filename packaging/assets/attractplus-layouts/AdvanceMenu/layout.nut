//
// Tema "AdvanceMenu" para Attract-Mode Plus.
//
// Reproduz o visual do AdvanceMENU: lista de texto em video invertido na
// selecao, snapshot do jogo ao lado, barra de titulo em cima e linha de status
// embaixo. Sem imagem de fundo nem arte decorativa — e o que se le num CRT de
// 640x240, onde layout feito para 1080p vira borrao.
//
// O AdvanceMENU em si nao e empacotado: o projeto foi abandonado pelo
// GroovyArcade e o caminho KMS dele nao e documentado. O que se queria era a
// aparencia, e ela cabe num tema.
//
// Tudo e posicionado a partir de fe.layout.width/height, que antes de serem
// sobrescritos trazem a resolucao real da tela. Assim o mesmo tema serve os
// tres perfis de monitor (640x240, 512x384 e 640x480).

local flw = fe.layout.width;
local flh = fe.layout.height;

// Pixel de CRT em 640x240 nao e quadrado: a tela continua 4:3, entao cada
// pixel aparece duas vezes mais alto que largo. Para uma caixa parecer 4:3 na
// tela, sua altura em pixels tem de ser largura * (altura/largura) da tela.
// Em 640x480 isso da 0.75 (quadrado normal); em 640x240, 0.375.
local function box_height( width_px )
{
    return ( width_px.tofloat() * flh.tofloat() / flw.tofloat() ).tointeger();
}

local pad     = ( flw / 64 );            // respiro proporcional (10 px em 640)
local bar_h   = ( flh / 10 );            // barra de titulo e de status
local body_y  = bar_h + pad;
local body_h  = flh - ( bar_h * 2 ) - ( pad * 2 );

// Snapshot a direita, com a altura corrigida para o pixel do CRT.
local snap_w  = ( flw * 38 ) / 100;
local snap_h  = box_height( snap_w );
if ( snap_h > body_h ) snap_h = body_h;
local snap_x  = flw - snap_w - pad;

// Lista a esquerda, ocupando o que sobra.
local list_w  = snap_x - ( pad * 2 );

// ── Fundo ───────────────────────────────────────────────────
local bg = fe.add_rectangle( 0, 0, flw, flh );
bg.set_rgb( 8, 10, 18 );

// ── Barra de titulo ─────────────────────────────────────────
local head_bg = fe.add_rectangle( 0, 0, flw, bar_h );
head_bg.set_rgb( 28, 34, 54 );

local head = fe.add_text( "[DisplayName]", pad, 0, flw - ( pad * 2 ), bar_h );
head.set_rgb( 225, 232, 255 );
head.align = Align.Left;
head.style = Style.Bold;

// ── Lista de jogos ──────────────────────────────────────────
local lb = fe.add_listbox( pad, body_y, list_w, body_h );
lb.rows = 11;
lb.charsize = ( body_h / lb.rows ) * 7 / 10;
lb.align = Align.Left;
lb.set_rgb( 190, 198, 215 );
// Selecao em video invertido, como no AdvanceMENU.
// set_sel_bg_rgb e o nome atual; o set_selbg_rgb que os layouts embutidos
// ainda usam esta deprecado desde a 3.2.3, a versao empacotada aqui.
lb.set_sel_bg_rgb( 225, 232, 255 );
lb.set_sel_rgb( 8, 10, 18 );
lb.sel_style = Style.Bold;

// ── Snapshot do jogo selecionado ────────────────────────────
local snap_frame = fe.add_rectangle( snap_x - 1, body_y - 1, snap_w + 2, snap_h + 2 );
snap_frame.set_rgb( 60, 70, 95 );

local snap = fe.add_artwork( "snap", snap_x, body_y, snap_w, snap_h );
// Deixa preencher a caixa: a proporcao ja foi corrigida em box_height(), e
// preservar o aspecto do arquivo desfaria essa correcao no CRT.
snap.preserve_aspect_ratio = false;
snap.trigger = Transition.EndNavigation;

// Abaixo do snapshot, fabricante e ano — o rodape do AdvanceMENU.
local info_y = body_y + snap_h + ( pad / 2 );
if ( info_y + bar_h < flh - bar_h )
{
    local info = fe.add_text( "[Year] [Manufacturer]", snap_x, info_y, snap_w, bar_h );
    info.set_rgb( 140, 150, 175 );
    info.align = Align.Centre;
    info.charsize = lb.charsize * 8 / 10;
}

// ── Linha de status ─────────────────────────────────────────
local foot_y = flh - bar_h;
local foot_bg = fe.add_rectangle( 0, foot_y, flw, bar_h );
foot_bg.set_rgb( 28, 34, 54 );

local foot_left = fe.add_text( "[Title]", pad, foot_y, ( flw / 2 ) - pad, bar_h );
foot_left.set_rgb( 190, 198, 215 );
foot_left.align = Align.Left;

local foot_right = fe.add_text( "[ListEntry]/[ListSize]  [FilterName]",
                                flw / 2, foot_y, ( flw / 2 ) - pad, bar_h );
foot_right.set_rgb( 190, 198, 215 );
foot_right.align = Align.Right;

// Faz os menus internos (sair, filtros) usarem a mesma barra e lista, em vez
// de abrirem com a aparencia padrao por cima do tema.
fe.overlay.set_custom_controls( head, lb );
