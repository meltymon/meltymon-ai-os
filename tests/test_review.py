"""Tests for the MELTYMON AI OS review cockpit."""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts import review

# ---------------------------------------------------------------------------
# run_check
# ---------------------------------------------------------------------------


def test_run_check_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        review.subprocess,
        "run",
        lambda *args, **kwargs: MagicMock(returncode=0, stdout="OK\n"),
    )

    result = review.run_check("Example", ["example"])

    assert result.status == "PASS"
    assert result.name == "Example"
    assert result.output == "OK"
    assert result.command == "example"


def test_run_check_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        review.subprocess,
        "run",
        lambda *args, **kwargs: MagicMock(returncode=1, stdout="Error"),
    )

    result = review.run_check("Example", ["example"])

    assert result.status == "FAIL"
    assert result.output == "Error"


def test_run_check_missing_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_missing(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(review.subprocess, "run", raise_missing)

    result = review.run_check("Example", ["missing"])

    assert result.status == "SKIP"
    assert "nicht gefunden" in result.note


def test_run_check_timeout_with_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(
            cmd="example",
            timeout=10,
            output=b"Partial output",
        )

    monkeypatch.setattr(review.subprocess, "run", raise_timeout)

    result = review.run_check("Example", ["example"], timeout=10)

    assert result.status == "FAIL"
    assert result.output == "Partial output"
    assert "10 Sekunden" in result.note


def test_run_check_timeout_with_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(
            cmd="example",
            timeout=10,
            output="Partial output",
        )

    monkeypatch.setattr(review.subprocess, "run", raise_timeout)

    result = review.run_check("Example", ["example"], timeout=10)

    assert result.status == "FAIL"
    assert result.output == "Partial output"


def test_run_check_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_os_error(*args: object, **kwargs: object) -> None:
        raise OSError("Permission denied")

    monkeypatch.setattr(review.subprocess, "run", raise_os_error)

    result = review.run_check("Example", ["example"])

    assert result.status == "FAIL"
    assert "Permission denied" in result.note


def test_run_check_truncates_large_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(review, "OUTPUT_LIMIT", 10)
    monkeypatch.setattr(
        review.subprocess,
        "run",
        lambda *args, **kwargs: MagicMock(
            returncode=0,
            stdout="A" * 30,
        ),
    )

    result = review.run_check("Example", ["example"])

    assert result.status == "PASS"
    assert "[Output gekürzt]" in result.output
    assert len(result.output) > 10


# ---------------------------------------------------------------------------
# git_output and collect_git_summary
# ---------------------------------------------------------------------------


def test_git_output_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        review.subprocess,
        "run",
        lambda *args, **kwargs: MagicMock(
            returncode=0,
            stdout="branch output\n",
        ),
    )

    output, result = review.git_output("status", "--short")

    assert output == "branch output"
    assert result.status == "PASS"
    assert result.output == ""


def test_git_output_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        review.subprocess,
        "run",
        lambda *args, **kwargs: MagicMock(
            returncode=128,
            stdout="fatal: not a repository",
        ),
    )

    output, result = review.git_output("status")

    assert output == "fatal: not a repository"
    assert result.status == "FAIL"
    assert result.output == "fatal: not a repository"


def test_git_output_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(
            cmd="git status",
            timeout=60,
            output=b"Partial Git output",
        )

    monkeypatch.setattr(review.subprocess, "run", raise_timeout)

    output, result = review.git_output("status")

    assert output == ""
    assert result.status == "FAIL"
    assert result.output == "Partial Git output"


def test_git_output_timeout_without_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(
            cmd="git status",
            timeout=60,
            output=None,
        )

    monkeypatch.setattr(review.subprocess, "run", raise_timeout)

    output, result = review.git_output("status")

    assert output == ""
    assert result.status == "FAIL"
    assert result.output == ""


def test_git_output_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_os_error(*args: object, **kwargs: object) -> None:
        raise OSError("Git unavailable")

    monkeypatch.setattr(review.subprocess, "run", raise_os_error)

    output, result = review.git_output("status")

    assert output == ""
    assert result.status == "FAIL"
    assert "Git unavailable" in result.note


