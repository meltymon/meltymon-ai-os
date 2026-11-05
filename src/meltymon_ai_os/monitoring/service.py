"""Integrated monitoring service for MELTYMON AI OS."""

from dataclasses import dataclass

from meltymon_ai_os.monitoring.diagnostics import (
    DiagnosticEngine,
    DiagnosticReport,
)
from meltymon_ai_os.monitoring.health import (
    HealthEvaluator,
    HealthReport,
)
from meltymon_ai_os.monitoring.system import (
    SystemMonitor,
    SystemSnapshot,
)


@dataclass(frozen=True)
class MonitoringResult:
    """Complete result of one monitoring cycle."""

    snapshot: SystemSnapshot
    health: HealthReport
    diagnostics: DiagnosticReport

    @property
    def healthy(self) -> bool:
        """Return whether the health evaluation considers the system healthy."""
        return self.health.healthy


class MonitoringService:
    """Coordinate monitoring, health evaluation and diagnostics."""

    def __init__(
        self,
        monitor: SystemMonitor | None = None,
        health_evaluator: HealthEvaluator | None = None,
        diagnostic_engine: DiagnosticEngine | None = None,
    ) -> None:
        """Initialize the service with optional injectable components."""

        self.monitor = monitor if monitor is not None else SystemMonitor()

        self.health_evaluator = (
            health_evaluator if health_evaluator is not None else HealthEvaluator()
        )

        self.diagnostic_engine = (
            diagnostic_engine if diagnostic_engine is not None else DiagnosticEngine()
        )

    async def collect(self) -> MonitoringResult:
        """Run one complete monitoring and diagnostic cycle."""

        # 1. Collect hardware and system monitoring data.
        snapshot = await self.monitor.collect()

        # 2. Evaluate the health of the collected system snapshot.
        health_report = self.health_evaluator.evaluate(snapshot)

        # 3. Generate diagnostic findings from the health report.
        diagnostic_report = self.diagnostic_engine.diagnose(health_report)

        # 4. Return all results as one immutable object.
        return MonitoringResult(
            snapshot=snapshot,
            health=health_report,
            diagnostics=diagnostic_report,
        )
