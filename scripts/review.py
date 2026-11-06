#!/usr/bin/env python3
"""Read-only quality and security review cockpit for MELTYMON AI OS."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
REPORT_DIR = ROOT / "build" / "reports"
OUTPUT_LIMIT = 12_000


@dataclass
class CheckResult:
    name: str
    status: str
    command: str = ""
    duration: float = 0.0
    output: str = ""
    note: str = ""


def run_check(
    name: str,
    command: Sequence[str],
    *,
    timeout: int = 900,
    note: str = "",
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> CheckResult:
    """Execute one check without aborting the remaining review."""
    started = datetime.now(UTC)
    working_directory = cwd if cwd is not None else ROOT
    command_text = " ".join(command)

    try:
        completed = subprocess.run(
            list(command),
            cwd=working_directory,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        duration = (datetime.now(UTC) - started).total_seconds()
        output = completed.stdout or ""

        if len(output) > OUTPUT_LIMIT:
            output = output[-OUTPUT_LIMIT:] + "\n[Output gekürzt]"

        return CheckResult(
            name=name,
            status="PASS" if completed.returncode == 0 else "FAIL",
            command=command_text,
            duration=duration,
            output=output.strip(),
            note=note,
        )

    except FileNotFoundError:
        return CheckResult(
            name=name,
            status="SKIP",
            command=command_text,
            note="Werkzeug oder ausführbare Datei nicht gefunden.",
        )

    except subprocess.TimeoutExpired as exc:
        raw_output = exc.stdout
        if isinstance(raw_output, bytes):
            output = raw_output.decode(errors="replace")
        else:
            output = raw_output or ""

        return CheckResult(
            name=name,
            status="FAIL",
            command=command_text,
            duration=timeout,
            output=str(output)[-OUTPUT_LIMIT:],
            note=f"Zeitlimit von {timeout} Sekunden überschritten.",
        )

    except OSError as exc:
        return CheckResult(
            name=name,
            status="FAIL",
            command=command_text,
            duration=(datetime.now(UTC) - started).total_seconds(),
            note=f"Prozess konnte nicht gestartet werden: {exc}",
        )


def git_output(*args: str) -> tuple[str, CheckResult]:
    """Return Git output together with an explicit check result."""
    started = datetime.now(UTC)
    command = ["git", *args]
    command_text = " ".join(command)

    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=60,
        )
        duration = (datetime.now(UTC) - started).total_seconds()
        output = completed.stdout or ""

        if not args or args[0] != "ls-files":
            output = output.strip()

        result = CheckResult(
            name=f"Git {' '.join(args)}",
            status="PASS" if completed.returncode == 0 else "FAIL",
            command=command_text,
            duration=duration,
            output=output if completed.returncode != 0 else "",
            note=(
                ""
                if completed.returncode == 0
                else f"Git wurde mit Exit-Code {completed.returncode} beendet."
            ),
        )

        return output, result

    except subprocess.TimeoutExpired as exc:
        raw_output = exc.stdout
        if isinstance(raw_output, bytes):
            output = raw_output.decode(errors="replace")
        else:
            output = raw_output or ""

        return "", CheckResult(
            name=f"Git {' '.join(args)}",
            status="FAIL",
            command=command_text,
            duration=60,
            output=str(output)[-OUTPUT_LIMIT:],
            note="Git-Aufruf hat das Zeitlimit von 60 Sekunden überschritten.",
        )

    except OSError as exc:
        return "", CheckResult(
            name=f"Git {' '.join(args)}",
            status="FAIL",
            command=command_text,
            duration=(datetime.now(UTC) - started).total_seconds(),
            note=f"Git konnte nicht ausgeführt werden: {exc}",
        )


def check_untracked_whitespace(untracked: str) -> CheckResult:
    """Check untracked UTF-8 text files for trailing spaces and tabs."""
    issues: list[str] = []
    checked = 0
    skipped = 0

    for relative_path in untracked.split("\0"):
        if not relative_path:
            continue

        path = ROOT / relative_path

        try:
            content = path.read_bytes()
        except OSError as exc:
            return CheckResult(
                name="Whitespace-Prüfung (neue Dateien)",
                status="FAIL",
                note=f"Datei konnte nicht gelesen werden: {relative_path}: {exc}",
            )

        if b"\0" in content:
            skipped += 1
            continue

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            skipped += 1
            continue

        checked += 1
        is_markdown = path.name.casefold().endswith(
            (".md", ".markdown", ".md.new", ".markdown.new")
        )

        for line_number, line in enumerate(text.splitlines(), start=1):
            trailing = line[len(line.rstrip(" 	")) :]
            if not trailing:
                continue
            if is_markdown and len(trailing) >= 2 and set(trailing) == {" "}:
                continue
            issues.append(f"{relative_path}:{line_number}")

    if issues:
        return CheckResult(
            name="Whitespace-Prüfung (neue Dateien)",
            status="FAIL",
            output="\n".join(issues[:100]),
            note=(
                f"{len(issues)} Zeile(n) mit nachgestellten Leerzeichen "
                f"oder Tabs gefunden."
            ),
        )

    return CheckResult(
        name="Whitespace-Prüfung (neue Dateien)",
        status="PASS",
        note=(
            f"{checked} Textdatei(en) geprüft; "
            f"{skipped} Binär- oder Nicht-UTF-8-Datei(en) übersprungen."
        ),
    )


def collect_git_summary() -> tuple[str, list[CheckResult]]:
    """Collect repository state and verify whitespace in all changes."""
    results: list[CheckResult] = []

    status, status_result = git_output("status", "--short", "--branch")
    diff_stat, diff_result = git_output("diff", "--stat")
    staged_stat, staged_result = git_output("diff", "--cached", "--stat")
    untracked, untracked_result = git_output(
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    )

    results.extend(
        [
            status_result,
            diff_result,
            staged_result,
            untracked_result,
        ]
    )

    untracked_count = len([path for path in untracked.split("\0") if path])

    summary = (
        f"Branch/Status:\n{status or '(keine Ausgabe)'}\n\n"
        f"Änderungen (unstaged):\n{diff_stat or '(keine)'}\n\n"
        f"Änderungen (staged):\n{staged_stat or '(keine)'}\n\n"
        f"Nicht versionierte Dateien: {untracked_count}"
    )

    results.extend(
        [
            run_check(
                "Git-Diff-Integrität (unstaged)",
                ["git", "diff", "--check"],
                timeout=60,
            ),
            run_check(
                "Git-Diff-Integrität (staged)",
                ["git", "diff", "--cached", "--check"],
                timeout=60,
            ),
            check_untracked_whitespace(untracked),
        ]
    )

    return summary, results


def add_security_checks(
    results: list[CheckResult],
    *,
    audit_dependencies: bool,
) -> None:
    """Run local security analysis and optionally audit project dependencies."""
    results.append(
        run_check(
            "Bandit – statische Python-Sicherheitsanalyse",
            [
                PYTHON,
                "-m",
                "bandit",
                "-q",
                "-r",
                "src",
            ],
            timeout=300,
        )
    )

    if audit_dependencies:
        results.append(
            run_check(
                "pip-audit – Abhängigkeits-Schwachstellenscan",
                [
                    PYTHON,
                    "-m",
                    "pip_audit",
                    "--strict",
                    str(ROOT),
                ],
                timeout=900,
                note=(
                    "Explizit aktivierter Online-Abgleich mit "
                    "bekannten Python-Sicherheitsmeldungen."
                ),
            )
        )
    else:
        results.append(
            CheckResult(
                name="pip-audit – Abhängigkeits-Schwachstellenscan",
                status="SKIP",
                note=(
                    "Nicht aktiviert. Mit --audit-dependencies "
                    "wird der Online-Schwachstellenscan gestartet."
                ),
            )
        )


def read_coverage(path: Path) -> dict[str, object]:
    """Calculate statement and branch coverage separately."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        totals = data["totals"]

        statements = int(totals["num_statements"])
        covered_lines = int(totals["covered_lines"])
        missing_lines = int(totals["missing_lines"])

        branches = int(totals.get("num_branches", 0))
        missing_branches = int(totals.get("missing_branches", 0))

        if (
            min(statements, covered_lines, missing_lines, branches, missing_branches)
            < 0
        ):
            raise ValueError("Coverage-Werte dürfen nicht negativ sein.")

        if covered_lines + missing_lines != statements:
            raise ValueError("Coverage-Statement-Summen sind inkonsistent.")

        if missing_branches > branches:
            raise ValueError("Fehlende Branches überschreiten die Gesamtzahl.")

        statement_coverage = covered_lines / statements * 100 if statements else 100.0

        metrics: dict[str, object] = {
            "statement_coverage": statement_coverage,
            "statements": statements,
            "missing_statements": missing_lines,
            "branches": branches,
            "missing_branches": missing_branches,
        }

        if branches:
            metrics["branch_coverage"] = (branches - missing_branches) / branches * 100

        return metrics

    except (OSError, ValueError, KeyError, TypeError):
        return {"coverage_error": "Coverage-JSON konnte nicht gelesen werden."}


