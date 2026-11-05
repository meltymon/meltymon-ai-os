import pytest

from meltymon_ai_os.agents.capabilities import (
    Capability,
    CapabilitySet,
)
from meltymon_ai_os.agents.exceptions import AgentCapabilityError


def test_capability_creation():
    capability = Capability(
        name="llm.generate",
        description="Generate model responses",
    )

    assert capability.name == "llm.generate"


def test_capability_set_creation():
    capabilities = CapabilitySet(
        [
            "llm.generate",
            "memory.read",
            "tools.execute",
        ]
    )

    assert len(capabilities) == 3
    assert "llm.generate" in capabilities
    assert capabilities.has("memory.read")


def test_capability_objects_are_supported():
    capabilities = CapabilitySet(
        [
            Capability("llm.generate"),
            Capability("memory.read"),
        ]
    )

    assert capabilities.has("llm.generate")


def test_duplicate_capabilities_are_removed():
    capabilities = CapabilitySet(
        [
            "llm.generate",
            "llm.generate",
        ]
    )

    assert len(capabilities) == 1


def test_capabilities_are_immutable():
    capabilities = CapabilitySet(["llm.generate"])

    with pytest.raises(AttributeError):
        capabilities._names = frozenset()


def test_capability_names_are_normalized():
    capabilities = CapabilitySet(["  llm.generate  "])

    assert capabilities.has("llm.generate")


@pytest.mark.parametrize(
    "invalid_name",
    ["", " ", "*", "LLM.GENERATE", "llm..generate", "llm generate"],
)
def test_invalid_capability_names_are_rejected(invalid_name):
    with pytest.raises(ValueError):
        CapabilitySet([invalid_name])


def test_non_string_capability_is_rejected():
    with pytest.raises(TypeError):
        CapabilitySet([123])


def test_require_existing_capability():
    capabilities = CapabilitySet(["llm.generate"])

    capabilities.require("llm.generate")


def test_require_missing_capability():
    capabilities = CapabilitySet(["llm.generate"])

    with pytest.raises(AgentCapabilityError):
        capabilities.require("tools.execute")


def test_missing_capabilities():
    capabilities = CapabilitySet(["llm.generate"])

    missing = capabilities.missing(
        [
            "llm.generate",
            "memory.read",
            "tools.execute",
        ]
    )

    assert missing == frozenset(
        {
            "memory.read",
            "tools.execute",
        }
    )


def test_require_all_capabilities():
    capabilities = CapabilitySet(
        [
            "llm.generate",
            "memory.read",
        ]
    )

    capabilities.require_all(
        [
            "llm.generate",
            "memory.read",
        ]
    )


def test_require_all_reports_missing_capabilities():
    capabilities = CapabilitySet(["llm.generate"])

    with pytest.raises(AgentCapabilityError):
        capabilities.require_all(
            [
                "memory.read",
                "tools.execute",
            ]
        )


def test_iteration_is_deterministic():
    capabilities = CapabilitySet(
        [
            "tools.execute",
            "llm.generate",
            "memory.read",
        ]
    )

    assert list(capabilities) == [
        "llm.generate",
        "memory.read",
        "tools.execute",
    ]


def test_empty_capability_set():
    capabilities = CapabilitySet()

    assert len(capabilities) == 0
    assert not capabilities
