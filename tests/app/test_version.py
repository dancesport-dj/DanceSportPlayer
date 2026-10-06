#!/usr/bin/env python3
"""Tests for planner.version — which release a build is.

Run:  py -m unittest tests.app.test_version -v

Marcel: "ich brauche eine versionierung in der app und in github sonst kann ich
fehler nicht nachvollziehen". The tag a release is built from has to reach the
running app, its title bar and every 🐞 error report.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner import version

ROOT = Path(__file__).resolve().parents[2]


class BuildVersionTest(unittest.TestCase):
    """What the spec bakes in. Marcel: "the builded exe should have the
    version number", not the commit hash a build without a tag got from git
    describe. The number lives in planner.version, and a release tag
    overrides it: "wenn git ein tag hat soll es die version.py überschreiben
    damit es auf github stimmig ist". And "no v everywhere": the tag's v
    stays on the tag."""

    def test_a_build_without_a_tag_has_the_code_version(self):
        with mock.patch.dict(os.environ, {version.VERSION_ENV: ""}):
            self.assertEqual(version.build_version(), version.VERSION)

    def test_a_matching_release_tag_builds(self):
        tag = f" v{version.VERSION} "
        with mock.patch.dict(os.environ, {version.VERSION_ENV: tag}):
            self.assertEqual(version.build_version(), version.VERSION)

    def test_a_release_tag_overrides_the_code_version(self):
        # The GitHub release is named after the tag, so the app inside it and
        # its error reports have to say the same number.
        with mock.patch.dict(os.environ, {version.VERSION_ENV: "v999.0.0"}):
            self.assertEqual(version.build_version(), "999.0.0")

    def test_the_code_version_is_a_real_number(self):
        self.assertFalse(version.VERSION.startswith("v"))
        self.assertNotEqual(version.numbers(version.VERSION), (0, 0, 0))


class NumbersTest(unittest.TestCase):
    """The .exe's file version and the macOS bundle version take numbers only."""

    def test_a_version(self):
        self.assertEqual(version.numbers("1.2.3"), (1, 2, 3))
        self.assertEqual(version.numbers("v1.2.3"), (1, 2, 3))

    def test_a_short_version(self):
        self.assertEqual(version.numbers("1.4"), (1, 4, 0))

    def test_a_commit_or_dev_is_zero(self):
        self.assertEqual(version.numbers("abc1234"), (0, 0, 0))
        self.assertEqual(version.numbers("dev"), (0, 0, 0))

    def test_a_commit_that_starts_with_digits_is_no_version(self):
        # A local build without a tag is named by its hash (git describe
        # --always): 728c49b is no version 728, and an all-digit hash would
        # not even fit the .exe's 16-bit version fields.
        self.assertEqual(version.numbers("728c49b"), (0, 0, 0))
        self.assertEqual(version.numbers("1234567"), (0, 0, 0))
        self.assertEqual(version.numbers("1234567-dirty"), (0, 0, 0))


class AppVersionTest(unittest.TestCase):
    """What the running app reads back."""

    def setUp(self):
        self.bundle = Path(tempfile.mkdtemp(prefix="dp_version_"))
        for attr in ("frozen", "_MEIPASS"):
            if hasattr(sys, attr):
                self.addCleanup(setattr, sys, attr, getattr(sys, attr))
            else:
                self.addCleanup(lambda a=attr: hasattr(sys, a) and delattr(sys, a))

    def _freeze(self, text=None):
        sys.frozen = True
        sys._MEIPASS = str(self.bundle)
        if text is not None:
            (self.bundle / version.VERSION_FILE).write_text(text, encoding="utf-8")

    def test_a_source_run_is_dev(self):
        self.assertEqual(version.app_version(), "dev")

    def test_a_build_reads_what_the_spec_bundled(self):
        self._freeze("1.2.0\n")
        self.assertEqual(version.app_version(), "1.2.0")

    def test_a_build_without_the_file_is_dev(self):
        self._freeze()
        self.assertEqual(version.app_version(), "dev")