def wheel_smoke_test(
    wheel: Path,
    target_dir: Path,
    temp_dir: Path,
) -> CheckResult:
    """Install and import the built wheel in an isolated target directory."""
    install_result = run_check(
        "Wheel-Installation",
        [
            PYTHON,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-warn-script-location",
            "--target",
            str(target_dir),
            str(wheel),
        ],
        timeout=600,
    )

    if install_result.status != "PASS":
        return install_result

    env = os.environ.copy()
    env["PYTHONPATH"] = str(target_dir)

    smoke_code = (
        "from pathlib import Path; "
        "import meltymon_ai_os; "
        "from meltymon_ai_os.config.settings import AppSettings; "
        "module_path = Path(meltymon_ai_os.__file__).resolve(); "
        "target = Path(" + repr(str(target_dir)) + ").resolve(); "
        "assert module_path.is_relative_to(target), "
        "f'Import stammt nicht aus dem Wheel: {module_path}'; "
        "AppSettings(); "
        "print(f'Wheel-Import OK: {module_path}')"
    )

    return run_check(
        "Wheel-Import-Smoke-Test",
        [
            PYTHON,
            "-c",
            smoke_code,
        ],
        timeout=120,
        note="Isolierter Import aus dem frisch gebauten Wheel.",
        cwd=temp_dir,
        env=env,
    )


