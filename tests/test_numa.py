
"""Tests for NUMA monitoring."""

from pathlib import Path

import pytest

from meltymon_ai_os.monitoring.numa import (
    NUMAMonitor,
    NUMAMemoryStats,
)


def create_node(
    root: Path,
    node_id: int,
    cpulist: str,
    meminfo: str,
    distance: str,
) -> Path:
    """Create a simulated NUMA node."""
    node = root / f"node{node_id}"
    node.mkdir(parents=True)

    (node / "cpulist").write_text(cpulist)
    (node / "meminfo").write_text(meminfo)
    (node / "distance").write_text(distance)

    return node


@pytest.fixture
def numa_root(tmp_path: Path) -> Path:
    """Create a simulated two-node NUMA system."""
    create_node(
        tmp_path,
        0,
        "0-3,8-11",
        """Node 0 MemTotal: 8192000 kB
Node 0 MemFree: 4096000 kB
Node 0 MemUsed: 4096000 kB
Node 0 Active: 1024000 kB
Node 0 GPUActive: 1024 kB
""",
        "10 21",
    )

    create_node(
        tmp_path,
        1,
        "4-7,12-15",
        """Node 1 MemTotal: 8192000 kB
Node 1 MemFree: 6144000 kB
Node 1 MemUsed: 2048000 kB
Node 1 Active: 512000 kB
""",
        "21 10",
    )

    return tmp_path


def test_parse_cpu_list() -> None:
    """Parse Linux CPU list notation."""
    assert NUMAMonitor._parse_cpu_list("0-3,8,10-12") == (
        0, 1, 2, 3, 8, 10, 11, 12
    )


def test_parse_cpu_list_invalid_values() -> None:
    """Ignore invalid CPU list entries."""
    assert NUMAMonitor._parse_cpu_list("0-2,invalid,-1,5") == (
        0, 1, 2, 5
    )


def test_parse_memory_stats() -> None:
    """Convert memory statistics from kB to bytes."""
    stats = NUMAMonitor._parse_memory_stats(
        """Node 0 MemTotal: 8192000 kB
Node 0 MemFree: 4096000 kB
Node 0 MemUsed: 4096000 kB
Node 0 GPUActive: 1024 kB
"""
    )

    assert stats.total_bytes == 8192000 * 1024
    assert stats.free_bytes == 4096000 * 1024
    assert stats.used_bytes == 4096000 * 1024
    assert stats.statistics["GPUActive"] == 1024 * 1024
    assert stats.memory_percent == 50.0


def test_memory_stats_missing_values() -> None:
    """Handle missing memory values safely."""
    stats = NUMAMonitor._parse_memory_stats("")

    assert stats.total_bytes == 0
    assert stats.free_bytes == 0
    assert stats.used_bytes == 0
    assert stats.memory_percent == 0.0


@pytest.mark.asyncio
async def test_collect_two_nodes(numa_root: Path) -> None:
    """Collect both simulated NUMA nodes."""
    monitor = NUMAMonitor(sysfs_root=numa_root)

    snapshot = await monitor.collect()

    assert snapshot.node_count == 2
    assert snapshot.nodes[0].node_id == 0
    assert snapshot.nodes[1].node_id == 1

    assert snapshot.nodes[0].cpus == (0, 1, 2, 3, 8, 9, 10, 11)
    assert snapshot.nodes[1].cpus == (
        4, 5, 6, 7, 12, 13, 14, 15
    )

    assert snapshot.nodes[0].distances == (10, 21)
    assert snapshot.nodes[1].distances == (21, 10)

    assert snapshot.nodes[0].memory.memory_percent == 50.0
    assert snapshot.nodes[1].memory.memory_percent == 25.0

    assert snapshot.total_memory_bytes == 16384000 * 1024
    assert snapshot.free_memory_bytes == 10240000 * 1024
    assert snapshot.used_memory_bytes == 6144000 * 1024


@pytest.mark.asyncio
async def test_collect_missing_root(tmp_path: Path) -> None:
    """Return an empty snapshot if the NUMA root does not exist."""
    monitor = NUMAMonitor(sysfs_root=tmp_path / "missing")

    snapshot = await monitor.collect()

    assert snapshot.node_count == 0
    assert snapshot.total_memory_bytes == 0


@pytest.mark.asyncio
async def test_collect_node_with_missing_files(tmp_path: Path) -> None:
    """Handle missing node files without crashing."""
    node = tmp_path / "node0"
    node.mkdir()

    monitor = NUMAMonitor(sysfs_root=tmp_path)
    snapshot = await monitor.collect()

    assert snapshot.node_count == 1
    assert snapshot.nodes[0].cpus == ()
    assert snapshot.nodes[0].memory.total_bytes == 0
    assert snapshot.nodes[0].distances == ()