def test_collect_git_summary_collects_all_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outputs = iter(
        [
            "## main",
            "2 files changed",
            "1 file changed",
            "new_file.py\0another_file.py\0",
        ]
    )

    def fake_git_output(*args: str) -> tuple[str, review.CheckResult]:
        return next(outputs), review.CheckResult(
            name="Git test",
            status="PASS",
        )

    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        return review.CheckResult(name=name, status="PASS")

    monkeypatch.setattr(review, "git_output", fake_git_output)
    monkeypatch.setattr(review, "run_check", fake_run_check)
    monkeypatch.setattr(
        review,
        "check_untracked_whitespace",
        lambda untracked: review.CheckResult(
            name="Whitespace-Prüfung (neue Dateien)", status="PASS"
        ),
    )

    summary, results = review.collect_git_summary()

    assert "Nicht versionierte Dateien: 2" in summary
    assert len(results) == 7
    assert all(result.status == "PASS" for result in results)


# ---------------------------------------------------------------------------
# Security checks
# ---------------------------------------------------------------------------


def test_security_checks_skip_dependency_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        calls.append((name, command))
        return review.CheckResult(name=name, status="PASS")

    monkeypatch.setattr(review, "run_check", fake_run_check)

    results: list[review.CheckResult] = []
    review.add_security_checks(results, audit_dependencies=False)

    assert len(calls) == 1
    assert "bandit" in calls[0][1]
    assert len(results) == 2
    assert results[1].status == "SKIP"
    assert "pip-audit" in results[1].name


def test_security_checks_enable_dependency_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        calls.append(command)
        return review.CheckResult(name=name, status="PASS")

    monkeypatch.setattr(review, "run_check", fake_run_check)

    results: list[review.CheckResult] = []
    review.add_security_checks(results, audit_dependencies=True)

    assert len(calls) == 2
    assert any("bandit" in command for command in calls)
    assert any("pip_audit" in command for command in calls)
    assert all(result.status == "PASS" for result in results)


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


def test_read_coverage_calculates_statement_and_branch_coverage(
    tmp_path: Path,
) -> None:
    coverage_file = tmp_path / "coverage.json"
    coverage_file.write_text(
        json.dumps(
            {
                "totals": {
                    "num_statements": 100,
                    "covered_lines": 95,
                    "missing_lines": 5,
                    "num_branches": 40,
                    "missing_branches": 4,
                }
            }
        ),
        encoding="utf-8",
    )

    metrics = review.read_coverage(coverage_file)

    assert metrics["statement_coverage"] == 95.0
    assert metrics["branch_coverage"] == 90.0
    assert metrics["statements"] == 100
    assert metrics["missing_statements"] == 5
    assert metrics["branches"] == 40
    assert metrics["missing_branches"] == 4


def test_read_coverage_without_branches(tmp_path: Path) -> None:
    coverage_file = tmp_path / "coverage.json"
    coverage_file.write_text(
        json.dumps(
            {
                "totals": {
                    "num_statements": 10,
                    "covered_lines": 10,
                    "missing_lines": 0,
                }
            }
        ),
        encoding="utf-8",
    )

    metrics = review.read_coverage(coverage_file)

    assert metrics["statement_coverage"] == 100.0
    assert "branch_coverage" not in metrics


def test_read_coverage_with_zero_statements(tmp_path: Path) -> None:
    coverage_file = tmp_path / "coverage.json"
    coverage_file.write_text(
        json.dumps(
            {
                "totals": {
                    "num_statements": 0,
                    "covered_lines": 0,
                    "missing_lines": 0,
                }
            }
        ),
        encoding="utf-8",
    )

    metrics = review.read_coverage(coverage_file)

    assert metrics["statement_coverage"] == 100.0


@pytest.mark.parametrize(
    "content",
    [
        "{invalid json",
        "{}",
        '{"totals": null}',
        '{"totals": {"num_statements": "invalid"}}',
    ],
)
def test_read_coverage_invalid_data(
    tmp_path: Path,
    content: str,
) -> None:
    coverage_file = tmp_path / "coverage.json"
    coverage_file.write_text(content, encoding="utf-8")

    metrics = review.read_coverage(coverage_file)

    assert "coverage_error" in metrics


def test_read_coverage_missing_file(tmp_path: Path) -> None:
    metrics = review.read_coverage(tmp_path / "missing.json")

    assert "coverage_error" in metrics


# ---------------------------------------------------------------------------
# Wheel and build
# ---------------------------------------------------------------------------


