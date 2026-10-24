"""Tests for planner.config: build_flavor() (dev / lite / full detection via the
build_flavor.txt marker), the writable data dir, and write_json_atomic."""
import importlib.metadata
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner import config


class BuildFlavorTest(unittest.TestCase):
    """build_flavor() reads the marker only when frozen; source runs are 'dev'.

    The marker is a SHIPPED file, so it is read from INSTALL_DIR — the data dir
    may have moved out from under it (see DataDirTest) — and from the bundle
    folder (sys._MEIPASS), which is where PyInstaller actually puts shipped
    data: `_internal`, not next to the .exe."""

    def setUp(self):
        self._base = config.INSTALL_DIR
        self._tmp = Path(tempfile.mkdtemp(prefix="dp_flavor_"))
        self._bundle = Path(tempfile.mkdtemp(prefix="dp_flavor_internal_"))
        config.INSTALL_DIR = self._tmp

    def tearDown(self):
        config.INSTALL_DIR = self._base
        for attr in ("frozen", "_MEIPASS"):
            if hasattr(sys, attr):
                delattr(sys, attr)

    def _freeze(self, marker=None, bundled=None):
        """Freeze the app, with a marker beside the .exe and/or in the bundle."""
        sys.frozen = True
        if marker is not None:
            (self._tmp / "build_flavor.txt").write_text(marker, encoding="utf-8")
        if bundled is not None:
            sys._MEIPASS = str(self._bundle)
            (self._bundle / "build_flavor.txt").write_text(bundled, encoding="utf-8")

    def test_source_run_is_dev(self):
        self.assertEqual(config.build_flavor(), "dev")

    def test_frozen_reads_marker(self):
        self._freeze("full")
        self.assertEqual(config.build_flavor(), "full")

    def test_marker_is_normalized(self):
        self._freeze("  LITE \n")
        self.assertEqual(config.build_flavor(), "lite")

    def test_missing_marker_defaults_to_lite(self):
        self._freeze()
        self.assertEqual(config.build_flavor(), "lite")

    def test_junk_marker_defaults_to_lite(self):
        self._freeze("banana")
        self.assertEqual(config.build_flavor(), "lite")

    def test_the_marker_is_found_where_pyinstaller_puts_it(self):
        """The real layout of a build: the marker is data, so it lands in
        `_internal`. Reading only beside the .exe found nothing and answered
        'lite' — for a full build, the wrong answer with no error to show."""
        self._freeze(bundled="full")
        self.assertEqual(config.build_flavor(), "full")

    def test_frozen_reads_the_player_marker(self):
        """The third flavor: no librosa stack, planning UI locked away."""
        self._freeze("player")
        self.assertEqual(config.build_flavor(), "player")
        self.assertTrue(config.player_build())

    def test_only_the_player_marker_is_a_player_build(self):
        self.assertFalse(config.player_build())      # source run = dev
        for marker in ("lite", "full"):
            with self.subTest(marker=marker):
                self._freeze(marker)
                self.assertFalse(config.player_build())

    def test_a_marker_beside_the_exe_wins_over_the_bundled_one(self):
        """Hand-placed beats shipped: it is how a build gets re-labelled without
        being rebuilt, and the bundle is replaced wholesale by the next one."""
        self._freeze("lite", bundled="full")
        self.assertEqual(config.build_flavor(), "lite")


class SpecLanguagesTest(unittest.TestCase):
    """Every language ⚙ Settings offers is packaged. planner.i18n loads a
    catalog by name (importlib), which PyInstaller cannot see — so a module
    the spec does not name is missing from every .exe, and the app says
    "No catalog for de, staying English" on a machine set to German."""

    def test_every_offered_language_is_named_in_the_spec(self):
        from planner.i18n import DEFAULT_LANGUAGE, LANGUAGES
        spec = (Path(config.__file__).resolve().parent.parent
                / "dancesport.spec").read_text(encoding="utf-8")
        for code, _caption, _blurb in LANGUAGES:
            if code == DEFAULT_LANGUAGE:
                continue
            with self.subTest(language=code):
                self.assertTrue(f'"planner.i18n.lang_{code}"' in spec,
                                f"planner.i18n.lang_{code} is not in dancesport.spec")


class SpecWeddingMarksTest(unittest.TestCase):
    """S5: assets/hochzeit holds a couple's names. It stays out of git, but a
    build on the machine that has it bundled it into every installer, so it
    goes in only when DANCESPORT_WEDDING_MARKS=1 asks for it."""

    def test_the_wedding_marks_need_the_flag(self):
        spec = (Path(config.__file__).resolve().parent.parent
                / "dancesport.spec").read_text(encoding="utf-8")
        self.assertTrue('WEDDING_MARKS = os.environ.get("DANCESPORT_WEDDING_MARKS", "")'
                        '.strip() == "1"' in spec, "no DANCESPORT_WEDDING_MARKS flag")
        bundling = re.search(r"\n(.*)\n\s+datas \+= \[\(os\.path\.join\(_marks", spec)
        self.assertIsNotNone(bundling)
        self.assertIn("WEDDING_MARKS and", bundling.group(1))


