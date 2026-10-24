# Cena 1: a instalacao, do pendrive ao disco.

STEPS = [
    (1, "Checking the installation media", []),
    (2, "Checking /dev/sda", ["Samsung SSD 860 EVO, 250 GB, SATA"]),
    (3, "Creating the partition table", ["GPT: BIOS boot, EFI (1 GiB), system"]),
    (5, "Formatting the boot partition", ["mkfs.vfat -F 32 /dev/sda2"]),
    (6, "Formatting the system partition", ["mkfs.ext4 /dev/sda3"]),
    (7, "Mounting the new system", []),
    (8, "Copying system files", ["unsquashfs: 41,327 files"]),
    (81, "Configuring the system", ["Network, sound card, Samba shares"]),
    (82, "Configuring video", ["Arcade 15 kHz, 640x240, VGA-1"]),
    (83, "Configuring the user and the launcher", ["User fliperos, FliperOS frontend"]),
    (84, "Generating the initramfs", ["Kernel 6.18.54-15khz"]),
    (94, "Installing the bootloader", ["Limine: BIOS and UEFI"]),
    (98, "Finishing", []),
    (100, "Installation complete", []),
]


def script(R):
    R.ctx["status"] = "192.168.1.155 - LIVE"
    R.black(0.6)
    R.boot(3.5)
    R.bg("stars")
    R.push(demo.live(), 2.2)
    R.key("enter", 0.4)
    R.push(W.YesNo("Install to HD/SSD", ["Do you want to configure video?"], "yes"), 1.4)
    R.key("enter", 0.3)
    R.replace(demo.monitor(), 1.2)
    R.keys("up down", 0.45)
    R.key("enter", 0.5)
    R.pop()
    R.push(W.Menu("Automatically Partition", [
        ("sda", "Samsung SSD 860 EVO - 250 GB", "/dev/sda - SATA"),
        ("nvme0n1", "WD Blue SN570 - 500 GB", "/dev/nvme0n1 - NVMe"),
        ("return", "Return", "Back to the menu."),
    ], "sda", "Select the HD/SSD for the installation. The whole drive will be used."), 2.0)
    R.key("down", 0.6)
    R.key("up", 0.6)
    R.key("enter", 0.3)
    R.push(W.YesNo("WARNING", ["Warning. All data on the selected drive will be deleted.", "",
                               "Samsung SSD 860 EVO - 250 GB (/dev/sda)"], "no"), 1.5)
    R.key("left", 0.6)
    R.key("enter", 0.3)
    live = W.Live("Installing FliperOS", "Target: Samsung SSD 860 EVO, 250 GB (/dev/sda)", 0,
                  "Starting", "The log is in /var/log/fliperos-setup.log", [])
    R.push(live, 0.6)
    msgs = []
    # A barra sobe por etapa; a copia dos arquivos e a mais longa.
    for i, (pct, step, more) in enumerate(STEPS):
        nxt = STEPS[i + 1][0] if i + 1 < len(STEPS) else pct
        live.step = step
        msgs += more
        live.msgs = msgs[-3:]
        seconds = 6.0 if step == "Copying system files" else 0.9
        frames = int(seconds * 30)
        for f in range(frames):
            live.pct = int(pct + (nxt - pct) * f / frames)
            if step == "Copying system files" and f % 20 == 0:
                live.msgs = (msgs + ["usr/share/fliperos/... %d%%" % live.pct])[-3:]
            R.wait(1 / 30)
    live.pct = 100
    R.wait(0.8)
    R.push(W.YesNo("Installation complete", ["Installation completed successfully.",
                                             "Remove the installation CD/DVD/USB.", "", "Reboot now?"], "yes"), 2.2)
    R.key("enter", 0.3)
    R.replace(W.Message("Rebooting", ["Syncing the drives and rebooting..."], "info", wait=False), 1.4)
    R.black(0.6)