def test_wheel_smoke_test_stops_after_failed_install(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        calls.append(name)
        return review.CheckResult(name=name, status="FAIL")

    monkeypatch.setattr(review, "run_check", fake_run_check)

    result = review.wheel_smoke_test(
        tmp_path / "package.whl",
        tmp_path / "target",
        tmp_path,
    )

    assert result.status == "FAIL"
    assert calls == ["Wheel-Installation"]


def test_wheel_smoke_test_runs_import_after_install(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        calls.append((name, kwargs))
        return review.CheckResult(name=name, status="PASS")

    monkeypatch.setattr(review, "run_check", fake_run_check)

    result = review.wheel_smoke_test(
        tmp_path / "package.whl",
        tmp_path / "target",
        tmp_path,
    )

    assert result.status == "PASS"
    assert [name for name, _ in calls] == [
        "Wheel-Installation",
        "Wheel-Import-Smoke-Test",
    ]
    assert calls[1][1]["cwd"] == tmp_path

    env = calls[1][1]["env"]
    assert isinstance(env, dict)
    assert "PYTHONPATH" in env


def test_run_build_checks_skips_after_failed_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        calls.append(name)
        return review.CheckResult(name=name, status="FAIL")

    monkeypatch.setattr(review, "run_check", fake_run_check)

    results: list[review.CheckResult] = []
    review.run_build_checks(results, tmp_path)

    assert calls == ["Python-Paketbuild"]
    assert len(results) == 2
    assert results[0].status == "FAIL"
    assert results[1].status == "SKIP"


def test_run_build_checks_success_with_wheel_and_twine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        if name == "Python-Paketbuild":
            dist_dir = Path(command[command.index("--outdir") + 1])
            dist_dir.mkdir(parents=True)
            (dist_dir / "package.whl").write_bytes(b"wheel")
            (dist_dir / "package.tar.gz").write_bytes(b"source")

        return review.CheckResult(name=name, status="PASS")

    wheel_calls: list[Path] = []

    def fake_wheel_smoke_test(
        wheel: Path,
        target_dir: Path,
        temp_dir: Path,
    ) -> review.CheckResult:
        wheel_calls.append(wheel)
        return review.CheckResult(
            name="Wheel-Import-Smoke-Test",
            status="PASS",
        )

    monkeypatch.setattr(review, "run_check", fake_run_check)
    monkeypatch.setattr(review, "wheel_smoke_test", fake_wheel_smoke_test)
    monkeypatch.setattr(review.shutil, "which", lambda name: "/usr/bin/twine")

    results: list[review.CheckResult] = []
    review.run_build_checks(results, tmp_path)

    assert len(results) == 3
    assert all(result.status == "PASS" for result in results)
    assert len(wheel_calls) == 1
    assert wheel_calls[0].name == "package.whl"
    assert results[2].name == "Twine-Metadatenprüfung"


def test_run_build_checks_without_wheel_or_twine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        if name == "Python-Paketbuild":
            dist_dir = Path(command[command.index("--outdir") + 1])
            dist_dir.mkdir(parents=True)
            (dist_dir / "package.tar.gz").write_bytes(b"source")

        return review.CheckResult(name=name, status="PASS")

    monkeypatch.setattr(review, "run_check", fake_run_check)
    monkeypatch.setattr(review.shutil, "which", lambda name: None)

    results: list[review.CheckResult] = []
    review.run_build_checks(results, tmp_path)

    assert len(results) == 3
    assert results[0].status == "PASS"
    assert results[1].status == "FAIL"
    assert results[2].status == "SKIP"


# ---------------------------------------------------------------------------
# Command-line arguments
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (
            [],
            Namespace(
                quick=False,
                no_build=False,
                no_security=False,
                audit_dependencies=False,
                no_report=False,
            ),
        ),
        (
            ["--quick"],
            Namespace(
                quick=True,
                no_build=False,
                no_security=False,
                audit_dependencies=False,
                no_report=False,
            ),
        ),
        (
            ["--no-build", "--no-security", "--no-report"],
            Namespace(
                quick=False,
                no_build=True,
                no_security=True,
                audit_dependencies=False,
                no_report=True,
            ),
        ),
    ],
)
def test_parse_args(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
    expected: Namespace,
) -> None:
    monkeypatch.setattr("sys.argv", ["review.py", *arguments])

    args = review.parse_args()

    assert vars(args) == vars(expected)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--quick", "--audit-dependencies"],
        ["--no-security", "--audit-dependencies"],
    ],
)
def test_parse_args_rejects_conflicting_options(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
) -> None:
    monkeypatch.setattr("sys.argv", ["review.py", *arguments])

    with pytest.raises(SystemExit) as exc_info:
        review.parse_args()

    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def test_render_report_summarizes_results() -> None:
    results = [
        review.CheckResult(
            name="Lint",
            status="PASS",
            duration=0.25,
            command="ruff check",
            output="This output should not appear.",
        ),
        review.CheckResult(
            name="Tests",
            status="FAIL",
            duration=1.5,
            command="pytest",
            output="Test failed",
            note="Failure details",
        ),
        review.CheckResult(
            name="Security",
            status="SKIP",
            note="Not enabled",
        ),
    ]

    report = review.render_report(
        results,
        "Branch/Status:\n## main",
        {
            "statement_coverage": 96.85,
            "branch_coverage": 91.67,
            "statements": 100,
            "missing_statements": 3,
            "branches": 40,
            "missing_branches": 3,
        },
        "full",
    )

    assert "**FAIL**" in report
    assert "PASS: 1" in report
    assert "FAIL: 1" in report
    assert "SKIP: 1" in report
    assert "96.85%" in report
    assert "91.67%" in report
    assert "Test failed" in report
    assert "This output should not appear." not in report
    assert "Not enabled" in report
    assert "Git-Übersicht" in report


