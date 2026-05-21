from ddev.ai.flows.e2e_framework_lab.runner import FLOW_DIR
from ddev.ai.phases.config import FlowConfig


REQUIRED_PHASES = {
    "research_integration",
    "generate_component",
    "generate_scenario",
    "generate_tasks_and_registry",
    "review_lab",
}


def test_e2e_framework_lab_flow_loads() -> None:
    config = FlowConfig.from_yaml(FLOW_DIR / "flow.yaml", FLOW_DIR)

    assert set(config.phases) == REQUIRED_PHASES
    assert [entry.phase for entry in config.flow] == [
        "research_integration",
        "generate_component",
        "generate_scenario",
        "generate_tasks_and_registry",
        "review_lab",
    ]


def test_e2e_framework_lab_flow_dependencies() -> None:
    config = FlowConfig.from_yaml(FLOW_DIR / "flow.yaml", FLOW_DIR)
    dependencies = {entry.phase: entry.dependencies for entry in config.flow}

    assert dependencies["research_integration"] == []
    assert dependencies["generate_component"] == ["research_integration"]
    assert dependencies["generate_scenario"] == ["research_integration", "generate_component"]
    assert dependencies["generate_tasks_and_registry"] == ["generate_scenario"]
    assert dependencies["review_lab"] == [
        "generate_component",
        "generate_scenario",
        "generate_tasks_and_registry",
    ]


def test_e2e_framework_lab_flow_uses_write_tools_only_after_research() -> None:
    config = FlowConfig.from_yaml(FLOW_DIR / "flow.yaml", FLOW_DIR)

    assert config.agents["researcher"].tools == ["read_file", "grep", "list_files"]
    for agent_name in ["component_writer", "scenario_writer", "task_writer", "reviewer"]:
        assert "create_file" in config.agents[agent_name].tools
        assert "edit_file" in config.agents[agent_name].tools