class BuildNamesTest(unittest.TestCase):
    """The spec names the build; the scripts then copy ffmpeg into it
    (build_exe.bat) and sign it (build_app.sh) by that same name. A script
    left on an old name signs or fills a folder that is not there."""

    NAMES = ("DanceSport-Planner-Player", "DanceSport-Planner-Player-Full",
             "DanceSport-Player")

    def _read(self, name):
        root = Path(config.__file__).resolve().parent.parent
        return (root / name).read_text(encoding="utf-8")

    def test_spec_and_scripts_build_under_the_same_names(self):
        for file in ("dancesport.spec", "build_exe.bat", "build_app.sh",
                     "build_linux.sh"):
            text = self._read(file)
            for name in self.NAMES:
                with self.subTest(file=file, name=name):
                    self.assertIn(name, text)

    def test_nothing_is_built_under_the_old_name(self):
        for file in ("dancesport.spec", "build_exe.bat", "build_app.sh",
                     "build_linux.sh"):
            with self.subTest(file=file):
                self.assertNotIn("DancePlaylist", self._read(file))


class InstallerTest(unittest.TestCase):
    """The Windows setup (installer/dancesport.iss): one app per flavor, and
    it never ships or deletes the data the app keeps beside the .exe."""

    def setUp(self):
        root = Path(config.__file__).resolve().parent.parent
        self.iss = (root / "installer" / "dancesport.iss").read_text(encoding="utf-8")
        self.bat = (root / "build_installer.bat").read_text(encoding="utf-8")

    def test_every_flavor_is_its_own_app(self):
        for name in BuildNamesTest.NAMES:
            with self.subTest(name=name):
                self.assertIn(f'#define AppName "{name}"', self.iss)
                self.assertIn(name, self.bat)
        guids = re.findall(r'#define AppGuid "([0-9A-F-]{36})"', self.iss)
        self.assertEqual(len(set(guids)), len(BuildNamesTest.NAMES))

    def test_an_old_build_is_built_again_first(self):
        # Marcel: "seems the created installer installs an old version?" - the
        # setup wrapped a dist folder from weeks before under today's version.
        root = Path(config.__file__).resolve().parent.parent
        exe_bat = (root / "build_exe.bat").read_text(encoding="utf-8")
        self.assertIn("git rev-parse HEAD", exe_bat)
        self.assertIn("build_commit.txt", exe_bat)
        self.assertIn("git rev-parse HEAD", self.bat)
        self.assertIn("build_commit.txt", self.bat)
        self.assertIn('call "%~dp0build_exe.bat"', self.bat)

    def test_the_build_folder_is_never_shipped_whole(self):
        # A folder the app was started from holds that user's database.
        self.assertNotIn('Source: "{#Source}\\*"', self.iss)
        self.assertIn('Source: "{#Source}\\_internal\\*"', self.iss)

    def test_an_update_deletes_only_the_bundled_runtime(self):
        deletes = re.findall(r'^Type: \w+; Name: "([^"]+)"', self.iss, re.M)
        self.assertEqual(deletes, ["{app}\\_internal"])
        self.assertNotIn("[UninstallDelete]", self.iss)

    def test_the_folder_is_the_users_pick(self):
        self.assertIn("DisableDirPage=no", self.iss)
        self.assertIn("PrivilegesRequired=admin", self.iss)
        self.assertIn("PrivilegesRequiredOverridesAllowed=dialog", self.iss)

    def test_the_first_start_is_not_elevated(self):
        # Marcel: "why is the default folder for installer not programm files?"
        # Started as admin, the app finds C:\Program Files writable and keeps
        # its data there instead of in the user's folder.
        run = re.search(r"^\[Run\]\s*\n(.*)$", self.iss, re.M).group(1)
        self.assertIn("runasoriginaluser", run)


class DmgTest(unittest.TestCase):
    """Marcel: "the .app has no drag to programm folder to install it". The
    .dmg is the bare .app unless the script puts a link to /Applications next
    to it, which is what Finder shows as the place to drag the app to."""

    def setUp(self):
        root = Path(config.__file__).resolve().parent.parent
        self.script = (root / "build_app.sh").read_text(encoding="utf-8")

    def test_the_dmg_holds_a_link_to_the_applications_folder(self):
        self.assertIn('ln -s /Applications "$STAGE/Applications"', self.script)

    def test_the_dmg_is_made_from_the_folder_with_the_link(self):
        self.assertIn('-srcfolder "$STAGE"', self.script)
        self.assertNotIn('-srcfolder "$APP"', self.script)

    def test_the_window_shows_the_hint_with_the_icons_on_it(self):
        # Marcel: "können wir einen kurzen hinweis auf das freigeben bei mac
        # auch direkt im dmg fenster anzeigen?"
        self.assertIn('"$PY" -m tools.assets.dmg_background', self.script)
        self.assertIn('create-dmg "$@" "dist/$APP_NAME.dmg" "$STAGE"', self.script)
        for icon in ('"$APP_NAME.app" "$APP_X" "$APP_Y"',
                     'Applications "$APPLICATIONS_X" "$APPLICATIONS_Y"',
                     'README.txt "$README_X" "$README_Y"'):
            with self.subTest(icon=icon):
                self.assertIn(f"--icon {icon}", self.script)


