from __future__ import annotations

import argparse
import contextlib
import io
import unittest
from pathlib import Path

from mini_keyboard_tool.catalog import (
    PROCREATE_ACTIONS,
    PROCREATE_PRESET_BY_SLUG,
    VENDOR_MODELS,
    vendor_model_handlers,
)
from mini_keyboard_tool.cli import (
    _build_clear_reports,
    _build_experiment_reports,
    _build_profile_reports,
    _build_test_plan,
    _config_report_from_snapshot_item,
    _config_response_to_dict,
    _diff_snapshot_config,
    _diff_snapshot_led,
    _summarize_config_response,
    _led_report_from_snapshot_item,
    _read_config_requested_keys,
    _verify_tested_profile,
    build_parser,
    cmd_clear,
    cmd_procreate,
    cmd_procreate_actions,
    cmd_remap,
    cmd_test_plan,
    cmd_vendor_key_aliases,
    cmd_vendor_models,
    parse_mouse_action,
    parse_key_slots,
    parse_macro_tokens,
)
from mini_keyboard_tool.gui import (
    _parse_slot_list as _parse_gui_slot_list,
    _summarize_config_response as _summarize_gui_config_response,
)
from mini_keyboard_tool.keycodes import (
    keycode_name,
    media_usage_name,
    modifier_token_name,
    parse_keycode,
    vendor_basic_key_aliases,
)
from mini_keyboard_tool.ledcolors import canonical_led_swatches, parse_led_color, rgb_hex
from mini_keyboard_tool.protocol import (
    MODE_BASIC,
    BasicRemap,
    LedConfig,
    MouseRemap,
    SequenceRemap,
    build_basic_report,
    build_commit_report,
    build_led_report,
    build_media_report,
    build_mouse_report,
    build_sequence_report,
)