def run_build_checks(
    results: list[CheckResult],
    temp_dir: Path,
) -> None:
    """Build distributions, install the wheel and inspect metadata."""
    dist_dir = temp_dir / "dist"

    build_result = run_check(
        "Python-Paketbuild",
        [
            PYTHON,
            "-m",
            "build",
            "--outdir",
            str(dist_dir),
        ],
        timeout=900,
    )
    results.append(build_result)

    if build_result.status != "PASS":
        results.append(
            CheckResult(
                name="Wheel-Installation und Import",
                status="SKIP",
                note="Build fehlgeschlagen; kein Wheel-Smoke-Test möglich.",
            )
        )
        return

    artifacts = sorted(dist_dir.glob("*"))
    wheels = sorted(dist_dir.glob("*.whl"))

    if wheels:
        target_dir = temp_dir / "wheel-install"
        results.append(
            wheel_smoke_test(
                wheels[0],
                target_dir,
                temp_dir,
            )
        )
    else:
        results.append(
            CheckResult(
                name="Wheel-Installation und Import",
                status="FAIL",
                note="Build war erfolgreich, erzeugte aber kein Wheel.",
            )
        )

    twine = shutil.which("twine")

    if twine and artifacts:
        results.append(
            run_check(
                "Twine-Metadatenprüfung",
                [
                    twine,
                    "check",
                    *[str(path) for path in artifacts],
                ],
                timeout=300,
            )
        )
    else:
        results.append(
            CheckResult(
                name="Twine-Metadatenprüfung",
                status="SKIP",
                note="Twine fehlt oder es wurden keine Build-Artefakte erzeugt.",
            )
        )