def test_render_report_pass_with_skips() -> None:
    report = review.render_report(
        [
            review.CheckResult(name="Lint", status="PASS"),
            review.CheckResult(name="Audit", status="SKIP"),
        ],
        "Git status",
        {},
        "full",
    )

    assert "**PASS WITH SKIPS**" in report


def test_render_report_pass_without_skips() -> None:
    report = review.render_report(
        [review.CheckResult(name="Lint", status="PASS")],
        "Git status",
        {},
        "quick",
    )

    assert "**PASS**" in report


def test_render_report_includes_coverage_error() -> None:
    report = review.render_report(
        [review.CheckResult(name="Lint", status="PASS")],
        "Git status",
        {"coverage_error": "Coverage-JSON konnte nicht gelesen werden."},
        "full",
    )

    assert "## Coverage" in report
    assert "Coverage-JSON konnte nicht gelesen werden." in report


# ---------------------------------------------------------------------------
# Extended run_checks orchestration tests
# ---------------------------------------------------------------------------


def test_run_checks_quick_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        calls.append(name)
        return review.CheckResult(name=name, status="PASS")

    monkeypatch.setattr(review, "run_check", fake_run_check)

    results: list[review.CheckResult] = []
    metrics = review.run_checks(
        results,
        quick=True,
        no_build=False,
        no_security=False,
        audit_dependencies=False,
    )

    assert len(results) == 3
    assert calls == ["Ruff Lint", "Ruff Format", "Mypy"]
    assert metrics == {}


def test_run_checks_full_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        if name == "Pytest + Branch-Coverage":
            coverage_arg = next(
                arg for arg in command if arg.startswith("--cov-report=json:")
            )
            coverage_file = Path(coverage_arg.removeprefix("--cov-report=json:"))
            coverage_file.write_text(
                json.dumps(
                    {
                        "totals": {
                            "num_statements": 100,
                            "covered_lines": 95,
                            "missing_lines": 5,
                            "num_branches": 40,
                            "missing_branches": 4,
                        }
                    }
                ),
                encoding="utf-8",
            )
        return review.CheckResult(name=name, status="PASS")

    monkeypatch.setattr(review, "run_check", fake_run_check)
    monkeypatch.setattr(review, "add_security_checks", lambda *args, **kwargs: None)
    monkeypatch.setattr(review, "run_build_checks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        review.tempfile,
        "TemporaryDirectory",
        lambda **kwargs: __import__("contextlib").nullcontext(str(tmp_path)),
    )

    results: list[review.CheckResult] = []
    metrics = review.run_checks(
        results,
        quick=False,
        no_build=False,
        no_security=False,
        audit_dependencies=False,
    )

    assert len(results) == 4
    assert all(result.status == "PASS" for result in results)
    assert metrics["statement_coverage"] == 95.0
    assert metrics["branch_coverage"] == 90.0