class ProtocolReportTests(unittest.TestCase):
    def test_basic_report_new_layout(self) -> None:
        report = build_basic_report(BasicRemap(physical_key=1, layer=0, keycode=0x1E))
        self.assertEqual(len(report), 65)
        self.assertEqual(report[:10], bytes.fromhex("03 fd 01 01 01 00 01 00 00 1e"))

    def test_sequence_report_with_delays(self) -> None:
        report = build_sequence_report(
            SequenceRemap(
                physical_key=2,
                layer=0,
                mode=MODE_BASIC,
                tokens=(0x04, 0x05, 0x06),
                delays=(100, 100, 100),
            )
        )
        self.assertEqual(len(report), 65)
        self.assertEqual(report[:16], bytes.fromhex("03 fd 02 01 01 00 03 00 64 04 00 64 05 00 64 06"))

    def test_media_report_uses_16_bit_consumer_usage(self) -> None:
        report = build_media_report(physical_key=2, layer=0, consumer_usage=0x0192)
        self.assertEqual(report[:13], bytes.fromhex("03 fd 02 01 02 00 02 00 00 92 00 00 01"))

    def test_mouse_report_ctrl_negative_wheel(self) -> None:
        report = build_mouse_report(
            MouseRemap(physical_key=2, layer=0, page=1, wheel_modifier=0xF1, wheel=-1)
        )
        self.assertEqual(report[:22], bytes.fromhex("03 fd 02 01 03 01 04 00 00 f1 00 00 00 00 00 00 00 00 00 00 00 ff"))

    def test_mouse_button_aliases_match_physical_hid_buttons(self) -> None:
        right = build_mouse_report(MouseRemap(physical_key=1, layer=0, **parse_mouse_action("right-click")))
        middle = build_mouse_report(MouseRemap(physical_key=2, layer=0, **parse_mouse_action("middle-click")))
        self.assertEqual(right[12], 0x02)
        self.assertEqual(middle[12], 0x04)

    def test_led_report(self) -> None:
        report = build_led_report(LedConfig(layer=0, mode=1, colors=((0xFF, 0, 0),) * 16))
        self.assertEqual(len(report), 65)
        self.assertEqual(report[:14], bytes.fromhex("03 fe b0 00 01 ff 00 00 ff 00 00 ff 00 00"))

    def test_commit_report(self) -> None:
        self.assertEqual(build_commit_report()[:4], bytes.fromhex("03 fd fe ff"))

    def test_macro_parser_modifier_chord(self) -> None:
        self.assertEqual(parse_macro_tokens("shift+a"), (0xF2, 0x04))

    def test_slot_list_parser_accepts_ranges_and_aliases(self) -> None:
        self.assertEqual(parse_key_slots("1..3,top-left,1"), (1, 2, 3, 16))
        self.assertEqual(_parse_gui_slot_list("3..1,bottom-click"), (3, 2, 1, 20))

    def test_read_config_parser_accepts_multiple_slots(self) -> None:
        args = build_parser().parse_args(
            ["read-config", "--key", "2", "--key", "top-click", "--keys", "4..5,2"]
        )
        self.assertEqual(args.key, [2, 17])
        self.assertEqual(args.keys, (4, 5, 2))
        self.assertEqual(_read_config_requested_keys(args), (2, 17, 4, 5))

    def test_clear_reports_build_empty_records_for_multiple_slots(self) -> None:
        args = argparse.Namespace(
            key=None,
            keys=(12, 16),
            tested_12key=False,
            include_knobs=False,
            layer=0,
            all_layers=False,
            variant="new",
            mode=MODE_BASIC,
            no_commit=False,
        )
        reports = _build_clear_reports(args)
        self.assertEqual(len(reports), 3)
        self.assertEqual(reports[0][0], "clear slot 12 layer 0")
        self.assertEqual(reports[0][1][:10], bytes.fromhex("03 fd 0c 01 01 00 00 00 00 00"))
        self.assertEqual(reports[1][1][:10], bytes.fromhex("03 fd 10 01 01 00 00 00 00 00"))
        self.assertEqual(reports[-1][1][:4], bytes.fromhex("03 fd fe ff"))

    def test_clear_command_dry_run_prints_empty_records(self) -> None:
        args = argparse.Namespace(
            key=[12],
            keys=None,
            tested_12key=False,
            include_knobs=False,
            layer=0,
            all_layers=False,
            variant="new",
            mode=MODE_BASIC,
            no_commit=True,
            write=False,
            yes=False,
        )
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = cmd_clear(args)
        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("Clear slots 12", output)
        self.assertIn("03 fd 0c 01 01", output)

    def test_remap_command_accepts_modifier_chord(self) -> None:
        args = argparse.Namespace(
            key=12,
            layer=0,
            to="shift+a",
            clear=False,
            variant="new",
            mode=MODE_BASIC,
            no_commit=True,
            write=False,
            yes=False,
        )
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = cmd_remap(args)
        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("set to keys shift+a", output)
        self.assertIn("03 fd 0c 01 01 00 02 00 00 f2 00 00 04", output)


class CliDryRunSmokeTests(unittest.TestCase):
    def run_cli(self, argv: list[str]) -> str:
        args = build_parser().parse_args(argv)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = args.func(args)
        self.assertEqual(exit_code, 0, argv)
        return buffer.getvalue()

    def test_write_capable_commands_default_to_dry_run(self) -> None:
        cases = (
            (["remap", "--key", "12", "--to", "shift+a", "--no-commit"], "remap token-list"),
            (["media", "--key", "top-left", "--to", "volume-down", "--no-commit"], "media"),
            (["mouse", "--key", "bottom-click", "--to", "left-click", "--no-commit"], "mouse"),
            (["macro", "--key", "2", "--steps", "a,b,c", "--delay", "100", "--no-commit"], "macro"),
            (["procreate", "--key", "2", "--action", "copy", "--no-commit"], "procreate"),
            (["led", "--layer", "0", "--mode", "mode2", "--color", "#ff00ff"], "led"),
            (["experiment", "--name", "macro-delay", "--key", "2", "--no-commit"], "macro-delay"),
            (["experiment", "--name", "raw-media", "--key", "3", "--no-commit"], "raw-media"),
            (["experiment", "--name", "modified-wheel", "--key", "4", "--no-commit"], "modified-wheel"),
            (["experiment", "--name", "swipe", "--key", "5", "--no-commit"], "swipe"),
            (["experiment", "--name", "led-mode", "--led-layer", "0"], "led-mode"),
        )
        for argv, expected in cases:
            with self.subTest(argv=argv):
                output = self.run_cli(argv)
                self.assertIn(expected, output)
                self.assertIn("Dry run only", output)

    def test_catalog_commands_have_expected_rows(self) -> None:
        cases = (
            (["keycodes", "--filter", "print"], "printscreen"),
            (["vendor-key-aliases", "--filter", "prt"], "PrtScSysRq"),
            (["media-codes", "--filter", "volume"], "volume-down"),
            (["mouse-actions", "--filter", "swipe"], "swipe-left"),
            (["vendor-models", "--handlers", "--filter", "12+2"], "Set_Keyboard_12add2"),
            (["procreate-actions", "--filter", "redo"], "shift+cmd+z"),
            (["led-modes"], "mode2"),
            (["led-colors", "--filter", "swatch-1"], "#ff0000"),
            (["slots"], "top-left=16"),
            (["experiments"], "macro-delay"),
        )
        for argv, expected in cases:
            with self.subTest(argv=argv):
                output = self.run_cli(argv)
                self.assertIn(expected, output)