class LinuxPackTest(unittest.TestCase):
    """build_linux.sh, which CI runs as well. The build is started once in
    CI, and a start writes its settings and logs next to the executable."""

    ROOT = Path(config.__file__).resolve().parent.parent

    def setUp(self):
        self.script = (self.ROOT / "build_linux.sh").read_text(encoding="utf-8")
        flow = (self.ROOT / ".github" / "workflows"
                / "build-player.yml").read_text(encoding="utf-8")
        self.job = flow[flow.index("\n  linux:"):flow.index("\n  release:")]

    def test_ci_builds_through_the_script(self):
        # Marcel: "add a linux script for building". One way to build, so CI
        # and a desk build cannot drift apart.
        self.assertIn("./build_linux.sh player tar", self.job)
        self.assertNotIn("dancesport.spec", self.job)

    def test_the_script_is_executable(self):
        import subprocess
        mode = subprocess.run(["git", "ls-files", "-s", "build_linux.sh"],
                              cwd=self.ROOT, capture_output=True, text=True,
                              check=True).stdout.split()[:1]
        self.assertEqual(mode, ["100755"])

    def test_the_tar_carries_the_install_guide(self):
        self.assertIn('cp docs/install/linux.md "dist/$APP_NAME/README.txt"',
                      self.script)
        self.assertIn('tar -czf "dist/$APP_NAME-linux-$ARCH.tar.gz" -C dist "$APP_NAME"',
                      self.script)

    def test_the_tar_names_its_architecture(self):
        # Marcel's Omarchy machine is ARM: box64 ran the x86_64 build and died
        # on sqlite. The name says which machine a download is for, in the
        # word the release uses (arm64, not uname's aarch64).
        self.assertIn('ARCH=$(uname -m)', self.script)
        self.assertIn('[ "$ARCH" = aarch64 ] && ARCH=arm64', self.script)

    def test_ci_builds_x86_64_and_arm64(self):
        # PySide6's aarch64 wheels need glibc 2.39, so ARM builds on 24.04;
        # x86_64 stays on 22.04 for the older glibc.
        self.assertIn("- arch: x86_64\n            runner: ubuntu-22.04", self.job)
        self.assertIn("- arch: arm64\n            runner: ubuntu-24.04-arm", self.job)
        self.assertIn("runs-on: ${{ matrix.runner }}", self.job)
        self.assertIn("path: dist/DanceSport-Player-linux-${{ matrix.arch }}.tar.gz",
                      self.job)

    def test_the_tar_is_packed_before_the_test_start(self):
        # The v1.0.1 tar.gz shipped the CI run's gui_settings.json,
        # session.log and crash.log.
        self.assertLess(self.job.index("./build_linux.sh"),
                        self.job.index("timeout 20"))


class ManualPackTest(unittest.TestCase):
    """The manual as a PDF, English and German: in the bundle for the ❔ menu,
    and beside README.txt in every player download. CI prints both once and
    hands them to the build jobs, which only copy them."""

    ROOT = Path(config.__file__).resolve().parent.parent

    def _read(self, name):
        return (self.ROOT / name).read_text(encoding="utf-8")

    def setUp(self):
        flow = self._read(".github/workflows/build-player.yml")
        self.flow = flow
        self.manualJob = flow[flow.index("\n  manual:"):flow.index("\n  windows:")]

    def test_the_bundle_carries_both_languages(self):
        spec = self._read("dancesport.spec")
        self.assertIn('os.path.join("docs", "manual", "de")', spec)
        self.assertIn('os.path.join("docs", "manual")', spec)

    def test_every_download_carries_both_pdfs(self):
        bat = self._read("build_exe.bat")
        self.assertIn(r'"%~dp0docs\manual\manual.pdf" "%~dp0dist\%APP_NAME%\Manual.pdf"', bat)
        self.assertIn(r'"%~dp0docs\manual\de\manual.pdf" "%~dp0dist\%APP_NAME%\Handbuch.pdf"', bat)
        linux = self._read("build_linux.sh")
        self.assertIn('cp docs/manual/manual.pdf "dist/$APP_NAME/Manual.pdf"', linux)
        self.assertIn('cp docs/manual/de/manual.pdf "dist/$APP_NAME/Handbuch.pdf"', linux)
        mac = self._read("build_app.sh")
        self.assertIn('cp docs/manual/manual.pdf "$STAGE/Manual.pdf"', mac)
        self.assertIn('cp docs/manual/de/manual.pdf "$STAGE/Handbuch.pdf"', mac)
        for icon in ('Manual.pdf "$MANUAL_X" "$MANUAL_Y"',
                     'Handbuch.pdf "$HANDBUCH_X" "$HANDBUCH_Y"'):
            with self.subTest(icon=icon):
                self.assertIn(f"--icon {icon}", mac)

    def test_the_dmg_icons_below_the_hint_do_not_overlap(self):
        from tools.assets import dmg_background as bg
        row = sorted(bg.LAYOUT[k][0] for k in ("readme", "manual", "handbuch"))
        self.assertEqual(len({bg.LAYOUT[k][1] for k in ("readme", "manual", "handbuch")}), 1)
        for a, b in zip(row, row[1:], strict=False):
            self.assertGreaterEqual(b - a, bg.LAYOUT["icon_size"] + 40)
        self.assertGreaterEqual(row[0] - bg.LAYOUT["icon_size"] / 2, 0)
        self.assertLessEqual(row[-1] + bg.LAYOUT["icon_size"] / 2, bg.LAYOUT["window"][0])

    def test_ci_prints_both_once_with_the_release_version(self):
        self.assertIn("python3 -m tools.docs.build_manual_pdf", self.manualJob)
        self.assertIn("DANCEPLAYLIST_VERSION:", self.manualJob)
        self.assertIn("docs/manual/manual.pdf", self.manualJob)
        self.assertIn("docs/manual/de/manual.pdf", self.manualJob)
        # No Python setup of its own: the runner's python3 runs the tool.
        self.assertNotIn("setup-python", self.manualJob)

    def test_every_build_job_gets_the_printed_pdfs(self):
        for job in ("windows", "macos", "linux"):
            body = self.flow[self.flow.index(f"\n  {job}:"):]
            body = body[:body.index("upload-artifact")]
            with self.subTest(job=job):
                self.assertIn("needs: manual", body)
                self.assertIn("name: manual-pdf", body)
                self.assertIn("Handbuch.pdf", body)