def run_checks(
    results: list[CheckResult],
    *,
    quick: bool,
    no_build: bool,
    no_security: bool,
    audit_dependencies: bool,
) -> dict[str, object]:
    """Run the configured quality gates."""
    checks = [
        (
            "Ruff Lint",
            [
                PYTHON,
                "-m",
                "ruff",
                "check",
                "src",
                "tests",
                "scripts",
            ],
            300,
        ),
        (
            "Ruff Format",
            [
                PYTHON,
                "-m",
                "ruff",
                "format",
                "--check",
                "src",
                "tests",
                "scripts",
            ],
            300,
        ),
        (
            "Mypy",
            [PYTHON, "-m", "mypy", "src"],
            600,
        ),
    ]

    for name, command, timeout in checks:
        results.append(
            run_check(
                name,
                command,
                timeout=timeout,
            )
        )

    if quick:
        return {}

    metrics: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="meltymon-review-") as temp_name:
        temp_dir = Path(temp_name)
        coverage_file = temp_dir / "coverage.json"

        pytest_result = run_check(
            "Pytest + Branch-Coverage",
            [
                PYTHON,
                "-m",
                "pytest",
                "-q",
                "--cov=meltymon_ai_os",
                "--cov-branch",
                f"--cov-report=json:{coverage_file}",
            ],
            timeout=1800,
        )
        results.append(pytest_result)

        if coverage_file.exists():
            metrics.update(read_coverage(coverage_file))
        else:
            metrics["coverage_error"] = "Kein Coverage-JSON-Bericht erzeugt."

        if "coverage_error" in metrics:
            results.append(
                CheckResult(
                    name="Coverage-Bericht",
                    status="FAIL",
                    note=str(metrics["coverage_error"]),
                )
            )

        if no_security:
            results.append(
                CheckResult(
                    name="Optionale Sicherheitsprüfungen",
                    status="SKIP",
                    note="Durch --no-security übersprungen.",
                )
            )
        else:
            add_security_checks(
                results,
                audit_dependencies=audit_dependencies,
            )

        if no_build:
            results.append(
                CheckResult(
                    name="Build und Wheel-Smoke-Test",
                    status="SKIP",
                    note="Durch --no-build übersprungen.",
                )
            )
        else:
            run_build_checks(results, temp_dir)

    return metrics


