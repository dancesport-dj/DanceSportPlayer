# DanceSport Player for macOS

(Deutsch: siehe unten.)

For Macs with Apple silicon (M1 or newer).

## Install

1. Open the .dmg. Its window shows `DanceSport-Player` and the `Applications`
   folder.
2. Drag `DanceSport-Player` onto `Applications`, then eject the .dmg.
3. Start the app from the Applications folder.

## The first start

The app is not from the App Store and not notarized by Apple, so macOS blocks
the first start and has to be told once that it may open it:

1. macOS says **"DanceSport-Player" Not Opened**. Click **Done**, not *Move to
   Trash*.
2. Open **System Settings > Privacy & Security** and scroll down to
   **Security**. It says *"DanceSport-Player" was blocked to protect your Mac*.
3. Click **Open Anyway** and confirm with your password or Touch ID.
4. Click **Open Anyway** once more in the dialog that follows.

From then on the app starts normally. On macOS 14 or older it is shorter:
Control-click the app in the Applications folder, choose **Open**, then **Open**
again.

If macOS reports the app as **damaged**, remove the download mark in Terminal:

    xattr -dr com.apple.quarantine /Applications/DanceSport-Player.app

When the app asks for access to removable volumes or the Documents folder,
allow it: that is where it reads your music.

## ffmpeg

Playback works without it. Loudness equalizing, silence detection and the Paso
Doble highlights need ffmpeg. Install [Homebrew](https://brew.sh), then:

    brew install ffmpeg

Settings and playlists are kept in
`~/Library/Application Support/DanceSport-Planner-Player`.

---

# DanceSport Player für macOS

Für Macs mit Apple-Chip (M1 oder neuer).

## Installieren

1. Die .dmg öffnen. Im Fenster stehen `DanceSport-Player` und der Ordner
   `Programme` (`Applications`).
2. `DanceSport-Player` auf `Programme` ziehen, danach die .dmg auswerfen.
3. Die App aus dem Programme-Ordner starten.

## Der erste Start

Die App kommt nicht aus dem App Store und ist nicht von Apple beglaubigt.
Deshalb blockiert macOS den ersten Start, und man muss ihn einmal erlauben:

1. macOS meldet **"DanceSport-Player" wurde nicht geöffnet**. Auf **Fertig**
   klicken, nicht auf *In den Papierkorb legen*.
2. **Systemeinstellungen > Datenschutz & Sicherheit** öffnen und nach unten zum
   Abschnitt **Sicherheit** scrollen. Dort steht *"DanceSport-Player" wurde
   blockiert, um deinen Mac zu schützen*.
3. Auf **Trotzdem öffnen** klicken und mit Passwort oder Touch ID bestätigen.
4. Im folgenden Dialog noch einmal **Trotzdem öffnen** klicken.

Danach startet die App ganz normal. Unter macOS 14 oder älter geht es kürzer:
im Programme-Ordner mit gedrückter Ctrl-Taste auf die App klicken, **Öffnen**
wählen, dann noch einmal **Öffnen**.

Meldet macOS die App als **beschädigt**, die Download-Markierung im Terminal
entfernen:

    xattr -dr com.apple.quarantine /Applications/DanceSport-Player.app

Fragt die App nach Zugriff auf Wechseldatenträger oder den Ordner Dokumente,
das erlauben: Dort liest sie die Musik.

## ffmpeg

Die Wiedergabe läuft auch ohne. Lautstärke angleichen, Stille-Erkennung und die
Paso-Doble-Highlights brauchen ffmpeg. [Homebrew](https://brew.sh) installieren,
dann:

    brew install ffmpeg

Einstellungen und Playlisten liegen in
`~/Library/Application Support/DanceSport-Planner-Player`.
