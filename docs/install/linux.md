# DanceSport Player for Linux

(Deutsch: siehe unten.)

Two downloads: `…-linux-x86_64.tar.gz` for 64-bit PCs (Intel, AMD), built on
Ubuntu 22.04, and `…-linux-arm64.tar.gz` for ARM machines (e.g. Asahi Linux on
an Apple Mac), built on Ubuntu 24.04. Each runs on distributions at least that
new. `uname -m` says which one you need: `x86_64` or `aarch64`. These builds
have not been tried on a Linux desktop yet; reports are welcome.

## Install

1. Unpack the download, in the file manager or in a terminal:

       tar -xzf DanceSport-Player-*-linux-*.tar.gz

2. Start the app:

       ./DanceSport-Player/DanceSport-Player

Playback works without ffmpeg. Loudness equalizing, silence detection and the
Paso Doble highlights need it:

    sudo apt install ffmpeg        # Ubuntu, Debian, Mint
    sudo dnf install ffmpeg        # Fedora
    sudo pacman -S ffmpeg          # Arch, Manjaro, Omarchy

If the app does not start and says it *could not load the Qt platform plugin
"xcb"*:

    sudo apt install libxcb-cursor0

Settings and playlists are kept in the `DanceSport-Player` folder, or in
`~/.local/share/DanceSport-Planner-Player` where that folder is read-only.
*Keep the screen awake* needs a desktop with a screensaver service: GNOME, KDE,
Xfce, Cinnamon and MATE have one.

---

# DanceSport Player für Linux

Zwei Downloads: `…-linux-x86_64.tar.gz` für 64-Bit-PCs (Intel, AMD), gebaut
unter Ubuntu 22.04, und `…-linux-arm64.tar.gz` für ARM-Rechner (z. B. Asahi
Linux auf einem Apple-Mac), gebaut unter Ubuntu 24.04. Beide laufen auf
Distributionen, die mindestens so neu sind. `uname -m` sagt, welchen du
brauchst: `x86_64` oder `aarch64`. Auf einem Linux-Desktop sind diese
Builds noch nicht ausprobiert; Rückmeldungen sind willkommen.

## Installieren

1. Den Download entpacken, im Dateimanager oder im Terminal:

       tar -xzf DanceSport-Player-*-linux-*.tar.gz

2. Die App starten:

       ./DanceSport-Player/DanceSport-Player

Die Wiedergabe läuft auch ohne ffmpeg. Lautstärke angleichen, Stille-Erkennung
und die Paso-Doble-Highlights brauchen es:

    sudo apt install ffmpeg        # Ubuntu, Debian, Mint
    sudo dnf install ffmpeg        # Fedora
    sudo pacman -S ffmpeg          # Arch, Manjaro, Omarchy

Startet die App nicht und meldet, sie *could not load the Qt platform plugin
"xcb"*:

    sudo apt install libxcb-cursor0

Einstellungen und Playlisten liegen im Ordner `DanceSport-Player`, oder in
`~/.local/share/DanceSport-Planner-Player`, wenn der Ordner schreibgeschützt ist.
*Bildschirm wach halten* braucht einen Desktop mit Bildschirmschoner-Dienst:
GNOME, KDE, Xfce, Cinnamon und MATE haben einen.
