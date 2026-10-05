"""A store-download filename gives way to the ID3 title.

Run:  py -m unittest tests.planner.test_slug_title -v

User feedback: 'The_Moonlight_Sonata_2_CD1_04_Ugoy_Lullaby_Langsamer_Walzer_29BPM.mp3'
showed that whole filename as its title, though its TIT2 tag reads
'Ugoy - Lullaby'. The title comes from the filename on purpose (the library
is named by hand), but a slug — no spaces, words glued by '_' or '-' — was
never named by a person, and a spaced tag title is the better label.
"""
import unittest

from planner.parsing import _title_for


class SlugTitleTest(unittest.TestCase):

    def test_a_slug_filename_takes_the_tag_title(self):
        stem = "The_Moonlight_Sonata_2_CD1_04_Ugoy_Lullaby_Langsamer_Walzer_29BPM"
        self.assertEqual(_title_for(stem, "Ugoy - Lullaby"), "Ugoy - Lullaby")

    def test_a_hyphen_slug_takes_the_tag_title(self):
        stem = "free-dancesport-music-project_hidden-falls-sw-29bpm"
        self.assertEqual(_title_for(stem, "Hidden Falls"), "Hidden Falls")

    def test_a_hand_named_file_keeps_its_name(self):
        self.assertEqual(_title_for("Timber (Sf29)", "Timber feat. Ke$ha"), "Timber")

    def test_a_single_word_name_is_no_slug(self):
        self.assertEqual(_title_for("Quickstep", "Sing Sing Sing"), "Quickstep")

    def test_a_slug_tag_title_does_not_replace_the_filename(self):
        self.assertEqual(_title_for("4_applause_all", "Applaus_all"),
                         _title_for("4_applause_all"))

    def test_a_slug_without_a_tag_keeps_the_cleaned_filename(self):
        stem = "The_Moonlight_Sonata_2_CD1_04_Ugoy_Lullaby_Langsamer_Walzer_29BPM"
        self.assertEqual(_title_for(stem, None), _title_for(stem))
        self.assertNotEqual(_title_for(stem), "Ugoy - Lullaby")


if __name__ == "__main__":
    unittest.main(verbosity=2)