def _pins(name):
    """{package: version} of a requirements file's `pkg==version` lines."""
    path = Path(config.__file__).resolve().parent.parent / name
    pins = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "==" in line and not line.lstrip().startswith("#"):
            pkg, version = line.split("==")
            pins[pkg.strip().lower()] = version.strip()
    return pins


_LOCK_LINE = re.compile(r"^([A-Za-z0-9._-]+)==([^\s;\\]+)")


def _locked(name):
    """{package: version} of a lock file's top-level `pkg==version` entries."""
    path = Path(config.__file__).resolve().parent.parent / name
    pins = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _LOCK_LINE.match(line)
        if m:
            pins[m.group(1).lower().replace("_", "-")] = m.group(2)
    return pins


class LockFileTest(unittest.TestCase):
    """H3: builds and CI install from the hash-locked files, so a tag built
    weeks later bundles what was tested. A pin moved in a requirements file
    without regenerating its lock would silently not take effect there."""

    ROOT = Path(config.__file__).resolve().parent.parent
    LOCKS = {"requirements.lock": ("requirements.txt", "requirements-build.txt"),
             "requirements-player.lock": ("requirements-player.txt",
                                          "requirements-build.txt"),
             # The tester build's FULL stack. requirements-full.txt pulls in
             # requirements.txt itself (`-r`), and the lock pins the whole set.
             "requirements-full.lock": ("requirements-full.txt",
                                        "requirements-build.txt")}

    def test_each_lock_pins_its_sources_at_their_versions(self):
        for lock, sources in self.LOCKS.items():
            locked = _locked(lock)
            for source in sources:
                for pkg, version in _pins(source).items():
                    with self.subTest(lock=lock, pkg=pkg):
                        self.assertEqual(locked.get(pkg), version)

    def test_every_locked_package_carries_a_hash(self):
        for lock in self.LOCKS:
            text = (self.ROOT / lock).read_text(encoding="utf-8")
            entries = re.split(r"\n(?=[A-Za-z0-9])", text.split("\n\n", 1)[1])
            with self.subTest(lock=lock):
                self.assertGreater(len(entries), 10)
                for entry in entries:
                    self.assertIn("--hash=sha256:", entry, entry.splitlines()[0])

    def test_ci_installs_from_the_locks(self):
        workflows = self.ROOT / ".github" / "workflows"
        player = (workflows / "build-player.yml").read_text(encoding="utf-8")
        self.assertEqual(player.count("pip install -r requirements-player.lock"), 3)
        self.assertNotIn("requirements-player.txt", player)
        tests = (workflows / "tests.yml").read_text(encoding="utf-8")
        self.assertIn("pip install -r requirements.lock", tests)
        self.assertNotIn("-r requirements.txt", tests)


class TesterBuildTest(unittest.TestCase):
    """The FULL flavor for testers, delivered as an unpublished draft release.

    Two things here are easy to undo by accident and expensive to get wrong:
    installing the wrong lock (which silently builds the lite binary under the
    FULL name) and publishing the release (which would put a tester build on
    the public releases page)."""

    ROOT = Path(config.__file__).resolve().parent.parent

    def setUp(self):
        self.flow = (self.ROOT / ".github" / "workflows" / "build-tester.yml").read_text(
            encoding="utf-8")

    def _job(self, name):
        """One job's text: from its key up to the next top-level job key."""
        start = self.flow.index(f"\n  {name}:")
        rest = self.flow[start + 1:]
        cut = len(rest)
        for job in ("manual", "windows", "macos", "draft"):
            marker = f"\n  {job}:"
            if marker in rest:
                cut = min(cut, rest.index(marker))
        return rest[:cut]

    def test_only_started_by_hand(self):
        # A tag must never produce a tester build: the public release stays
        # exactly as it was.
        self.assertIn("workflow_dispatch:", self.flow)
        self.assertNotIn("push:", self.flow)
        self.assertNotIn("tags:", self.flow)

    def test_the_release_is_a_draft(self):
        draft = self._job("draft")
        self.assertIn("--draft", draft)
        # Built for the commit of this run: a draft has no tag, so without
        # --target its "source code" links would not be the binaries' source.
        self.assertIn('--target "$GITHUB_SHA"', draft)

    def test_it_does_not_link_a_nonexistent_tag_page(self):
        # A draft lives at untagged-<hash>, not at /releases/tag/<name>; a
        # constructed tag URL would 404 for every tester it was sent to. Only
        # the commands matter - a comment may name the wrong URL to explain it.
        draft = self._job("draft")
        self.assertIn("gh release view", draft)
        for line in draft.splitlines():
            if "/releases/tag/" in line:
                self.assertTrue(line.lstrip().startswith("#"), line)

    def test_both_builds_install_the_full_lock(self):
        for job in ("windows", "macos"):
            with self.subTest(job=job):
                body = self._job(job)
                self.assertIn("pip install -r requirements-full.lock", body)
                self.assertNotIn("pip install -r requirements.lock", body)

    def test_both_builds_build_the_full_flavor(self):
        self.assertIn(r".\build_exe.bat full", self._job("windows"))
        self.assertIn("./build_app.sh full dmg", self._job("macos"))


