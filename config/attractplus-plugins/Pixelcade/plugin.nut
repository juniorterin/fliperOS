///////////////////////////////////////////////////
//
// Pixelcade plugin do FliperOS: o marquee do Pixelcade mostra o jogo
// selecionado. Quem fala com o pixelweb e o config/fliperos-pixelcade; o
// jogo aberto vai pelo fliperos-kms-run / fliperos-x11-run.
//
///////////////////////////////////////////////////
class UserConfig </ help="Shows the selected game on the Pixelcade marquee (FliperOS)" /> {
	</ label="Command", help="FliperOS Pixelcade helper", order=1 />
	command = "/opt/fliperos/bin/fliperos-pixelcade";
}

class FliperosPixelcade {
	config = null;

	constructor() {
		config = fe.get_config();
		fe.add_transition_callback(this, "on_transition");
	}

	function quote(s) {
		local out = "";
		foreach (c in s)
			if (c != '"') out += c.tochar();
		return "\"" + out + "\"";
	}

	function on_transition(ttype, var, ttime) {
		local offset = 0;
		local rom = "";
		// O protetor de tela e outro layout: o que saiu avisa que ele comecou
		// (o marquee entra no modo attract), e o que volta, que acabou (o
		// helper mostra de novo o jogo que estava selecionado). Dentro dele
		// nada e selecionado.
		if (ScreenSaverActive)
			return false;
		if (ttype == Transition.EndLayout) {
			if (var == FromTo.ScreenSaver)
				fe.plugin_command_bg(config["command"], "screensaver start");
			return false;
		}
		if (ttype == Transition.StartLayout && var == FromTo.ScreenSaver) {
			fe.plugin_command_bg(config["command"], "screensaver stop");
			return false;
		}
		switch (ttype) {
			case Transition.ToNewSelection:
				offset = var;
			case Transition.StartLayout:
			case Transition.ToNewList:
			case Transition.FromGame:
				rom = fe.game_info(Info.Name, offset);
				if (rom != "")
					fe.plugin_command_bg(config["command"],
						"attract " + quote(fe.game_info(Info.Emulator, offset)) + " " + quote(rom));
				break;
		}
		return false;
	}
}

fe.plugin["Pixelcade"] <- FliperosPixelcade();
