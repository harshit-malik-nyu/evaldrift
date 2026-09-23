"""
Command line interface.

The CLI is the only part of this project another team would run in their own
pipeline, and the exit code is the part that matters: it is what lets a build
fail when someone reports an improvement their benchmark cannot resolve.
"""

from __future__ import annotations

import json

import pytest

from evaldrift.cli import main


class TestTable:

    def test_prints_every_benchmark(self, capsys):
        assert main(["table"]) == 0
        out = capsys.readouterr().out
        for name in ("HumanEval", "GPQA Diamond", "MMLU"):
            assert name in out

    def test_reports_how_many_fail(self, capsys):
        main(["table"])
        assert "cannot distinguish" in capsys.readouterr().out

    def test_json_output_is_parseable(self, capsys):
        assert main(["--json", "table"]) == 0
        rows = json.loads(capsys.readouterr().out)
        assert len(rows) >= 9
        assert "min_detectable_effect" in rows[0]

    def test_effect_size_is_configurable(self, capsys):
        main(["table", "--effect", "0.20"])
        out = capsys.readouterr().out
        assert "20%" in out


class TestCheck:

    def test_exits_nonzero_on_an_unsupportable_claim(self):
        """
        The behaviour that makes this usable as a CI gate: a build should fail
        when a reported improvement exceeds what the benchmark can resolve.
        """
        assert main(["check", "0.02", "198"]) == 1

    def test_exits_zero_on_a_supportable_claim(self):
        assert main(["check", "0.25", "198"]) == 0

    def test_explains_the_shortfall(self, capsys):
        main(["check", "0.02", "198"])
        out = capsys.readouterr().out
        assert "NOT SUPPORTABLE" in out
        assert "would be required" in out

    def test_json_carries_the_verdict_and_the_gap(self, capsys):
        main(["--json", "check", "0.02", "198"])
        d = json.loads(capsys.readouterr().out)
        assert d["supportable"] is False
        assert d["items_needed"] > 198


class TestResolution:

    def test_reports_interval_and_detectable_effect(self, capsys):
        assert main(["resolution", "500"]) == 0
        out = capsys.readouterr().out
        assert "interval on one score" in out
        assert "smallest detectable change" in out

    def test_states_that_these_are_lower_bounds(self, capsys):
        """
        Omitting this would overstate what the tool measures — the figures are
        sampling bounds only, and prompt and scoring variance widen them.
        """
        main(["resolution", "500"])
        assert "lower bound" in capsys.readouterr().out

    def test_discordance_changes_the_paired_figure(self, capsys):
        main(["--json", "resolution", "500", "--discordance", "0.10"])
        tight = json.loads(capsys.readouterr().out)
        main(["--json", "resolution", "500", "--discordance", "0.40"])
        loose = json.loads(capsys.readouterr().out)
        assert (tight["paired_min_detectable_effect"]
                < loose["paired_min_detectable_effect"])


class TestArgumentHandling:

    def test_a_subcommand_is_required(self):
        with pytest.raises(SystemExit):
            main([])

    def test_unknown_subcommand_exits(self):
        with pytest.raises(SystemExit):
            main(["nonsense"])