class DecodeNameTests(unittest.TestCase):
    def test_keycode_and_usage_names_are_human_readable(self) -> None:
        self.assertEqual(keycode_name(0x04), "a")
        self.assertEqual(media_usage_name(0x00EA), "volume-down")
        self.assertEqual(modifier_token_name(0xF2), "shift")

    def test_vendor_basic_key_aliases_parse(self) -> None:
        self.assertEqual(parse_keycode("PrtScSysRq"), 0x46)
        self.assertEqual(parse_keycode("ScrLock"), 0x47)
        self.assertEqual(parse_keycode("ArrowsUp"), 0x52)
        self.assertEqual(parse_keycode("NUM1"), 0x1E)
        self.assertEqual(parse_keycode("M_NUM1"), 0x59)
        self.assertEqual(parse_keycode("ADD"), 0x57)
        self.assertEqual(parse_keycode("SubUnd"), 0x2D)
        self.assertEqual(parse_keycode("NULL"), 0x00)

    def test_vendor_basic_key_alias_catalog_matches_parser(self) -> None:
        aliases = vendor_basic_key_aliases()
        self.assertGreaterEqual(len(aliases), 80)
        for label, alias, code in aliases:
            self.assertEqual(parse_keycode(label), code)
            self.assertEqual(parse_keycode(alias), code)

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cmd_vendor_key_aliases(argparse.Namespace(filter="prt", json=False))
        output = buffer.getvalue()
        self.assertIn("PrtScSysRq", output)
        self.assertIn("0x46", output)

    def test_summary_decodes_modifier_chord(self) -> None:
        response = bytes.fromhex("03 fa 0c 01 01 00 02 00 00 f2 00 00 04")
        self.assertIn("keys=shift+a", _summarize_config_response(response))
        item = _config_response_to_dict(response)
        self.assertEqual(item["token_names"], ["shift", "a"])
        self.assertEqual(item["keys"], "shift+a")

    def test_summary_decodes_media_and_mouse_actions(self) -> None:
        media = bytes.fromhex("03 fa 10 01 02 00 02 00 00 ea 00 00 00")
        mouse = bytes.fromhex(
            "03 fa 13 01 03 01 04 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ff"
        )
        like = bytes.fromhex(
            "03 fa 13 01 03 04 04 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00"
        )
        self.assertIn("media=volume-down(0x00ea)", _summarize_config_response(media))
        self.assertIn("action=wheel-negative", _summarize_config_response(mouse))
        self.assertIn("action=like", _summarize_config_response(like))
        self.assertEqual(_config_response_to_dict(mouse)["mouse"]["action"], "wheel-negative")
        self.assertEqual(_config_response_to_dict(like)["mouse"]["action"], "like")
        self.assertIn("action=like", _summarize_gui_config_response(like))

    def test_summary_decodes_mouse_buttons(self) -> None:
        right = bytes.fromhex(
            "03 fa 01 01 03 01 04 00 00 00 00 00 02 00 00 00 00 00 00 00 00 00"
        )
        middle = bytes.fromhex(
            "03 fa 02 01 03 01 04 00 00 00 00 00 04 00 00 00 00 00 00 00 00 00"
        )
        self.assertIn("action=right-click", _summarize_config_response(right))
        self.assertIn("action=middle-click", _summarize_config_response(middle))
        self.assertIn("action=right-click", _summarize_gui_config_response(right))
        self.assertIn("action=middle-click", _summarize_gui_config_response(middle))


    def test_vendor_led_swatch_aliases(self) -> None:
        self.assertEqual(parse_led_color("swatch-1"), (255, 0, 0))
        self.assertEqual(parse_led_color("LED_color_56"), (200, 200, 150))
        self.assertEqual(rgb_hex(parse_led_color("orange")), "#ffa500")
        self.assertGreaterEqual(len(canonical_led_swatches()), 50)


