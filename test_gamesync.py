import json
import tempfile
import unittest
from pathlib import Path

import gamesync as g

DATA = Path(__file__).parent / "testdata"
HOME = "C:/Users/ramray"
STEAM = ["E:/steam"]
INSTALLED = {570, 578080}  # Dota 2, PUBG
SKIP = STEAM + ["C:/Program Files/WindowsApps"]


def load():
    preview = json.loads((DATA / "preview_sample.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA / "manifest_sample.json").read_text(encoding="utf-8"))
    return preview, manifest


class PortablePath(unittest.TestCase):
    def test_home_relative_round_trip_with_other_username(self):
        p = g.to_portable("C:\\Users\\ramray\\AppData\\LocalLow\\Team Cherry\\Hollow Knight", HOME)
        self.assertEqual(p, "<home>/AppData/LocalLow/Team Cherry/Hollow Knight")
        self.assertEqual(g.from_portable(p, "C:/Users/claw"),
                         "C:/Users/claw/AppData/LocalLow/Team Cherry/Hollow Knight")

    def test_case_insensitive_home(self):
        self.assertEqual(g.to_portable("c:/users/RAMRAY/Saved Games/X", HOME), "<home>/Saved Games/X")

    def test_outside_home_stays_absolute(self):
        p = g.to_portable("C:/XboxGames/GameSave/pgs/u_1", HOME)
        self.assertEqual(p, "C:/XboxGames/GameSave/pgs/u_1")
        self.assertEqual(g.from_portable(p, "C:/Users/claw"), p)

    def test_similar_prefix_is_not_home(self):
        self.assertEqual(g.to_portable("C:/Users/ramray2/x", HOME), "C:/Users/ramray2/x")


class Roots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preview, cls.manifest = load()

    def roots(self, name):
        files = list(self.preview[name]["files"])
        pats = list(self.manifest.get(name, {}).get("files", {}))
        return g.compute_roots(files, pats, HOME, SKIP)

    def test_absolum_file_patterns_use_parent_dir(self):
        self.assertEqual(self.roots("Absolum")[0], [HOME + "/AppData/Local/Absolum_SaveGame_Steam"])

    def test_hades(self):
        self.assertEqual(self.roots("Hades II")[0], [HOME + "/Saved Games/Hades II"])

    def test_outer_wilds(self):
        self.assertEqual(self.roots("Outer Wilds")[0],
                         [HOME + "/AppData/LocalLow/Mobius Digital/Outer Wilds/SteamSaves"])

    def test_my_games_is_not_synced_whole(self):
        roots = self.roots("Dragon Quest I & II HD-2D Remake")[0]
        self.assertEqual(len(roots), 1)
        self.assertTrue(roots[0].startswith(HOME + "/Documents/My Games/DRAGON QUEST"))

    def test_forza_two_locations(self):
        roots = self.roots("Forza Horizon 6")[0]
        self.assertEqual(sorted(roots), sorted([
            "C:/XboxGames/GameSave/pgs/u_2535405491797049_16D460",
            HOME + "/AppData/Local/ForzaHorizon6/LocalStorage_Shared"]))

    def test_sibling_dirs_merge(self):
        self.assertEqual(self.roots("Disco Elysium")[0],
                         [HOME + "/AppData/LocalLow/ZAUM Studio/Disco Elysium"])

    def test_different_bases_do_not_merge(self):
        self.assertEqual(len(self.roots("Sid Meier's Civilization VI")[0]), 2)

    def test_steam_userdata_skipped(self):
        roots, skipped, _ = self.roots("Astlibra Revision")
        self.assertEqual(roots, [HOME + "/AppData/Local/ASTLIBRA/SAVE"])
        self.assertTrue(skipped and all(s.startswith("E:/steam") for s in skipped))

    def test_no_root_is_broad(self):
        broad = {g.pkey(b) for b in g.broad_dirs(HOME)}
        for name in self.preview:
            for r in self.roots(name)[0]:
                self.assertNotIn(g.pkey(r), broad, f"{name}: {r}")

    def test_file_directly_in_broad_dir_is_problem(self):
        roots, _, problems = g.compute_roots([HOME + "/AppData/Local/loose.sav"], [], HOME)
        self.assertEqual(roots, [])
        self.assertEqual(problems, [HOME + "/AppData/Local/loose.sav"])

    def test_unmatched_file_uses_anchor(self):
        roots, _, _ = g.compute_roots([HOME + "/AppData/Roaming/Foo/sub/a.sav"], [], HOME)
        self.assertEqual(roots, [HOME + "/AppData/Roaming/Foo"])


class Steam(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preview, cls.manifest = load()

    def reason(self, name):
        return g.steam_reason(list(self.preview[name]["files"]), self.manifest.get(name, {}), STEAM, INSTALLED)

    def test_installed(self):
        self.assertEqual(self.reason("Dota 2"), "installed in Steam")
        self.assertEqual(self.reason("PUBG: Battlegrounds"), "installed in Steam")

    def test_userdata(self):
        self.assertEqual(self.reason("Astlibra Revision"), "saves in Steam dir")

    def test_non_steam(self):
        self.assertIsNone(self.reason("Hades II"))
        self.assertIsNone(self.reason("Forza Horizon 6"))

    def test_library_parsing(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "steamapps").mkdir()
            (Path(d) / "steamapps" / "appmanifest_123.acf").write_text("x")
            (Path(d) / "steamapps" / "appmanifest_bad.acf").write_text("x")
            self.assertEqual(g.installed_steam_ids([d]), {123})


class Misc(unittest.TestCase):
    def test_parse_selection(self):
        self.assertEqual(g.parse_selection("1,3,5-7", 8), [0, 2, 4, 5, 6])
        self.assertEqual(g.parse_selection("2\uff0c1 2", 3), [1, 0])  # full-width comma
        self.assertEqual(g.parse_selection("3-1", 3), [0, 1, 2])
        with self.assertRaises(ValueError):
            g.parse_selection("9", 3)
        with self.assertRaises(ValueError):
            g.parse_selection("a", 3)

    def test_slugify(self):
        self.assertEqual(g.slugify("Hades II"), "hades-ii")
        self.assertEqual(g.slugify("Sid Meier's Civilization VI"), "sid-meier-s-civilization-vi")
        s = g.slugify("\u30ec\u30a4\u30b8\u30f3\u30b0")  # non-ASCII name
        self.assertTrue(s.startswith("g") and len(s) == 9)

    def test_pattern_prefix(self):
        self.assertEqual(g.pattern_prefix("<winDocuments>/My Games/X/<storeUserId>/*.sav", HOME),
                         HOME + "/Documents/My Games/X")
        self.assertIsNone(g.pattern_prefix("<base>/save/*", HOME))

    def test_registry_skips_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            g.write_entry(Path(d), {"folder_id": "gs-a", "game": "A"})
            (Path(d) / "gs-a.sync-conflict-20260101-000000-ABCDEFG.json").write_text('{"folder_id":"gs-x"}')
            (Path(d) / "gs-broken.json").write_text("{")
            self.assertEqual(list(g.read_registry(Path(d))), ["gs-a"])

    def test_nesting_conflict(self):
        folders = [{"id": "gs-a", "path": "C:\\Users\\x\\AppData\\Local\\Game\\Saved\\Config"}]
        self.assertIsNotNone(g.nesting_conflict("C:/Users/x/AppData/Local/Game/Saved", folders))
        self.assertIsNone(g.nesting_conflict("C:/Users/x/AppData/Local/Game2", folders))


class Settings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preview, cls.manifest = load()

    def split(self, name):
        return g.classify_files(list(self.preview[name]["files"]), self.manifest.get(name, {}), HOME)

    def plan(self, name):
        saves, configs = self.split(name)
        pats = list(self.manifest.get(name, {}).get("files", {}))
        roots, _, _ = g.compute_roots(saves, pats, HOME, SKIP)
        return roots, {r: g.config_ignores(r, saves, configs) for r in roots}

    def test_pattern_regex(self):
        rx = g.pattern_regex("<winLocalAppData>/Foo/*/save?.dat", HOME)
        self.assertTrue(rx.match(HOME + "/AppData/Local/Foo/profile/save1.dat"))
        self.assertTrue(rx.match("c:/users/RAMRAY/appdata/local/foo/p/SAVE1.DAT"))
        self.assertFalse(rx.match(HOME + "/AppData/Local/Foo/a/b/save1.dat"))
        deep = g.pattern_regex("<winDocuments>/Game/**/*.sav", HOME)
        self.assertTrue(deep.match(HOME + "/Documents/Game/a/b/c.sav"))
        folder = g.pattern_regex("<winAppData>/Game/Saves", HOME)
        self.assertTrue(folder.match(HOME + "/AppData/Roaming/Game/Saves/slot1/data.bin"))
        self.assertIsNone(g.pattern_regex("<base>/cfg/*", HOME))

    def test_hades_settings_file(self):
        saves, configs = self.split("Hades II")
        self.assertEqual([c.rsplit("/", 1)[1] for c in configs], ["GlobalSettingsWin.sjson"])
        self.assertIn(HOME + "/Saved Games/Hades II/Profile1.sav", saves)
        roots, ign = self.plan("Hades II")
        self.assertEqual(roots, [HOME + "/Saved Games/Hades II"])
        self.assertEqual(ign[roots[0]], ["GlobalSettingsWin.sjson"])

    def test_last_of_us_screen_settings(self):
        _, configs = self.split("The Last of Us Part I")
        self.assertTrue(any(c.endswith("screeninfo.cfg") for c in configs))
        roots, ign = self.plan("The Last of Us Part I")
        self.assertTrue(any(i.endswith("screeninfo.cfg") for r in roots for i in ign[r]))

    def test_fragpunk_config_dir_not_synced(self):
        saves, configs = self.split("FragPunk")
        self.assertTrue(saves and configs)
        self.assertTrue(all("/Saved/Config/" in c for c in configs))
        roots, ign = self.plan("FragPunk")
        self.assertEqual(roots, [HOME + "/AppData/Local/FragPunk/Steam/Saved/SaveGames"])
        self.assertEqual(ign[roots[0]], [])

    def test_snowbreak_settings_only(self):
        saves, configs = self.split("Snowbreak: Containment Zone")
        self.assertEqual(saves, [])
        self.assertTrue(configs)

    def test_config_dir_collapses(self):
        root = "C:/g"
        saves = ["C:/g/SaveGames/1.sav"]
        configs = ["C:/g/Config/Win/a.ini", "C:/g/Config/Win/b.ini", "C:/g/Config/c.ini", "C:/g/SaveGames/opts.ini"]
        self.assertEqual(g.config_ignores(root, saves, configs), ["Config", "SaveGames/opts.ini"])

    def test_ignore_line_escaping(self):
        self.assertEqual(g.ignore_line("Config", True), "/Config")
        self.assertEqual(g.ignore_line("a[1]/b*.ini", True), "/a|[1|]/b|*.ini")
        self.assertEqual(g.ignore_line("a[1]/b*.ini", False), "/a\\[1\\]/b\\*.ini")

    def test_untagged_files_count_as_saves(self):
        saves, configs = g.classify_files([HOME + "/AppData/Local/X/s.dat"], {}, HOME)
        self.assertEqual((len(saves), configs), (1, []))


class Unshare(unittest.TestCase):
    def test_split_registry(self):
        me, other = "ME", "OTHER"
        reg = {
            "gs-a": {"folder_id": "gs-a", "devices": [other, me]},                   # offered, not here
            "gs-b": {"folder_id": "gs-b", "devices": [other, me]},                   # already here
            "gs-c": {"folder_id": "gs-c", "devices": [other, me], "removed": True},  # unshared, still here
            "gs-d": {"folder_id": "gs-d", "devices": [other, me], "removed": True},  # unshared, gone here
            "gs-e": {"folder_id": "gs-e", "devices": [other]},                       # not for me
        }
        to_remove, to_accept = g.split_registry(reg, me, {"gs-b", "gs-c"})
        self.assertEqual([e["folder_id"] for e in to_remove], ["gs-c"])
        self.assertEqual([e["folder_id"] for e in to_accept], ["gs-a"])

    def test_active(self):
        self.assertTrue(g.active({"folder_id": "x"}))
        self.assertFalse(g.active({"folder_id": "x", "removed": True}))


class Menu(unittest.TestCase):
    def run_menu(self, inputs):
        import contextlib
        import io
        from unittest import mock
        out, err = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as d, \
                mock.patch("builtins.input", side_effect=list(inputs)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = g.main(["--config-dir", d])
        return code, out.getvalue(), err.getvalue()

    def test_menu_runs_command_and_returns(self):
        # 9 = invalid, 5 = status (fails: not configured), Enter, 0 = exit
        code, out, err = self.run_menu(["9", "5", "", "0"])
        self.assertEqual(code, 0)
        self.assertIn("not set up yet", out)
        self.assertIn("Invalid choice", out)
        self.assertIn("--- status ---", out)
        self.assertIn("NAS is not configured", err)
        self.assertEqual(out.count("=== gamesync"), 3)  # menu shown again after each step

    def test_menu_exit_on_eof(self):
        code, out, _ = self.run_menu([EOFError()])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