def render_report(
    results: list[CheckResult],
    git_summary: str,
    metrics: dict[str, object],
    mode: str,
) -> str:
    """Render the complete Markdown review report."""
    timestamp = datetime.now(UTC).astimezone().isoformat(timespec="seconds")

    counts = {
        state: sum(result.status == state for result in results)
        for state in ("PASS", "FAIL", "SKIP")
    }

    if counts["FAIL"]:
        overall = "FAIL"
    elif counts["SKIP"]:
        overall = "PASS WITH SKIPS"
    else:
        overall = "PASS"

    lines = [
        "# MELTYMON AI OS – Review Report",
        "",
        f"- Zeitpunkt: `{timestamp}`",
        f"- Modus: `{mode}`",
        f"- Projekt: `{ROOT}`",
        f"- Ergebnis: **{overall}**",
        "",
        "## Zusammenfassung",
        "",
        f"- PASS: {counts['PASS']}",
        f"- FAIL: {counts['FAIL']}",
        f"- SKIP: {counts['SKIP']}",
        "",
    ]

    if metrics.get("statement_coverage") is not None:
        lines.extend(
            [
                "## Coverage",
                "",
                (f"- Statement-Coverage: **{metrics['statement_coverage']:.2f}%**"),
                (
                    "- Branch-Coverage: "
                    + (
                        f"**{metrics['branch_coverage']:.2f}%**"
                        if metrics.get("branch_coverage") is not None
                        else "**nicht verfügbar**"
                    )
                ),
                f"- Statements: {metrics.get('statements', 'unbekannt')}",
                (
                    "- Fehlende Statements: "
                    f"{metrics.get('missing_statements', 'unbekannt')}"
                ),
                f"- Branches: {metrics.get('branches', 'unbekannt')}",
                (
                    "- Fehlende Branches: "
                    f"{metrics.get('missing_branches', 'unbekannt')}"
                ),
                "",
            ]
        )
    elif metrics.get("coverage_error"):
        lines.extend(
            [
                "## Coverage",
                "",
                str(metrics["coverage_error"]),
                "",
            ]
        )

    lines.extend(["## Prüfergebnisse", ""])

    for result in results:
        lines.append(f"### [{result.status}] {result.name} ({result.duration:.2f}s)")

        if result.command:
            lines.extend(
                [
                    "",
                    "```text",
                    result.command,
                    "```",
                ]
            )

        if result.note:
            lines.extend(["", result.note])

        if result.output and result.status == "FAIL":
            lines.extend(
                [
                    "",
                    "**Fehlerausgabe:**",
                    "",
                    "```text",
                    result.output,
                    "```",
                ]
            )

        lines.append("")

    lines.extend(
        [
            "## Git-Übersicht",
            "",
            "```text",
            git_summary,
            "```",
            "",
            "## Grenzen des Berichts",
            "",
            "- Automatische Prüfungen ersetzen keine manuelle Review.",
            "- Ein übersprungener Scanner ist keine bestandene Prüfung.",
            "- Hardwareabhängige und privilegierte Messungen werden nicht erzwungen.",
            "- pip-audit fragt nur bei expliziter Aktivierung externe Advisory-Daten ab.",
            "- Der Bericht bewertet nur den Zustand zum Prüfzeitpunkt.",
            "",
        ]
    )

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only Quality- und Security-Gate für MELTYMON AI OS."
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Git, Ruff und Mypy; ohne Tests, Security und Packaging.",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Build und Wheel-Prüfung überspringen.",
    )
    parser.add_argument(
        "--no-security",
        action="store_true",
        help="Beide Sicherheitsprüfungen überspringen.",
    )
    parser.add_argument(
        "--audit-dependencies",
        action="store_true",
        help="pip-audit mit externem Advisory-Abgleich aktivieren.",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Keinen Markdown-Bericht schreiben.",
    )

    args = parser.parse_args()

    if args.quick and args.audit_dependencies:
        parser.error("--audit-dependencies kann nicht mit --quick kombiniert werden.")

    if args.no_security and args.audit_dependencies:
        parser.error(
            "--audit-dependencies kann nicht mit --no-security kombiniert werden."
        )

    return args


def main() -> int:
    args = parse_args()
    mode = "quick" if args.quick else "full"

    if args.audit_dependencies:
        mode += " + dependency audit"

    print(f"\nMELTYMON AI OS – REVIEW ({mode.upper()})")
    print(f"Projekt: {ROOT}\n")

    git_summary, results = collect_git_summary()

    metrics = run_checks(
        results,
        quick=args.quick,
        no_build=args.no_build,
        no_security=args.no_security,
        audit_dependencies=args.audit_dependencies,
    )

    print("Prüfergebnisse:")
    for result in results:
        print(f"  [{result.status:4}] {result.name} ({result.duration:.2f}s)")
        if result.note and result.status != "PASS":
            print(f"         {result.note}")

    if metrics.get("statement_coverage") is not None:
        print(f"\nStatement-Coverage: {metrics['statement_coverage']:.2f}%")
        if metrics.get("branch_coverage") is not None:
            print(f"Branch-Coverage: {metrics['branch_coverage']:.2f}%")

    failures = sum(result.status == "FAIL" for result in results)
    skips = sum(result.status == "SKIP" for result in results)
    passed = sum(result.status == "PASS" for result in results)

    print(f"\nGesamt: {passed} PASS, {failures} FAIL, {skips} SKIP")

    if not args.no_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / (
            "review-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".md"
        )
        report_path.write_text(
            render_report(results, git_summary, metrics, mode),
            encoding="utf-8",
        )
        print(f"Bericht: {report_path.relative_to(ROOT)}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