class ShownTest(unittest.TestCase):
    """Where the version shows up."""

    def test_the_title_bar_names_the_release(self):
        from gui.dialogs import app_title
        self.assertEqual(app_title("player", "1.2.0"), "DanceSport Player 1.2.0")

    def test_a_source_run_keeps_the_plain_title(self):
        from gui.dialogs import app_title
        self.assertEqual(app_title("player", "dev"), "DanceSport Player")
        self.assertEqual(app_title("both"), "DanceSport Planner & Player")

    def test_an_error_report_names_the_release(self):
        from shared import error_reports
        self.addCleanup(setattr, error_reports, "_active", False)
        error_reports._active = False
        with mock.patch.object(error_reports, "dsn",
                               return_value="https://k@errors.example.invalid/1"), \
                mock.patch.object(error_reports, "app_version", return_value="1.2.0"), \
                mock.patch("sentry_sdk.init") as init:
            error_reports.apply({"error_reports": True})
        self.assertEqual(init.call_args.kwargs["release"], "1.2.0")


class BuildWiringTest(unittest.TestCase):
    """The tag has to get from GitHub into the bundle."""

    def test_the_spec_bundles_the_version(self):
        spec = (ROOT / "dancesport.spec").read_text(encoding="utf-8")
        self.assertIn("build_version()", spec)
        self.assertIn("datas += [(_version_file, \".\")]", spec)
        self.assertIn("version=exe_version_info", spec)
        self.assertIn('"CFBundleShortVersionString": VERSION_NUMBERS', spec)

    def test_every_release_build_gets_the_tag(self):
        # Windows, macOS and Linux.
        flow = (ROOT / ".github" / "workflows" / "build-player.yml").read_text(
            encoding="utf-8")
        self.assertEqual(flow.count(f"{version.VERSION_ENV}: ${{{{ startsWith("
                                    "github.ref, 'refs/tags/v') && github.ref_name"), 3)

    def test_the_release_downloads_carry_no_v(self):
        # Marcel: the download names lose the tag's v too, like the app.
        flow = (ROOT / ".github" / "workflows" / "build-player.yml").read_text(
            encoding="utf-8")
        self.assertIn('VERSION="${TAG#v}"', flow)
        self.assertNotIn("DanceSport-Player-$TAG-", flow)
        self.assertIn('"DanceSport-Player-$VERSION-windows.zip"', flow)
        self.assertIn('"DanceSport-Player-$VERSION-macos.dmg"', flow)
        self.assertIn('"DanceSport-Player-$VERSION-linux.tar.gz"', flow)
        self.assertIn('--title "DanceSport Player $VERSION"', flow)

    def test_every_download_says_how_to_install_it(self):
        # Marcel: "i miss a readme or info for the user which tells him how to
        # install or open it". Each download carries its platform's guide, and
        # the release text links all three.
        flow = (ROOT / ".github" / "workflows" / "build-player.yml").read_text(
            encoding="utf-8")
        script = (ROOT / "build_app.sh").read_text(encoding="utf-8")
        linux = (ROOT / "build_linux.sh").read_text(encoding="utf-8")
        self.assertIn("cp docs/install/windows.md artifacts/DanceSport-Player/README.txt",
                      flow)
        self.assertIn('cp docs/install/linux.md "dist/$APP_NAME/README.txt"', linux)
        self.assertIn('cp docs/install/macos.md "$STAGE/README.txt"', script)
        for name in ("windows", "macos", "linux"):
            with self.subTest(platform=name):
                self.assertTrue((ROOT / "docs" / "install" / f"{name}.md").exists())
                self.assertIn(f"docs/install/{name}.md)", flow)

    def test_the_linux_docs_name_arch_for_ffmpeg(self):
        # Marcel asked about Arch (Omarchy): the tar.gz runs there, only the
        # docs named apt and dnf alone.
        guide = (ROOT / "docs" / "install" / "linux.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(guide.count("sudo pacman -S ffmpeg"), 2)  # English, German
        self.assertIn("sudo pacman -S ffmpeg", readme)


if __name__ == "__main__":
    unittest.main()
