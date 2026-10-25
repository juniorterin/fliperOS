# Controller on the stream

Put your controller on the screen of your live stream. The stick and the buttons light up while you press them on the cabinet, like the input displays of fighting game streams. Viewers see every motion and every button.

It's a page for an OBS **Browser Source**, with a transparent background, so it sits on top of the game. You restyle it in the web panel, in a CSS editor with a live preview. A saved style shows up in OBS at once.

It needs no extra hardware or program: it reads the same controls you set in Setup > Joysticks > Button mapping.

## Put it in OBS

1. Open the web panel (`http://fliperos.local`) and go to **Live**.
2. Scroll to the **Controller for OBS** card and press **Copy** next to the address.
3. In OBS: **Sources > + > Browser**, and paste the address in **URL**.
4. Width and height: **800 × 400** for one player, **1600 × 400** for two.
5. Place it over the game, in a corner or below it, and resize it as you like: everything scales with the source.

The address carries a key, the same as the marquee's and the live screen's, because OBS can't sign in. **New address**, on the Marquee for OBS card (it shows with the marquee page on), makes a new key for all three; then copy the addresses again.

## Options

| In the panel | In the address | What it does |
| --- | --- | --- |
| Players: Player 1 | (nothing) | One panel, player 1 |
| Players: Player 2 | `&players=2` | One panel, player 2 |
| Players: 1 and 2 | `&players=1,2` | Two panels side by side (also `1,2,3` and `1,2,3,4`) |
| Demo in the preview | `&demo=1` | Presses the buttons by itself, with no one at the cabinet |

The demo only changes the preview in the panel. In OBS, leave it out of the address, or the buttons light up on their own.

## What it shows

Each player has:

- the **stick**: a ball that leans to the direction pressed, diagonals too;
- **six buttons**: 1 2 3 on top and 4 5 6 below, the panel order of Button mapping, on the curve of a Vewlix panel;
- **Start** and **Coin**;
- the **P1** / **P2** label.

The buttons follow the Button mapping, not one game's labels: button 1 is the panel's button 1 in every game.

## Change the look (CSS)

The card has a CSS editor next to the preview, with syntax colours. The preview changes at each key you type.

- **Save** writes the CSS to the cabinet, and the pages open in OBS take it at once. No need to refresh the source.
- **Format** lays the CSS out with one property per line. Ctrl+Z undoes it.
- **Factory CSS** goes back to the default style.

The factory CSS is commented part by part, and the best start is to edit it.

### The classes

| Class | What it is |
| --- | --- |
| `.pad` | One player's panel; also `.p1`, `.p2`, and `.active` while something is pressed |
| `.label` | P1, P2... |
| `.stick` | The stick; gets `.up` `.down` `.left` `.right` while pressed, and `data-dir` such as `up-left` |
| `.gate`, `.ball` | The base of the stick and its ball |
| `.buttons` | The six buttons |
| `.button` | Each button: `.b1` to `.b6`, `.start`, `.coin`; `.on` while pressed |
| `.system` | Start and Coin |
| `body.players-2` | Two panels (also `players-3`, `players-4`) |

Sizes use **`--u`**: one panel is 200 × 100 `--u`, and `--u` grows with the OBS source. Write sizes as `calc(var(--u) * 26)` and the style fits any source size.

### Examples

Add these at the end of the CSS and press Save.

Other button colours (here, the Sega Astro City pattern):

```css
:root {
  --b1: #ff5555;
  --b2: #f1fa8c;
  --b3: #8be9fd;
  --b4: #ff5555;
  --b5: #f1fa8c;
  --b6: #8be9fd;
}
```

Unpressed buttons hidden, only the presses show:

```css
.button { opacity: 0; }
.button.on { opacity: 1; }
```

No Start and Coin:

```css
.system { display: none; }
```

A dark box behind each panel:

```css
.pad {
  background: rgba(25, 26, 33, 0.7);
  border-radius: calc(var(--u) * 8);
}
```

The whole panel lights up while anything is pressed:

```css
.pad.active .gate { border-color: #ff79c6; }
```

## If nothing lights up

- **The page says "wrong overlay address"**: the key changed (New address). Copy the address again from the panel.
- **Nothing lights up, or the wrong button does**: check Setup > Joysticks > Button mapping. The page shows exactly what that map says; with no map it uses MAME's default keys for players 1 and 2.
- **A controller plugged in after the page opened**: it's picked up in about 2 seconds; a keyboard encoder too.
- **The page stays blank**: the cabinet is off or out of the network. The page reconnects by itself when it comes back.

## How it works

While at least one controller page is open, the web panel runs one **`fliperos-buttons watch`** at low priority. It reads the Button mapping controls: joysticks through SDL, and a keyboard encoder's keys straight from the input devices, without taking them from the game.

Each change of the pressed controls is one line of JSON, which the panel sends to the pages as Server-Sent Events. A saved CSS goes the same way (`event: css`), so the open pages fetch it again.

When the last page closes, the reader stops. The CSS lives in `/etc/fliperos/input-overlay.css`; without it, the page uses the factory `input.css`.

The page, the events and the CSS are at `/overlay/input`, `/api/overlay/input/events` and `/api/overlay/input/css`, all opened by the address's key. More of the web panel: [Web panel](Web-panel.md).