def test_run_checks_skips_security_and_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        return review.CheckResult(name=name, status="PASS")

    monkeypatch.setattr(review, "run_check", fake_run_check)

    results: list[review.CheckResult] = []
    metrics = review.run_checks(
        results,
        quick=False,
        no_build=True,
        no_security=True,
        audit_dependencies=False,
    )

    assert len(results) == 7
    assert results[0].name == "Ruff Lint"
    assert results[3].name == "Pytest + Branch-Coverage"
    assert results[4].status == "FAIL"
    assert results[4].name == "Coverage-Bericht"
    assert results[5].status == "SKIP"
    assert results[5].name == "Optionale Sicherheitsprüfungen"
    assert results[6].status == "SKIP"
    assert results[6].name == "Build und Wheel-Smoke-Test"
    assert metrics.get("coverage_error") == ("Kein Coverage-JSON-Bericht erzeugt.")


def test_run_checks_records_missing_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_check(
        name: str,
        command: list[str],
        **kwargs: object,
    ) -> review.CheckResult:
        return review.CheckResult(name=name, status="PASS")

    monkeypatch.setattr(review, "run_check", fake_run_check)

    results: list[review.CheckResult] = []
    metrics = review.run_checks(
        results,
        quick=False,
        no_build=True,
        no_security=True,
        audit_dependencies=False,
    )

    assert "coverage_error" in metrics


# ---------------------------------------------------------------------------
# Main entry point tests
# ---------------------------------------------------------------------------


def test_main_returns_zero_without_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = Namespace(
        quick=True,
        no_build=False,
        no_security=False,
        audit_dependencies=False,
        no_report=True,
    )

    monkeypatch.setattr(review, "parse_args", lambda: args)
    monkeypatch.setattr(
        review,
        "collect_git_summary",
        lambda: (
            "Git status",
            [review.CheckResult(name="Git", status="PASS")],
        ),
    )
    monkeypatch.setattr(
        review,
        "run_checks",
        lambda results, **kwargs: {},
    )

    exit_code = review.main()

    assert exit_code == 0
    assert "REVIEW (QUICK)" in capsys.readouterr().out


def test_main_returns_one_when_check_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = Namespace(
        quick=True,
        no_build=False,
        no_security=False,
        audit_dependencies=False,
        no_report=True,
    )

    monkeypatch.setattr(review, "parse_args", lambda: args)
    monkeypatch.setattr(
        review,
        "collect_git_summary",
        lambda: (
            "Git status",
            [review.CheckResult(name="Git", status="PASS")],
        ),
    )

    def fake_run_checks(
        results: list[review.CheckResult],
        **kwargs: object,
    ) -> dict[str, object]:
        results.append(
            review.CheckResult(
                name="Mock failure",
                status="FAIL",
            )
        )
        return {}

    monkeypatch.setattr(review, "run_checks", fake_run_checks)

    assert review.main() == 1


def test_main_writes_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = Namespace(
        quick=True,
        no_build=False,
        no_security=False,
        audit_dependencies=False,
        no_report=False,
    )

    monkeypatch.setattr(review, "ROOT", tmp_path)
    monkeypatch.setattr(review, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(review, "parse_args", lambda: args)
    monkeypatch.setattr(
        review,
        "collect_git_summary",
        lambda: (
            "Git status",
            [review.CheckResult(name="Git", status="PASS")],
        ),
    )
    monkeypatch.setattr(
        review,
        "run_checks",
        lambda results, **kwargs: {},
    )

    exit_code = review.main()

    reports = list((tmp_path / "reports").glob("review-*.md"))

    assert exit_code == 0
    assert len(reports) == 1
    assert "MELTYMON AI OS" in reports[0].read_text(encoding="utf-8")
    assert "Bericht:" in capsys.readouterr().out


def test_main_dependency_audit_and_coverage_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = Namespace(
        quick=False,
        no_build=True,
        no_security=False,
        audit_dependencies=True,
        no_report=True,
    )

    monkeypatch.setattr(review, "parse_args", lambda: args)
    monkeypatch.setattr(
        review,
        "collect_git_summary",
        lambda: (
            "Git status",
            [
                review.CheckResult(
                    name="Dependency Audit",
                    status="SKIP",
                    note="Audit nicht verfügbar.",
                )
            ],
        ),
    )
    monkeypatch.setattr(
        review,
        "run_checks",
        lambda results, **kwargs: {
            "statement_coverage": 96.85,
            "branch_coverage": 91.67,
        },
    )

    exit_code = review.main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "FULL + DEPENDENCY AUDIT" in output
    assert "Audit nicht verfügbar." in output
    assert "Statement-Coverage: 96.85%" in output
    assert "Branch-Coverage: 91.67%" in output
