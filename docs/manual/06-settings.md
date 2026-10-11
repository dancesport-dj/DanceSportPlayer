# 6 · Settings

[Manual index](README.md) · previous: [Tags](05-tags.md)

Open **⚙ Settings** from the bottom of the Playing panel. The changes apply
when you click **OK**. Theme, accent colour, language and the audio backend
are read at start: for those the app asks for a restart.

The tabs, in order: **⚙ General**, **📁 Paths**, **🎨 Look**, **🔊 Sound &
player**, **⚗ Analysis**, **🎛 Play sets** and **📦 Venue pack**. The full app
adds **🎵 Checks**, the thresholds of its music check; the player hides it.

## General

The **⚙ General** tab.

| Setting | Does |
|---|---|
| **App mode** | Which side of the app is shown: *Both*, *Planner only* or *Player only*. Switching back brings everything back. The player build has no such row. |
| **📱 Phone remote** | **📱 Start Server** starts the phone remote and opens its window on top of the settings. While it runs, the button reads **📱 Stop Server**. See [chapter 4](04-playing.md#-the-phone-remote). |
| **🎛 Controller** | **🎛 Set up…** opens the window for a USB MIDI or HID controller. See [chapter 4](04-playing.md#-a-hardware-controller). |
| **🐞 Send error reports** | Only in builds that can send them. When the app hits an error, it sends the technical details to the developer: the error, the last log lines, the system and the app version. Never your music or playlists. Off by default. |
| **🔔 Check for new versions** | Once per start, ask GitHub (api.github.com) whether a newer release is out, and announce it once with a link to its download page. The request carries nothing about you or your music; GitHub sees the IP address it comes from. Nothing is downloaded or installed. Off by default; the first start asks. Applies from the next start. |

## Paths

The **📁 Paths** tab.

![Settings, Paths tab](img/settings-paths.png)

The folders are described in
[chapter 1](01-getting-started.md#point-the-app-at-your-music). Among them
sits the **Playlist file format**: *UTF-8 (.m3u)*, *UTF-8 with BOM (.m3u)* or
*UTF-8 (.m3u8)*, see
[chapter 3](03-playlists.md#the-playlist-file-format).

## Look

The **🎨 Look** tab.

![Settings, Look tab](img/settings-look.png)

- **🎨 Theme**: a list of every look, each with a picture of the main window
  in it beside the list.
  - **Standard**: the classic *Light*, the default, and *Dark* for a dim hall.
    They keep the emoji on the buttons and take the accent colour below.
  - **Platform looks**: Windows 11, macOS and Linux GNOME, each light and
    dark. Every look can be picked on every system.
  - **Desk looks**: *Console*, *Carbon*, *Neon* and *Studio*, dark like a
    mixing desk.
  - **Modern looks**: *Graphite*, *Midnight*, *Aurora*, *Paper* and two
    high-contrast looks, picked for readability first.

  A look restyles the buttons, fields, tabs and menus, brings its own font and
  accent colour, and swaps the button emoji for drawn icons. Warnings stay red
  in every theme.
  - **Own looks**: looks you make yourself, kept on this computer.
    **＋ New look…** copies the selected look (*Light* and *Dark* start from
    *Paper* and *Graphite*) and opens the editor: every colour, the corners, the
    button, tab and focus style and the font, with a live preview beside them.
    Text that reads too faintly against its ground is listed as a warning.
    **✎ Edit…** and **🗑 Delete** change or remove an own look, **Export…**
    saves one as a `.json` file and **Import…** adds one someone passed on.
    These buttons save at once. Changing the look the app runs in offers a
    restart when you close the settings with OK.
- **🎚 Accent colour**: the blue of the buttons, sliders and the player panel,
  for *Light* and *Dark*.
  **↺ Default blue** resets it. Colours that mean something, such as red
  warnings, keep their hue.
- **🌐 Language**: English, Deutsch, Español, Nederlands or Русский. Track
  names and anything read from your files stay as they are.
- **Keep the German dance and round names on a screen in another language**:
  *Langsamer Walzer*, *Vorrunde*, *Eintanzen* instead of *Slow Waltz*,
  *Round 1*, *Practice*. The presenter screen and the recorded announcements
  are then German too.

Theme, accent colour and language take effect after a restart.

- **⛶ Fullscreen clock: only the time (20:45:12), no date**: the clock in the
  status bar while the window is in [fullscreen](01-getting-started.md#-fullscreen).
  It changes within a second of saving.

## Sound and player

The **🔊 Sound & player** tab.

| Setting | Does |
|---|---|
| **🔊 Audio backend** | The engine every title is played through. On Windows: *FFmpeg* (the default) or *Windows Media Foundation*. Only change it when a title won't play or a tempo change leaves a gap. Takes effect after a restart. |
| **🔇 Release the sound card between titles** | An onboard sound card puts a hiss on the PA while an app holds it open. This hands the device back after a few seconds of silence. The price is a soft click when the next title starts, so switch it on only if you hear the hiss. |
| **🔕 Mute system sounds while the evening runs** | No error ding or notification chime over the speakers. The system sounds come back when you close the app. |
| **🎧 Preview player** | A mini player (seek, skip, volume) floats over the deck when you click a ▶ in a row. |
| **▶ Player position** | Where the player card stands: *beside the playlists*, at the head of the Playing panel, or *above the playlists*, as one wide strip over the decks. |
| **🎙 Advanced voice controls** | Shows *…with heat* and *🔈 Test* under *Announce next dance*. Hidden, the switch keeps its value. |

## Analysis

The **⚗ Analysis** tab collects every analysis. It only *reads* your files.
Everything is cached, so a second run only does what is new.

![Settings, Analysis tab](img/settings-analysis.png)

The player needs three of them:

- **📊 Analyze loudness (R128)**: for *Equalize volume*.
- **🐂 Analyze PD highlights**: for the Paso Doble stop.
- **🔇 Probe silences**: for skipping silence at the start and end.

**📤 Export / 📥 Import manual PD marks** carries the highlights you marked by
hand to another PC. Run from the full app, the tab lists more analyses; the
player build shows only these.

The hand-set PD marks, the tag edits made in the app and the log of
[played titles](04-playing.md#-played-titles) are the only data no analysis
can find again, so the app backs them up by itself: on the first
start of each day it writes a small file to the `backups` folder next to its
database, brings it up to date when the app closes, and keeps the last seven. **♻ Restore user data backup…** merges one
of them back in; it takes effect after a restart.

**🧱 Build ALL caches…** runs every analysis in turn, for a library you
choose. It can be cancelled.

**🧹 Clean up database…** removes cached rows for files that no longer exist
and compacts the database. It refuses to run when the music drive looks
unmounted, so the analysis can't be wiped by accident.

## Play sets

The **🎛 Play sets** tab sets what the **🏆 Tournament set** and **🎉 Party
set** buttons of the Playing panel apply (see
[chapter 4](04-playing.md#play-sets)).

![Settings, Play sets tab](img/settings-play-sets.png)

For each set:

- **Play length**: pick one, type `m:ss` or seconds, or choose *full*.
- **Fade-out**, in half-second steps.
- **⏭ Auto-advance**, **⏸ No pause between songs**, **🔈 Announce next
  dance**, **🔊 Equalize volume**, **▶️ Double-click starts the title** and
  **🎚 TSO pitch to the heat tempo**.

The tournament set always switches the 🐂 Paso Doble stop off: the detection
is not reliable enough to cut a competition Paso Doble. The party set leaves
it as it is.

**🎚 TSO pitch target** sets, per dance, the tempo the TSO button pitches a
heat to:

- **Middle of the round**: puts the whole round on one tempo, where most of
  its titles already are. No title moves more than one bar per minute.
- **Lower / Middle / Upper**: a fixed tempo within the TSO range. This is
  worth setting for the slow dances, where one bar per minute is a much
  bigger pitch change.

## Venue pack

The **📦 Venue pack** takes the whole desk to another PC in one file: the
settings, every deck and wishlist, and the 🎛 cartwall with its pads and
keys. If you want, the music they use goes in too.

- **📦 Export venue pack…** writes the file. A progress window shows how far
  it is and can cancel it.
- **📥 Import venue pack…** on the other PC loads it. It takes over the
  settings, decks and cartwall at the next start; what it replaces is kept in
  a `before-venue-import` folder next to them. Music in the pack is unpacked
  into a folder you pick, and every deck and pad is pointed at it.

Folder settings, such as the library, playlist and save-as folders, the
presenter screen and the audio backend, stay with each PC.

Next: [Keyboard and mouse](07-shortcuts.md)
