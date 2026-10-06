# DanceSport Player for Linux

(Deutsch: siehe unten.)

For 64-bit PCs (x86_64). Built on Ubuntu 22.04, so it runs on distributions at
least that new. This build has not been tried on a Linux desktop yet; reports
are welcome.

## Install

1. Unpack the download, in the file manager or in a terminal:

       tar -xzf DanceSport-Player-*-linux.tar.gz

2. Start the app:

       ./DanceSport-Player/DanceSport-Player

Playback works without ffmpeg. Loudness equalizing, silence detection and the
Paso Doble highlights need it:

    sudo apt install ffmpeg        # Ubuntu, Debian, Mint
    sudo dnf install ffmpeg        # Fedora

If the app does not start and says it *could not load the Qt platform plugin
"xcb"*:

    sudo apt install libxcb-cursor0

Settings and playlists are kept in the `DanceSport-Player` folder, or in
`~/.local/share/DanceSport-Planner-Player` where that folder is read-only.
*Keep the screen awake* needs a desktop with a screensaver service: GNOME, KDE,
Xfce, Cinnamon and MATE have one.

---

# DanceSport Player für Linux

Für 64-Bit-PCs (x86_64). Gebaut unter Ubuntu 22.04, läuft also auf
Distributionen, die mindestens so neu sind. Auf einem Linux-Desktop ist dieser
Build noch nicht ausprobiert; Rückmeldungen sind willkommen.

## Installieren

1. Den Download entpacken, im Dateimanager oder im Terminal:

       tar -xzf DanceSport-Player-*-linux.tar.gz

2. Die App starten:

       ./DanceSport-Player/DanceSport-Player

Die Wiedergabe läuft auch ohne ffmpeg. Lautstärke angleichen, Stille-Erkennung
und die Paso-Doble-Highlights brauchen es:

    sudo apt install ffmpeg        # Ubuntu, Debian, Mint
    sudo dnf install ffmpeg        # Fedora

Startet die App nicht und meldet, sie *could not load the Qt platform plugin
"xcb"*:

    sudo apt install libxcb-cursor0

Einstellungen und Playlisten liegen im Ordner `DanceSport-Player`, oder in
`~/.local/share/DanceSport-Planner-Player`, wenn der Ordner schreibgeschützt ist.
*Bildschirm wach halten* braucht einen Desktop mit Bildschirmschoner-Dienst:
GNOME, KDE, Xfce, Cinnamon und MATE haben einen.
