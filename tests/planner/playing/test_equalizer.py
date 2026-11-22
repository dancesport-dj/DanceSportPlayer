#!/usr/bin/env python3
"""🎚 The equalizer settings (planner.playing.equalizer).

Run:  .venv/Scripts/python.exe -m unittest tests.planner.playing.test_equalizer -v
"""
import unittest

from planner.playing import equalizer as eqs


def _saved(source: str, **cfg) -> dict:
    return {"equalizer": {source: cfg}}


class EqualizerSettingsTest(unittest.TestCase):

    # ===== Acceptance criteria =====

    def test_every_source_starts_off_and_flat(self):
        for source in eqs.SOURCES:
            cfg = eqs.eq_of({}, source)
            self.assertFalse(cfg["on"], source)
            self.assertEqual(len(cfg["bands"]), 5, source)
            self.assertTrue(all(b["gain"] == 0.0 for b in cfg["bands"]), source)
            self.assertEqual(eqs.audible_bands(cfg), [], source)

    def test_the_voice_starts_with_a_higher_low_cut_and_no_low_shelf(self):
        voice = eqs.eq_of({}, "announcer")["bands"]
        self.assertEqual(voice[0]["freq"], 100.0)
        self.assertFalse(voice[1]["on"])
        self.assertEqual(eqs.eq_of({}, "music")["bands"][0]["freq"], 30.0)

    def test_a_preset_sets_the_four_gains_after_the_low_cut(self):
        cfg = eqs.apply_preset(eqs.eq_of({}, "music"), "boomy_hall", {})
        self.assertEqual([b["gain"] for b in cfg["bands"][1:]], [-3.0, -3.0, 1.0, 1.0])
        self.assertEqual(cfg["preset"], "boomy_hall")
        self.assertEqual(cfg["bands"][0]["freq"], 30.0)

    def test_the_operators_own_preset_is_saved_applied_and_deleted(self):
        settings = eqs.with_user_preset({}, "Stadthalle", [-2, -4, 1, 0])
        self.assertEqual(eqs.user_presets(settings), {"Stadthalle": (-2.0, -4.0, 1.0, 0.0)})
        cfg = eqs.apply_preset(eqs.eq_of(settings, "music"), "Stadthalle", settings)
        self.assertEqual(cfg["bands"][2]["gain"], -4.0)
        self.assertEqual(eqs.user_presets(eqs.with_user_preset(settings, "Stadthalle", None)), {})

    def test_bypass_keeps_the_path_but_passes_the_sound(self):
        """Bypass is an A/B compare inside the EQ path; only "off" leaves it."""
        cfg = eqs.apply_preset(eqs.eq_of({}, "music"), "weak_speakers", {})
        cfg = {**cfg, "on": True, "bypass": True}
        self.assertTrue(eqs.tapped(cfg))
        self.assertEqual(eqs.audible_bands(cfg), [])
        self.assertEqual(len(eqs.audible_bands({**cfg, "bypass": False})), 5)

    # ===== Core behavior =====

    def test_a_saved_eq_round_trips(self):
        cfg = eqs.apply_preset(eqs.eq_of({}, "cue"), "small_room", {})
        cfg["on"] = True
        settings = eqs.with_eq({"zoom": 2}, "cue", cfg)
        self.assertEqual(eqs.eq_of(settings, "cue"), cfg)
        self.assertEqual(settings["zoom"], 2)

    def test_replacing_one_source_keeps_the_others_and_the_presets(self):
        settings = eqs.with_user_preset(_saved("music", on=True), "Mine", [1, 1, 1, 1])
        settings = eqs.with_eq(settings, "announcer", eqs.default_eq("announcer"))
        self.assertTrue(eqs.eq_of(settings, "music")["on"])
        self.assertIn("Mine", eqs.user_presets(settings))

    def test_gains_are_held_to_12_db(self):
        bands = [dict(b) for b in eqs.default_eq("music")["bands"]]
        bands[2]["gain"], bands[3]["gain"] = 40, -99
        cfg = eqs.eq_of(_saved("music", bands=bands), "music")
        self.assertEqual((cfg["bands"][2]["gain"], cfg["bands"][3]["gain"]), (12.0, -12.0))

    def test_frequencies_are_only_the_operators_with_advanced_on(self):
        bands = [dict(b) for b in eqs.default_eq("music")["bands"]]
        bands[3]["freq"], bands[3]["q"] = 4000, 2.0
        plain = eqs.eq_of(_saved("music", bands=bands), "music")
        self.assertEqual(plain["bands"][3]["freq"], 2500.0)
        advanced = eqs.eq_of(_saved("music", bands=bands, advanced=True), "music")
        self.assertEqual((advanced["bands"][3]["freq"], advanced["bands"][3]["q"]), (4000.0, 2.0))

    def test_the_low_cut_can_be_switched_off_without_advanced(self):
        bands = [dict(b) for b in eqs.default_eq("music")["bands"]]
        bands[0]["on"] = False
        self.assertFalse(eqs.eq_of(_saved("music", bands=bands), "music")["bands"][0]["on"])

    def test_the_low_cut_keeps_its_frequency_without_advanced(self):
        """Marcel: the cut-off is picked from a list, without ⚙ Advanced."""
        bands = [dict(b) for b in eqs.default_eq("music")["bands"]]
        bands[0]["freq"], bands[0]["q"] = 80, 2.0
        cut = eqs.eq_of(_saved("music", bands=bands), "music")["bands"][0]
        self.assertEqual((cut["freq"], cut["q"]), (80.0, eqs.default_eq("music")["bands"][0]["q"]))

    # ===== Coverage and null checks =====

    def test_broken_settings_fall_back_to_the_defaults(self):
        for broken in ({"equalizer": "x"}, {"equalizer": {"music": 3}},
                       _saved("music", bands="x"), _saved("music", bands=[{}] * 2)):
            self.assertEqual(eqs.eq_of(broken, "music")["bands"],
                             eqs.default_eq("music")["bands"], broken)

    def test_a_band_of_the_wrong_kind_keeps_its_default(self):
        bands = [dict(b) for b in eqs.default_eq("music")["bands"]]
        bands[2] = {"kind": "notch", "gain": 6}
        self.assertEqual(eqs.eq_of(_saved("music", bands=bands), "music")["bands"][2]["gain"], 0.0)

    def test_a_non_number_gain_is_zero(self):
        bands = [dict(b) for b in eqs.default_eq("music")["bands"]]
        bands[1]["gain"] = "loud"
        bands[2]["gain"] = float("nan")
        cfg = eqs.eq_of(_saved("music", bands=bands), "music")
        self.assertEqual((cfg["bands"][1]["gain"], cfg["bands"][2]["gain"]), (0.0, 0.0))

    def test_an_unknown_preset_changes_nothing(self):
        cfg = eqs.eq_of({}, "music")
        self.assertIs(eqs.apply_preset(cfg, "nope", {}), cfg)

    def test_malformed_user_presets_are_left_out(self):
        settings = {"equalizer": {"presets": {"ok": [0, 0, 0, 0], "short": [1], "": [0] * 4}}}
        self.assertEqual(list(eqs.user_presets(settings)), ["ok"])


if __name__ == "__main__":
    unittest.main()