class TesterRequirementsGuardTest(unittest.TestCase):
    """A FULL venv without torch still "builds full" - PyInstaller just emits
    the lite binary under the FULL name. Every build script has to refuse it."""

    ROOT = Path(config.__file__).resolve().parent.parent

    def test_the_windows_script_refuses_a_full_venv_without_torch(self):
        bat = (self.ROOT / "build_exe.bat").read_text(encoding="utf-8")
        self.assertIn("import torch, demucs, transformers", bat)
        self.assertIn(":no_full_deps", bat)
        self.assertIn("if /I \"%~1\"==\"full\" set LOCK=requirements-full.lock", bat)

    def test_the_shell_scripts_refuse_a_full_venv_without_torch(self):
        for name in ("build_app.sh", "build_linux.sh"):
            with self.subTest(script=name):
                text = (self.ROOT / name).read_text(encoding="utf-8")
                self.assertIn('mods += ["torch", "demucs", "transformers"]', text)
                self.assertIn('else "requirements-full.lock" if flavor == "full"', text)


class CiPinningTest(unittest.TestCase):
    """S10: what the release job runs with `contents: write` is fixed. A
    tag like @v7 moves to whatever its owner pushes next, and a download
    without a hash is whatever the server sends."""

    ROOT = Path(config.__file__).resolve().parent.parent

    def test_every_action_is_pinned_by_commit(self):
        for flow in sorted((self.ROOT / ".github" / "workflows").glob("*.yml")):
            for line in flow.read_text(encoding="utf-8").splitlines():
                if "uses:" in line:
                    with self.subTest(flow=flow.name, line=line.strip()):
                        self.assertRegex(line, r"uses: [\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d")

    def test_the_ffmpeg_zip_is_checked_before_it_is_unpacked(self):
        flow = (self.ROOT / ".github" / "workflows" / "build-player.yml").read_text(encoding="utf-8")
        fetch = flow[flow.index("- name: Fetch ffmpeg"):flow.index("Expand-Archive")]
        self.assertTrue("Get-FileHash ffmpeg.zip -Algorithm SHA256" in fetch, fetch)
        self.assertTrue(re.search(r"\b[0-9A-F]{64}\b", fetch), fetch)


class PlayerRequirementsTest(unittest.TestCase):
    """The CI player builds install requirements-player.txt, not
    requirements.txt. segno and hidapi went into requirements.txt only, so the
    1.2.0 player would have shipped without the phone remote's QR code and
    without HID controllers."""

    # The planning half, which a player build leaves out on purpose.
    PLANNER_ONLY = {"librosa"}

    def test_the_player_pins_every_runtime_package_but_the_planner_ones(self):
        player = _pins("requirements-player.txt")
        for pkg, version in _pins("requirements.txt").items():
            if pkg in self.PLANNER_ONLY:
                continue
            with self.subTest(pkg=pkg):
                self.assertEqual(player.get(pkg), version)