class VendorCatalogTests(unittest.TestCase):
    def test_vendor_model_catalog_contains_tested_model(self) -> None:
        self.assertIn("12+2KEY", VENDOR_MODELS)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cmd_vendor_models(argparse.Namespace(filter="12", json=False))
        self.assertIn("12+2KEY", buffer.getvalue())

    def test_vendor_model_handlers_include_connected_board(self) -> None:
        handlers = vendor_model_handlers()
        connected = [row for row in handlers if row["model"] == "12+2KEY"]
        self.assertEqual(len(connected), 1)
        self.assertEqual(connected[0]["handler"], "Widget::Set_Keyboard_12add2()")
        self.assertTrue(connected[0]["public"])
        self.assertIn("physically tested", str(connected[0]["note"]))

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cmd_vendor_models(argparse.Namespace(filter="12+2", json=False, handlers=True))
        output = buffer.getvalue()
        self.assertIn("12+2KEY", output)
        self.assertIn("Set_Keyboard_12add2", output)

    def test_procreate_catalog_contains_vendor_labels(self) -> None:
        slugs = {slug for slug, _ in PROCREATE_ACTIONS}
        self.assertIn("quick-menu", slugs)
        self.assertIn("cut", slugs)
        self.assertIn("undo", slugs)
        self.assertIn("redo", slugs)
        self.assertNotIn("m-ios17", slugs)
        self.assertEqual(PROCREATE_PRESET_BY_SLUG["copy"][1], (0xF4, 0x06))
        self.assertEqual(PROCREATE_PRESET_BY_SLUG["redo"][1], (0xF2, 0xF4, 0x1D))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cmd_procreate_actions(argparse.Namespace(filter="brush", json=False))
        output = buffer.getvalue()
        self.assertIn("brush-tool", output)
        self.assertIn("static-vendor", output)

    def test_procreate_command_builds_static_vendor_preset(self) -> None:
        args = argparse.Namespace(
            key=2,
            layer=0,
            action="copy",
            variant="new",
            record_mode=MODE_BASIC,
            no_commit=True,
            write=False,
            yes=False,
        )
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = cmd_procreate(args)
        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("Expanded tokens: 0xf4 0x06", output)
        self.assertIn("cmd+c", output)


class SnapshotRestoreTests(unittest.TestCase):
    def test_config_restore_rewrites_read_response_to_write_report(self) -> None:
        item = {
            "raw": "03 fa 0c 01 01 00 02 00 00 f2 00 00 04"
        }
        report = _config_report_from_snapshot_item(item)
        self.assertEqual(len(report), 65)
        self.assertEqual(report[:13], bytes.fromhex("03 fd 0c 01 01 00 02 00 00 f2 00 00 04"))

    def test_led_restore_builds_led_report(self) -> None:
        item = {
            "layer": 1,
            "mode": 2,
            "colors": ["#00ff00"] * 16,
        }
        report = _led_report_from_snapshot_item(item)
        self.assertEqual(len(report), 65)
        self.assertEqual(report[:11], bytes.fromhex("03 fe b0 01 02 00 ff 00 00 ff 00"))


