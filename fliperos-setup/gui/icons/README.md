# Icons

The official icon of each program in Setup > Games > Extras, taken from its
own repository or website and scaled down to 64 px. The Setup's graphical
interface shows `VALUE.png` for the menu item of that value (`theme.py`).
QMamehook has no icon of its own and keeps its initial.

| File | Source |
| --- | --- |
| `wine.png` | Wine, `dlls/user32/resources/oic_winlogo.ico` (256 px frame) |
| `steam.png` | Steam, `store.steampowered.com/favicon.ico` (256 px frame) |
| `heroic.png` | Heroic Games Launcher, `public/icon.png` |
| `pixelcade.png` | Pixelcade, `pixelcade.org/favicon.ico` |
| `zedmd.png` | ZeDMD, `docs/images/ZeDMD_logo_pixelated.png` |
| `doflinx.png` | DOFLinx, the avatar of its GitHub organization |
| `hotr.png` | Hook Of The Reaper, `hotr.6bolt.com/hotrIcon32.ico` |
| `ledspicer.png` | LEDSpicer, the logo of its README |

The emulators and frontends use the icons of the website
(`website/public/icons`, which lists their sources), scaled down the same
way: `attractplus`, `emulationstation`, `pegasus`, `retroarch`, `groovymame`
(also MAME 2010), `fightcade`, `flycast`, `pcsx2`, `pcsx2x6`, `dolphin`, `openbor` and
`model2`.

`metapics/` holds the Arcadeflow theme's metapics (genre, controller and
button icons), used by the FliperOS frontend's game info (`feview.py`).

`pad/` holds the controller drawings of the joypad mapper (Setup > Joysticks >
Button mapping > Joypad, `widgets.PadCapture`): the button, d-pad, stick and
trigger icons of Batocera's EmulationStation (`resources/help/*.svg` of
github.com/batocera-linux/batocera-emulationstation), the same ones its own
"configure a controller" screen shows. Each `.svg` is the original file and
the `.png` next to it is that file rendered at 64 px. They are under the
EmulationStation licence (MIT):

    Copyright (c) 2014 Alec Lofquist

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE SOFTWARE.