class LicensePackTest(unittest.TestCase):
    """Marcel: "lege es mit rein". MIT, CC-BY and the ElevenLabs terms want
    their notice in every copy: the bundle carries the licence files in
    licenses/ (inside the .app on macOS), and the Windows and Linux player
    downloads show them in a Licenses folder beside the manual."""

    ROOT = Path(config.__file__).resolve().parent.parent
    # The GNU texts too: the GPL and LGPL want their full text with every copy
    # (mutagen, FFmpeg, Qt and its FFmpeg, on Linux libusb and libudev), and
    # PyInstaller leaves the packages' own licence files out of the bundle.
    FILES = ("LICENSE", "ICONS-LICENSE.txt", "THIRD_PARTY_LICENSES.md",
             "speech/LICENSE-AUDIO.md", "licenses/GPL-2.0.txt",
             "licenses/GPL-3.0.txt", "licenses/LGPL-2.1.txt",
             "licenses/LGPL-3.0.txt", "licenses/PYTHON-LICENSE.txt")

    def _read(self, name):
        return (self.ROOT / name).read_text(encoding="utf-8")

    def test_the_files_exist(self):
        for name in self.FILES:
            with self.subTest(name=name):
                self.assertTrue((self.ROOT / name).is_file())

    def test_the_bundle_carries_them(self):
        spec = self._read("dancesport.spec")
        for name in self.FILES:
            with self.subTest(name=name):
                self.assertIn(f'"{name}"', spec)
        self.assertIn('datas += [(os.path.join(SPECPATH, _licence), "licenses")', spec)

    def test_the_windows_and_linux_downloads_show_them(self):
        bat = self._read("build_exe.bat")
        linux = self._read("build_linux.sh")
        for name in self.FILES:
            with self.subTest(name=name):
                source = name.replace("/", "\\")
                self.assertIn(rf'copy /y "%~dp0{source}" "%~dp0dist\%APP_NAME%\Licenses\"',
                              bat)
                self.assertIn(f'cp {name} "dist/$APP_NAME/Licenses/"', linux)

    def test_the_notice_licences_have_their_notice(self):
        # MIT, BSD and MPL want the notice in every copy, and the bundle
        # has none of the packages' own files.
        text = self._read("THIRD_PARTY_LICENSES.md")
        notices = text[text.index("## Notices"):]
        for pkg in ("segno", "hidapi (cython-hidapi)", "HIDAPI", "sentry-sdk",
                    "urllib3", "certifi"):
            with self.subTest(pkg=pkg):
                self.assertIn(f"\n### {pkg}\n", notices)
        python = self._read("licenses/PYTHON-LICENSE.txt")
        self.assertIn("Copyright (c) 2001 Python Software Foundation", python)

    def test_the_python_licence_has_the_libraries_python_brings(self):
        # Marcel: "add missing libs". The interpreter carries expat, libffi,
        # mpdecimal, mimalloc, OpenSSL (with a DSN), bzip2 and Zstandard, and
        # their MIT/BSD/Apache terms want the notice in every copy.
        python = self._read("licenses/PYTHON-LICENSE.txt")
        for part in ("Licenses and Acknowledgements for Incorporated Software",
                     "expat", "libffi", "libmpdec", "mimalloc", "Apache License",
                     "strtod and dtoa", "Mersenne Twister",
                     "copyright (C) 1996-2019 Julian R Seward",
                     "For Zstandard software"):
            with self.subTest(part=part):
                self.assertIn(part, python)

    def test_every_player_package_is_listed_with_its_version(self):
        # segno and hidapi came with 1.2.0 and were missing from the list.
        text = self._read("THIRD_PARTY_LICENSES.md")
        player = text[text.index("## In the player build"):
                      text.index("## Only in the planner")]
        for pkg, version in _pins("requirements-player.txt").items():
            with self.subTest(pkg=pkg):
                row = next((line for line in player.splitlines()
                            if f"[{pkg}](" in line.lower()), "")
                self.assertIn(f"| {version} |", row)

    def test_every_full_package_is_listed_with_its_version(self):
        # Marcel: "do we need to add the lib mert to die about dialog, what is
        # with licence file?" The FULL build's torch stack was missing.
        text = self._read("THIRD_PARTY_LICENSES.md")
        full = text[text.index("## Only in the FULL build"):
                    text.index("## Icons and recordings")]
        for pkg, version in _pins("requirements-full.txt").items():
            with self.subTest(pkg=pkg):
                row = next((line for line in full.splitlines()
                            if f"[{pkg}](" in line.lower()), "")
                self.assertIn(f"| {version} |", row)
        # The weights are not bundled, but MERT's are non-commercial.
        mert = next((line for line in full.splitlines() if "MERT-v1-95M" in line), "")
        self.assertIn("CC BY-NC 4.0", mert)

    def test_the_full_notice_licences_have_their_notice(self):
        # Marcel: "add The file doesn't include the full MIT/BSD notice texts
        # for the full-build-only packages". Every package of a FULL row under
        # MIT, BSD or ISC gets its notice, as the player build's do.
        text = self._read("THIRD_PARTY_LICENSES.md")
        full = text[text.index("## Only in the FULL build"):
                    text.index("The model weights are not part")]
        notices = text[text.index("## Notices"):]
        rows = [line for line in full.splitlines() if line.startswith("| [")]
        self.assertGreater(len(rows), 10)
        for row in rows:
            licence = row.rstrip(" |").rsplit("|", 1)[-1]
            if not re.search(r"\b(MIT|BSD|ISC)\b", licence):
                continue
            for name in re.findall(r"\[([^\]]+)\]\(", row.split("|")[1]):
                with self.subTest(pkg=name):
                    self.assertIn(f"\n### {name}\n", notices)

    def test_the_full_build_carries_torchs_third_party_licences(self):
        # torch bundles over 30 libraries of its own; their texts ship in its
        # wheel's dist-info, which the bundle leaves out.
        spec = self._read("dancesport.spec")
        full = spec[spec.index("if FULL:\n    # torch's own third-party"):]
        self.assertIn('"licenses/TORCH-THIRD-PARTY.txt"', full.split("\n\n")[0])
        text = self._read("licenses/TORCH-THIRD-PARTY.txt")
        try:
            dist = importlib.metadata.distribution("torch")
        except importlib.metadata.PackageNotFoundError:
            self.skipTest("torch is not installed")
        self.assertIn(f"torch {dist.version}", text.splitlines()[0])
        third = {Path(str(f)).parts[3] for f in dist.files
                 if str(f).replace("\\", "/").split("/")[1:3] == ["licenses", "third_party"]}
        for name in sorted(third):
            with self.subTest(lib=name):
                self.assertIn(f"third_party/{name}/", text)


