"""NUMA topology and memory monitoring for MELTYMON AI OS."""

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class NUMAMemoryStats:
    """Memory statistics for a NUMA node."""

    total_bytes: int
    free_bytes: int
    used_bytes: int
    statistics: dict[str, int]

    @property
    def memory_percent(self) -> float:
        """Return the used memory percentage."""
        if self.total_bytes <= 0:
            return 0.0
        return self.used_bytes / self.total_bytes * 100.0


@dataclass(frozen=True)
class NUMANode:
    """Information about a single NUMA node."""

    node_id: int
    cpus: tuple[int, ...]
    memory: NUMAMemoryStats
    distances: tuple[int, ...]


@dataclass(frozen=True)
class NUMASnapshot:
    """A snapshot of the system NUMA topology and memory usage."""

    timestamp: datetime
    nodes: tuple[NUMANode, ...]

    @property
    def node_count(self) -> int:
        """Return the number of detected NUMA nodes."""
        return len(self.nodes)

    @property
    def total_memory_bytes(self) -> int:
        """Return total memory across all NUMA nodes."""
        return sum(node.memory.total_bytes for node in self.nodes)

    @property
    def free_memory_bytes(self) -> int:
        """Return free memory across all NUMA nodes."""
        return sum(node.memory.free_bytes for node in self.nodes)

    @property
    def used_memory_bytes(self) -> int:
        """Return used memory across all NUMA nodes."""
        return sum(node.memory.used_bytes for node in self.nodes)


class NUMAMonitor:
    """Monitor NUMA topology and per-node memory statistics."""

    NODE_PATTERN = re.compile(r"^node(\d+)$")

    def __init__(
        self,
        sysfs_root: Path = Path("/sys/devices/system/node"),
    ) -> None:
        """Initialize the NUMA monitor."""
        self.sysfs_root = Path(sysfs_root)

    @staticmethod
    def _read_text(path: Path) -> str | None:
        """Read a text file without raising filesystem errors."""
        try:
            return path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return None

    @staticmethod
    def _parse_cpu_list(value: str) -> tuple[int, ...]:
        """Parse Linux CPU list notation such as 0-3,8,10-12."""
        cpus: set[int] = set()

        for part in value.split(","):
            part = part.strip()
            if not part:
                continue

            if "-" in part:
                bounds = part.split("-", maxsplit=1)
                if len(bounds) != 2:
                    continue

                try:
                    start, end = map(int, bounds)
                except ValueError:
                    continue

                if start < 0 or end < start:
                    continue

                cpus.update(range(start, end + 1))
            else:
                try:
                    cpu = int(part)
                except ValueError:
                    continue

                if cpu >= 0:
                    cpus.add(cpu)

        return tuple(sorted(cpus))

    @staticmethod
    def _parse_memory_stats(value: str) -> NUMAMemoryStats:
        """Parse a NUMA node meminfo file.

        Linux reports these values in kB. They are converted to bytes.
        Unknown additional metrics are retained in the statistics mapping.
        """
        raw: dict[str, int] = {}

        for line in value.splitlines():
            match = re.match(
                r"^\s*Node\s+\d+\s+([A-Za-z0-9_()]+):\s+(\d+)\s*(kB)?",
                line,
            )
            if not match:
                continue

            key, number, unit = match.groups()
            amount = int(number)

            if unit == "kB":
                amount *= 1024

            raw[key] = amount

        total = raw.get("MemTotal", 0)
        free = raw.get("MemFree", 0)
        used = raw.get("MemUsed", total - free)

        return NUMAMemoryStats(
            total_bytes=total,
            free_bytes=free,
            used_bytes=used,
            statistics=raw,
        )

    def _discover_node_paths(self) -> list[tuple[int, Path]]:
        """Discover available NUMA node directories."""
        if not self.sysfs_root.is_dir():
            return []

        nodes: list[tuple[int, Path]] = []

        try:
            entries = self.sysfs_root.iterdir()
            for path in entries:
                match = self.NODE_PATTERN.fullmatch(path.name)
                if match and path.is_dir():
                    nodes.append((int(match.group(1)), path))
        except OSError:
            return []

        return sorted(nodes, key=lambda item: item[0])

    def _collect_node(self, node_id: int, path: Path) -> NUMANode:
        """Collect topology and memory information for one NUMA node."""
        cpu_text = self._read_text(path / "cpulist") or ""
        memory_text = self._read_text(path / "meminfo") or ""
        distance_text = self._read_text(path / "distance") or ""

        distances: list[int] = []
        for value in distance_text.split():
            try:
                distances.append(int(value))
            except ValueError:
                continue

        return NUMANode(
            node_id=node_id,
            cpus=self._parse_cpu_list(cpu_text),
            memory=self._parse_memory_stats(memory_text),
            distances=tuple(distances),
        )

    async def collect(self) -> NUMASnapshot:
        """Collect a NUMA snapshot asynchronously."""
        nodes = await asyncio.to_thread(self._collect)

        return NUMASnapshot(
            timestamp=datetime.now(UTC),
            nodes=tuple(nodes),
        )

    def _collect(self) -> list[NUMANode]:
        """Perform filesystem collection in a worker thread."""
        return [
            self._collect_node(node_id, path)
            for node_id, path in self._discover_node_paths()
        ]
