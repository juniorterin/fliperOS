//
// Layout "Basic" do Attract-Mode Plus, na versao do FliperOS (o padrao das
// telas novas). O mesmo desenho do Basic que vem com o Attract-Mode: lista a
// esquerda, marquee e snap a direita, titulo em cima e informacoes embaixo.
//
// O original desenha em 640x480 fixos, e o Attract-Mode escala o resultado
// para a tela: em 320x240 ou 640x240 o texto e reamostrado e vira borrao. Este
// desenha na resolucao real (fe.layout.width/height, antes de mudados, sao os
// da tela), com as medidas do original convertidas, e o texto sai pixel a
// pixel. As letras sao um pouco maiores que as do original.
//

local flw = fe.layout.width;
local flh = fe.layout.height;

// Medidas do original (em 640x480) para a tela.
local function X( v ) { return ( v * flw / 640.0 ).tointeger(); }
local function Y( v ) { return ( v * flh / 480.0 ).tointeger(); }

local t = fe.add_artwork( "snap", X( 348 ), Y( 152 ), X( 262 ), Y( 262 ) );
t.trigger = Transition.EndNavigation;

t = fe.add_artwork( "marquee", X( 348 ), Y( 64 ), X( 262 ), Y( 72 ) );
t.trigger = Transition.EndNavigation;

local lb = fe.add_listbox( X( 32 ), Y( 64 ), X( 262 ), Y( 352 ) );
lb.char_size = Y( 22 );
lb.set_sel_bg_rgb( 255, 255, 255 );
lb.set_sel_rgb( 0, 0, 0 );
lb.sel_style = Style.Bold;

// A moldura preta com as janelas da lista, do marquee e do snap.
fe.add_image( "bg.png", 0, 0, flw, flh );

local l = fe.add_text( "[DisplayName]", 0, Y( 12 ), flw, Y( 40 ) );
l.char_size = Y( 30 );
l.set_rgb( 200, 200, 70 );
l.style = Style.Bold;

// Os menus (sair, filtros) usam o titulo e a lista deste layout.
fe.overlay.set_custom_controls( l, lb );

// line( TEXTO, LINHA, ESQUERDA ): as tres linhas de baixo, a esquerda ou a
// direita.
local function line( text, row, left )
{
	local y = Y( 420 + row * 19 );
	local o = left ? fe.add_text( text, X( 30 ), y, X( 330 ), Y( 19 ) )
		: fe.add_text( text, X( 320 ), y, X( 290 ), Y( 19 ) );
	o.char_size = Y( 18 );
	o.set_rgb( 200, 200, 70 );
	o.align = left ? Align.Left : Align.Right;
	return o;
}

line( "[Title]", 0, true );
line( "[Year] [Manufacturer]", 1, true );
line( "[Category]", 2, true );
line( "[ListEntry]/[ListSize]", 0, false );
line( "[FilterName]", 1, false );