class DmgBackgroundTest(unittest.TestCase):
    """The drawn half of the .dmg window (tools/assets/dmg_background.py)."""

    def test_the_tests_workflow_has_pillow_to_draw_it(self):
        """Pillow is a build tool, not in requirements.txt: without it here
        the GitHub tests run died on `No module named 'PIL'`. It comes in
        through requirements-build.txt, which the lock the run installs takes in."""
        workflow = (Path(config.__file__).resolve().parent.parent / ".github"
                    / "workflows" / "tests.yml").read_text(encoding="utf-8")
        self.assertIn("pip install -r requirements.lock", workflow)
        self.assertIn("pillow", _pins("requirements-build.txt"))
        self.assertIn("pillow", _locked("requirements.lock"))

    def test_it_draws_the_window_size_and_twice_that_for_retina(self):
        from tools.assets import dmg_background as bg
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("sys.stdout"):
                bg.main([tmp])
            from PIL import Image
            with Image.open(Path(tmp) / "background.png") as one:
                self.assertEqual(one.size, bg.LAYOUT["window"])
            with Image.open(Path(tmp) / "background@2x.png") as two:
                self.assertEqual(two.size, tuple(2 * n for n in bg.LAYOUT["window"]))

    def test_it_names_where_macos_lets_the_app_open(self):
        from tools.assets import dmg_background as bg
        hint = " ".join(text for text, _ in bg.HINT)
        self.assertIn("Datenschutz & Sicherheit", hint)
        self.assertIn("Trotzdem öffnen", hint)
        self.assertIn("Privacy & Security", hint)

    def test_every_variable_the_script_reads_is_printed(self):
        from tools.assets import dmg_background as bg
        script = (Path(config.__file__).resolve().parent.parent
                  / "build_app.sh").read_text(encoding="utf-8")
        for name in bg.shell_vars():
            with self.subTest(name=name):
                self.assertRegex(script, rf"\b{name}\b")


class DataDirTest(unittest.TestCase):
    """Everything the app writes goes next to it — unless it cannot."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="dp_datadir_"))

    def test_a_writable_folder_is_writable(self):
        self.assertTrue(config._is_writable(self._tmp))

    def test_a_folder_that_is_not_there_is_not_writable(self):
        self.assertFalse(config._is_writable(self._tmp / "nope"))

    def test_the_probe_leaves_nothing_behind(self):
        config._is_writable(self._tmp)
        self.assertEqual(list(self._tmp.iterdir()), [])

    def test_a_writable_app_folder_stays_the_data_folder(self):
        """The portable-folder property: nothing moves, no migration."""
        self.assertEqual(config._data_dir(self._tmp), self._tmp)

    def test_a_folder_inside_a_dot_app_is_never_the_data_folder(self):
        """A writable bundle is still a bundle: the next version replaces it whole."""
        inside = Path("/Applications/DancePlaylist.app/Contents/MacOS")
        self.assertTrue(config._in_app_bundle(inside))
        user = self._tmp / "user"
        with mock.patch.object(config, "_is_writable", return_value=True), \
             mock.patch.object(config, "_user_data_dir", return_value=user):
            self.assertEqual(config._data_dir(inside), user)

    def test_an_ordinary_folder_is_not_a_bundle(self):
        self.assertFalse(config._in_app_bundle(self._tmp))
        self.assertFalse(config._in_app_bundle(
            Path("/Users/me/Contents/MacOS")))       # no .app above it

    def test_a_read_only_app_folder_falls_back_to_the_user_folder(self):
        user = self._tmp / "user data"
        with mock.patch.object(config, "_is_writable", return_value=False), \
             mock.patch.object(config, "_user_data_dir", return_value=user):
            self.assertEqual(config._data_dir(self._tmp / "app"), user)
        self.assertTrue(user.is_dir())          # created, ready to be written to

    def test_an_unusable_fallback_keeps_the_app_folder(self):
        """Nothing works — fail exactly the way the app failed before, not worse."""
        app = self._tmp / "app"
        with mock.patch.object(config, "_is_writable", return_value=False), \
             mock.patch.object(config, "_user_data_dir",
                               return_value=self._tmp / "user"), \
             mock.patch.object(Path, "mkdir", side_effect=OSError("read-only fs")):
            self.assertEqual(config._data_dir(app), app)

    def test_the_user_folder_is_the_one_the_os_expects(self):
        name = "DanceSport-Planner-Player"
        cases = {
            "darwin": ("HOME", Path("Library") / "Application Support" / name),
            "win32": ("LOCALAPPDATA", Path(name)),
            "linux": ("XDG_DATA_HOME", Path(name)),
        }
        for platform, (env_key, tail) in cases.items():
            with self.subTest(platform=platform):
                env = {env_key: str(self._tmp)}
                with mock.patch.object(sys, "platform", platform), \
                     mock.patch.dict(config.os.environ, env, clear=False), \
                     mock.patch.object(Path, "home", return_value=self._tmp):
                    self.assertEqual(config._user_data_dir(), self._tmp / tail)


class RenamedDataDirTest(unittest.TestCase):
    """The app was DancePlaylist; its user folder moves along with the name.

    A Mac that ran the old build has its database, settings and playlists in
    …/Application Support/DancePlaylist. The first start under the new name
    moves that folder over whole, so nothing is left behind or copied twice."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="dp_rename_"))
        self.new = self._tmp / "DanceSport-Planner-Player"
        self.old = self._tmp / "DancePlaylist"
        self._bundle = Path("/Applications/DanceSport Planner & Player.app"
                            "/Contents/MacOS")

    def _data_dir(self):
        with mock.patch.object(config, "_user_data_dir", return_value=self.new):
            return config._data_dir(self._bundle)

    def test_the_old_folder_moves_to_the_new_name(self):
        self.old.mkdir()
        (self.old / "audio_features.db").write_bytes(b"db")
        self.assertEqual(self._data_dir(), self.new)
        self.assertEqual((self.new / "audio_features.db").read_bytes(), b"db")
        self.assertFalse(self.old.exists())

    def test_a_new_folder_that_is_there_already_wins(self):
        """Moved before, or started fresh: the old folder is left alone."""
        self.old.mkdir()
        self.new.mkdir()
        (self.new / "gui_settings.json").write_text("{}")
        self.assertEqual(self._data_dir(), self.new)
        self.assertTrue(self.old.is_dir())

    def test_no_old_folder_starts_a_new_one(self):
        self.assertEqual(self._data_dir(), self.new)
        self.assertTrue(self.new.is_dir())

    def test_a_move_that_fails_keeps_using_the_old_folder(self):
        """Never start empty next to the user's real data."""
        self.old.mkdir()
        with mock.patch.object(Path, "rename", side_effect=OSError("busy")):
            self.assertEqual(self._data_dir(), self.old)
        self.assertFalse(self.new.exists())

    def test_a_writable_app_folder_is_not_touched_by_the_move(self):
        """The portable folder next to the .exe is not a user folder."""
        self.old.mkdir()
        app = self._tmp / "app"
        app.mkdir()
        with mock.patch.object(config, "_user_data_dir", return_value=self.new):
            self.assertEqual(config._data_dir(app), app)
        self.assertTrue(self.old.is_dir())