class SnapshotDiffTests(unittest.TestCase):
    def test_config_diff_reports_changed_raw_record(self) -> None:
        args = argparse.Namespace(key=None, layer=None)
        before = {
            "config": [
                {
                    "slot": 12,
                    "layer": 0,
                    "raw": "03 fa 0c 01 01 00 01 00 00 2e",
                    "summary": "slot 12 layer 0 equals",
                }
            ]
        }
        after = {
            "config": [
                {
                    "slot": 12,
                    "layer": 0,
                    "raw": "03 fa 0c 01 01 00 02 00 00 f2 00 00 04",
                    "summary": "slot 12 layer 0 shift+a",
                }
            ]
        }
        lines = _diff_snapshot_config(before, after, args)
        self.assertIn("~ config slot 12 layer 0:", lines)
        self.assertTrue(any("shift+a" in line for line in lines))

    def test_config_diff_semantic_ignores_media_page_normalization(self) -> None:
        args = argparse.Namespace(key=None, layer=None, semantic=True)
        before = {
            "config": [
                _config_response_to_dict(
                    bytes.fromhex(
                        "03 fa 01 01 02 01 02 00 00 b4 00 00 00"
                    )
                )
            ]
        }
        after = {
            "config": [
                _config_response_to_dict(
                    bytes.fromhex(
                        "03 fa 01 01 02 00 02 00 00 b4 00 00 00"
                    )
                )
            ]
        }
        self.assertEqual(_diff_snapshot_config(before, after, args), [])

    def test_config_diff_raw_still_reports_media_page_normalization(self) -> None:
        args = argparse.Namespace(key=None, layer=None, semantic=False)
        before = {
            "config": [
                _config_response_to_dict(
                    bytes.fromhex(
                        "03 fa 01 01 02 01 02 00 00 b4 00 00 00"
                    )
                )
            ]
        }
        after = {
            "config": [
                _config_response_to_dict(
                    bytes.fromhex(
                        "03 fa 01 01 02 00 02 00 00 b4 00 00 00"
                    )
                )
            ]
        }
        lines = _diff_snapshot_config(before, after, args)
        self.assertIn("~ config slot 01 layer 0:", lines)

    def test_led_diff_reports_mode_or_color_change(self) -> None:
        args = argparse.Namespace(led_layers=None)
        before = {"led": [{"layer": 0, "mode": 1, "colors": ["#ff0000"] * 16}]}
        after = {"led": [{"layer": 0, "mode": 2, "colors": ["#00ff00"] * 16}]}
        lines = _diff_snapshot_led(before, after, args)
        self.assertIn("~ LED layer 0:", lines)
        self.assertTrue(any("mode 2" in line for line in lines))


class ExperimentPresetTests(unittest.TestCase):
    def test_macro_delay_experiment_builds_delayed_macro(self) -> None:
        args = argparse.Namespace(
            name="macro-delay",
            key=2,
            layer=0,
            variant="new",
            steps="a,b,c",
            delay=250,
            no_commit=False,
            usage="0x0192",
            action="ctrl-wheel-negative",
            led_layer=0,
            mode=2,
            color="#ff0000",
            commit_led=False,
        )
        reports, instruction = _build_experiment_reports(args)
        self.assertEqual(len(reports), 2)
        self.assertIn("a, b, c", instruction)
        self.assertEqual(reports[0][1][:16], bytes.fromhex("03 fd 02 01 01 00 03 00 fa 04 00 fa 05 00 fa 06"))

    def test_swipe_experiment_defaults_to_swipe_left(self) -> None:
        args = argparse.Namespace(
            name="swipe",
            key=2,
            layer=0,
            variant="new",
            steps="a,b,c",
            delay=250,
            no_commit=True,
            usage="0x0192",
            action="ctrl-wheel-negative",
            led_layer=0,
            mode=2,
            color="#ff0000",
            commit_led=False,
        )
        reports, _ = _build_experiment_reports(args)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0][1][:10], bytes.fromhex("03 fd 02 01 03 04 04 00 00 02"))


