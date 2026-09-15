#!/usr/bin/env python3
"""Read current DRM CRTC timings; never acquire DRM master or set a mode.

Exit: 0 = selected active outputs in range; 1 = out of range; 2 = inconclusive.
This reports kernel state, not an electrical measurement or a boot guarantee.
"""
import argparse
import ctypes as C
import glob
import json
import os
import time
from pathlib import Path

U32, U16, INT = C.c_uint32, C.c_uint16, C.c_int
P32 = C.POINTER(U32)


class Mode(C.Structure):
    _fields_ = [("clock", U32)] + [(n, U16) for n in (
        "hdisplay", "hsync_start", "hsync_end", "htotal", "hskew",
        "vdisplay", "vsync_start", "vsync_end", "vtotal", "vscan")] + [
        ("vrefresh", U32), ("flags", U32), ("type", U32), ("name", C.c_char * 32)]


class Resources(C.Structure):
    _fields_ = [("count_fbs", INT), ("fbs", P32), ("count_crtcs", INT),
                ("crtcs", P32), ("count_connectors", INT), ("connectors", P32),
                ("count_encoders", INT), ("encoders", P32)] + [
                    (n, U32) for n in ("min_width", "max_width", "min_height", "max_height")]


class Connector(C.Structure):
    _fields_ = [(n, U32) for n in ("connector_id", "encoder_id", "connector_type", "connector_type_id")] + [
        ("connection", INT), ("mmWidth", U32), ("mmHeight", U32), ("subpixel", INT),
        ("count_modes", INT), ("modes", C.POINTER(Mode)), ("count_props", INT),
        ("props", P32), ("prop_values", C.POINTER(C.c_uint64)),
        ("count_encoders", INT), ("encoders", P32)]


class Encoder(C.Structure):
    _fields_ = [(n, U32) for n in ("encoder_id", "encoder_type", "crtc_id", "possible_crtcs", "possible_clones")]


class Crtc(C.Structure):
    _fields_ = [(n, U32) for n in ("crtc_id", "buffer_id", "x", "y", "width", "height")] + [
        ("mode_valid", INT), ("mode", Mode), ("gamma_size", INT)]


def timing(clock, htotal, vtotal, flags=0, vscan=0):
    if clock <= 0 or htotal <= 0 or vtotal <= 0:
        raise ValueError("Timing incompleto")
    if flags & ((1 << 12) | (1 << 13)):
        raise ValueError("Clock multiplicado/dividido: requer leitura especifica do driver")
    horizontal = clock / htotal  # DRM clock is kHz, including blanking in htotal.
    refresh = horizontal * 1000 / vtotal
    if flags & 16:  # INTERLACE: report field rate, not frame rate.
        refresh *= 2
    if flags & 32:  # DBLSCAN changes vertical refresh, not HSync frequency.
        refresh /= 2
    if vscan > 1:
        refresh /= vscan
    return {"horizontal_khz": horizontal, "vertical_hz": refresh,
            "interlaced": bool(flags & 16), "doublescan": bool(flags & 32)}