class WriteJsonAtomicTest(unittest.TestCase):

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="dp_json_"))

    def test_round_trip(self):
        target = self._tmp / "out.json"
        config.write_json_atomic(target, {"a": 1, "täkte": [58, 59]})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")),
                         {"a": 1, "täkte": [58, 59]})
        self.assertFalse(target.with_suffix(".json.tmp").exists())

    def test_overwrites_existing(self):
        target = self._tmp / "out.json"
        target.write_text('{"old": true}', encoding="utf-8")
        config.write_json_atomic(target, {"new": True})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")),
                         {"new": True})

    def test_the_bytes_are_on_disk_before_the_file_is_swapped_in(self):
        """NTFS journals the rename, not the data: a power cut right after it
        left a settings file of zeros where the old one had been."""
        target = self._tmp / "out.json"
        calls = []
        real_fsync, real_replace = config.os.fsync, config.os.replace
        with mock.patch.object(config.os, "fsync",
                               side_effect=lambda fd: (calls.append("fsync"),
                                                       real_fsync(fd))), \
             mock.patch.object(config.os, "replace",
                               side_effect=lambda a, b: (calls.append("replace"),
                                                         real_replace(a, b))):
            config.write_json_atomic(target, {"a": 1})
        self.assertEqual(calls, ["fsync", "replace"])

    def test_two_writers_of_one_file_do_not_share_a_temp_file(self):
        """The autosave and a worker thread can save the same store at once;
        with one fixed .tmp name the second truncated the first one's half-
        written file and the first one's swap then found nothing to move."""
        target = self._tmp / "out.json"
        real_replace = config.os.replace
        state = {"first": True}

        def replace(src, dst):
            if state.pop("first", False):
                config.write_json_atomic(target, {"writer": "B"})   # B runs whole
            real_replace(src, dst)

        with mock.patch.object(config.os, "replace", side_effect=replace):
            config.write_json_atomic(target, {"writer": "A"})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")),
                         {"writer": "A"})
        self.assertEqual([p.name for p in self._tmp.iterdir()], ["out.json"])

    def test_a_write_that_fails_leaves_no_temp_file(self):
        target = self._tmp / "out.json"
        with mock.patch.object(config.os, "replace", side_effect=OSError("locked")):
            with self.assertRaises(OSError):
                config.write_json_atomic(target, {"a": 1})
        self.assertEqual(list(self._tmp.iterdir()), [])

    def test_a_target_locked_for_a_moment_is_written_anyway(self):
        """A virus scanner opens a file the moment it is written, and Windows
        refuses to replace it while it looks (WinError 32): the next save of the
        same file, a moment later, was lost."""
        target = self._tmp / "out.json"
        real_replace = config.os.replace
        state = {"locked": 2}

        def replace(src, dst):
            if state["locked"]:
                state["locked"] -= 1
                raise PermissionError(13, "used by another process")
            real_replace(src, dst)

        with mock.patch.object(config.os, "replace", side_effect=replace), \
             mock.patch.object(config.time, "sleep") as sleep:
            config.write_json_atomic(target, {"a": 1})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"a": 1})
        self.assertEqual(sleep.call_count, 2)

    def test_a_target_that_stays_locked_still_fails(self):
        target = self._tmp / "out.json"
        with mock.patch.object(config.os, "replace",
                               side_effect=PermissionError(13, "locked")), \
             mock.patch.object(config.time, "sleep"):
            with self.assertRaises(PermissionError):
                config.write_json_atomic(target, {"a": 1})
        self.assertEqual(list(self._tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