class TestPlanTests(unittest.TestCase):
    def _args(self, **overrides: object) -> argparse.Namespace:
        values = {
            "key": 2,
            "layer": 0,
            "snapshot": Path("snapshots/before.json"),
            "command_prefix": "uv run python -m mini_keyboard_tool",
            "usage": "0x0192",
            "modified_wheel_action": "ctrl-wheel-negative",
            "swipe_action": "swipe-left",
            "led_layer": 0,
            "led_mode": "mode2",
            "led_color": "swatch-1",
            "no_led": False,
            "json": False,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_test_plan_contains_safe_loop_and_remaining_experiments(self) -> None:
        plan = _build_test_plan(self._args())
        steps = plan["steps"]
        self.assertIsInstance(steps, list)
        text = "\n".join(str(step) for step in steps)
        self.assertIn("snapshot --json snapshots/before.json", text)
        self.assertIn("experiment --name macro-delay --key 2 --layer 0", text)
        self.assertIn("experiment --name swipe --key 2 --layer 0 --action like", text)
        self.assertIn("experiment --name swipe --key 2 --layer 0 --action swipe-left", text)
        self.assertIn("restore-snapshot --json snapshots/before.json --key 2 --layer 0", text)
        self.assertIn("experiment --name led-mode --led-layer 0 --mode mode2 --color swatch-1", text)

    def test_test_plan_can_omit_led_probe(self) -> None:
        plan = _build_test_plan(self._args(no_led=True))
        text = "\n".join(str(step) for step in plan["steps"])
        self.assertNotIn("led-mode", text)
        self.assertIn("verify-current --no-led", text)

    def test_cmd_test_plan_json_prints_plan_without_writing(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = cmd_test_plan(self._args(json=True))
        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn('"steps"', output)
        self.assertIn("--write --yes", output)


class ProfilePresetTests(unittest.TestCase):
    def test_verified_controls_profile_builds_known_reports(self) -> None:
        args = argparse.Namespace(
            name="verified-controls",
            no_config=False,
            no_led=False,
            no_commit=False,
        )
        reports, config_count = _build_profile_reports(args)
        self.assertEqual(config_count, 7)
        self.assertEqual(len(reports), 11)
        self.assertEqual(reports[0][1][:13], bytes.fromhex("03 fd 0c 01 01 00 02 00 00 f2 00 00 04"))
        self.assertEqual(reports[1][1][:13], bytes.fromhex("03 fd 10 01 02 00 02 00 00 ea 00 00 00"))
        self.assertEqual(reports[-1][1][:4], bytes.fromhex("03 fd fe ff"))

    def test_tested_12key_profile_includes_slot_two_baseline(self) -> None:
        args = argparse.Namespace(
            name="tested-12key-baseline",
            no_config=False,
            no_led=True,
            no_commit=False,
        )
        reports, config_count = _build_profile_reports(args)
        self.assertEqual(config_count, 18)
        self.assertEqual(len(reports), 19)
        self.assertEqual(reports[1][1][:10], bytes.fromhex("03 fd 02 01 01 00 01 00 00 1f"))


class VerifyProfileTests(unittest.TestCase):
    def test_known_tested_profile_passes(self) -> None:
        snapshot = {
            "config": [
                {"slot": 12, "layer": 0, "mode": 1, "tokens": [0xF2, 0x04], "summary": "ok"},
                {"slot": 16, "layer": 0, "mode": 2, "media": {"usage": 0x00EA}, "summary": "ok"},
                {"slot": 17, "layer": 0, "mode": 2, "media": {"usage": 0x00E2}, "summary": "ok"},
                {"slot": 18, "layer": 0, "mode": 2, "media": {"usage": 0x00E9}, "summary": "ok"},
                {
                    "slot": 19,
                    "layer": 0,
                    "mode": 3,
                    "page": 1,
                    "mouse": {"button": 0, "wheel_modifier": 0, "wheel": -1},
                    "summary": "ok",
                },
                {
                    "slot": 20,
                    "layer": 0,
                    "mode": 3,
                    "page": 1,
                    "mouse": {"button": 1, "wheel_modifier": 0, "wheel": 0},
                    "summary": "ok",
                },
                {
                    "slot": 21,
                    "layer": 0,
                    "mode": 3,
                    "page": 1,
                    "mouse": {"button": 0, "wheel_modifier": 0, "wheel": 1},
                    "summary": "ok",
                },
            ],
            "led": [
                {"layer": 0, "mode": 1, "colors": ["#ff0000"] * 16, "summary": "ok"},
                {"layer": 1, "mode": 1, "colors": ["#00ff00"] * 16, "summary": "ok"},
                {"layer": 2, "mode": 1, "colors": ["#0000ff"] * 16, "summary": "ok"},
            ],
        }
        results = _verify_tested_profile(snapshot)
        self.assertTrue(all(ok for ok, _, _ in results))

    def test_known_tested_profile_reports_failure(self) -> None:
        snapshot = {
            "config": [
                {"slot": 12, "layer": 0, "mode": 1, "tokens": [0x04], "summary": "wrong"},
            ],
            "led": [],
        }
        results = _verify_tested_profile(snapshot, include_led=False)
        self.assertFalse(results[0][0])
        self.assertIn("tokens expected", results[0][2])


if __name__ == "__main__":
    unittest.main()