def read_active():
    lib = C.CDLL("libdrm.so.2", use_errno=True)
    for suffix, struct in (("Resources", Resources), ("ConnectorCurrent", Connector),
                           ("Encoder", Encoder), ("Crtc", Crtc)):
        fn = getattr(lib, "drmModeGet" + suffix)
        fn.restype = C.POINTER(struct)
        fn.argtypes = [INT] if suffix == "Resources" else [INT, U32]
        free = getattr(lib, "drmModeFree" + suffix.replace("Current", ""))
        free.argtypes, free.restype = [C.POINTER(struct)], None
    names = ("Unknown", "VGA", "DVI-I", "DVI-D", "DVI-A", "Composite", "SVIDEO",
             "LVDS", "Component", "DIN", "DP", "HDMI-A", "HDMI-B", "TV", "eDP",
             "Virtual", "DSI", "DPI", "Writeback", "SPI", "USB")
    rows, errors = [], []
    for card in sorted(glob.glob("/dev/dri/card[0-9]*")):
        try:
            fd = os.open(card, os.O_RDONLY | os.O_CLOEXEC)
        except OSError as exc:
            errors.append(f"{card}: {exc}")
            continue
        res = None
        try:
            res = lib.drmModeGetResources(fd)
            if not res:
                raise OSError("DRM resources indisponiveis")
            for i in range(res.contents.count_connectors):
                con = lib.drmModeGetConnectorCurrent(fd, res.contents.connectors[i])
                if not con:
                    errors.append(f"{card}: conector ilegivel")
                    continue
                enc, crtc = None, None
                try:
                    co = con.contents
                    kind = names[co.connector_type] if co.connector_type < len(names) else "Unknown"
                    name = f"{kind}-{co.connector_type_id}"
                    row = {"card": card, "connector": name, "active": False}
                    rows.append(row)
                    # A forced analog connector may report disconnected despite an active CRTC.
                    if not co.encoder_id:
                        continue
                    enc = lib.drmModeGetEncoder(fd, co.encoder_id)
                    if not enc:
                        raise OSError("Encoder ilegivel")
                    if not enc.contents.crtc_id:
                        continue
                    crtc = lib.drmModeGetCrtc(fd, enc.contents.crtc_id)
                    if not crtc:
                        raise OSError("CRTC ilegivel")
                    if not crtc.contents.mode_valid:
                        continue
                    dpms = Path("/sys/class/drm") / (Path(card).name + "-" + name) / "dpms"
                    if dpms.exists() and dpms.read_text().strip() != "On":
                        row["reason"] = "DPMS desligado"
                        continue
                    mode = crtc.contents.mode
                    row.update(timing(mode.clock, mode.htotal, mode.vtotal, mode.flags, mode.vscan))
                    row.update(active=True, clock_khz=mode.clock, htotal=mode.htotal,
                               vtotal=mode.vtotal, width=mode.hdisplay, height=mode.vdisplay,
                               crtc=crtc.contents.crtc_id)
                except (OSError, ValueError) as exc:
                    errors.append(f"{card}: {exc}")
                finally:
                    if crtc:
                        lib.drmModeFreeCrtc(crtc)
                    if enc:
                        lib.drmModeFreeEncoder(enc)
                    lib.drmModeFreeConnector(con)
        except OSError as exc:
            errors.append(f"{card}: {exc}")
        finally:
            if res:
                lib.drmModeFreeResources(res)
            os.close(fd)
    return rows, errors


def verdict(rows, errors, connector, minimum, maximum):
    selected = [r for r in rows if (not connector or r["connector"] == connector)]
    active = [r for r in selected if r["active"]]
    if any(not minimum <= r["horizontal_khz"] <= maximum for r in active):
        return "FORA_DA_FAIXA", 1
    if errors or not active or (connector and any(not r["active"] for r in selected)):
        return "INCONCLUSIVO", 2
    return "MODO_ATIVO_15KHZ", 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--connector", help="Ex.: VGA-1; omitido consulta todas as saidas ativas")
    parser.add_argument("--min-khz", type=float, default=15.0)
    parser.add_argument("--max-khz", type=float, default=16.0)
    parser.add_argument("--wait", type=float, default=0, help="Aguardar modo ativo por ate N segundos (maximo 30)")
    args = parser.parse_args()
    if not 0 < args.min_khz <= args.max_khz:
        parser.error("Faixa horizontal invalida")
    if not 0 <= args.wait <= 30:
        parser.error("Espera deve estar entre 0 e 30 segundos")
    deadline = time.monotonic() + args.wait
    while True:
        try:
            rows, errors = read_active()
        except OSError as exc:
            rows, errors = [], [str(exc)]
        status, code = verdict(rows, errors, args.connector, args.min_khz, args.max_khz)
        if code != 2 or time.monotonic() >= deadline:
            break
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    report = {"status": status, "source": "DRM current CRTC (software)",
              "electrically_measured": False, "outputs": rows, "errors": errors}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(status)
        for row in rows:
            if row["active"]:
                print(f'{row["card"]} {row["connector"]}: {row["width"]}x{row["height"]} '
                      f'{row["horizontal_khz"]:.5f} kHz / {row["vertical_hz"]:.3f} Hz '
                      f'{"interlaced" if row["interlaced"] else "progressive"}')
            else:
                print(f'{row["card"]} {row["connector"]}: inativo')
        for error in errors:
            print(error)
        print("Leitura do kernel; nao mede o sinal eletrico nem certifica BIOS/GRUB ou outros momentos.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
