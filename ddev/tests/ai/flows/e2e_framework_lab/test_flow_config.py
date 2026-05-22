from ddev.ai.flows.e2e_framework_lab.runner import FLOW_DIR
from ddev.ai.phases.config import FlowConfig
from ddev.ai.phases.template import render_prompt

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


def test_e2e_framework_lab_prompts_render_runtime_variables() -> None:
    context = {
        "integration": "redisdb",
        "integration_path": "/repo/redisdb",
        "agent_repo_path": "/repo/datadog-agent",
        "agent_worktree_path": "/repo/datadog-agent-worktrees/e2e-lab-redisdb",
        "branch_name": "e2e-lab-redisdb",
        "agent_e2e_docs_pr": "https://example.test/pr",
        "research_integration_memory": "researched redisdb",
        "generate_component_memory": "component ready",
        "generate_scenario_memory": "scenario ready",
        "generate_tasks_and_registry_memory": "tasks ready",
    }

    prompt_paths = [
        *sorted((FLOW_DIR / "prompts").glob("*.md")),
        *sorted((FLOW_DIR / "tasks").glob("*.md")),
    ]

    for prompt_path in prompt_paths:
        rendered = render_prompt(prompt_path, context)
        assert "{{" not in rendered, prompt_path
        assert "}}" not in rendered, prompt_path

    assert "redisdb" in render_prompt(FLOW_DIR / "tasks" / "research.md", context)
    assert "researched redisdb" in render_prompt(FLOW_DIR / "tasks" / "component.md", context)
    assert "/repo/datadog-agent-worktrees/e2e-lab-redisdb" in render_prompt(
        FLOW_DIR / "prompts" / "component_writer.md", context
    )


def test_e2e_framework_lab_prompts_include_autodiscovery_reachability_guidance() -> None:
    component_task = (FLOW_DIR / "tasks" / "component.md").read_text()
    review_task = (FLOW_DIR / "tasks" / "review.md").read_text()

    assert "%%host%%" in component_task
    assert "container that owns the label" in component_task
    assert "put the label on the target service container" in component_task
    assert "extra optional service instances" in component_task

    assert "Autodiscovery" in review_task
    assert "host and port resolve to a reachable listener" in review_task


def test_e2e_framework_lab_prompts_require_explicit_auxiliary_asset_copying() -> None:
    component_task = (FLOW_DIR / "tasks" / "component.md").read_text()
    review_task = (FLOW_DIR / "tasks" / "review.md").read_text()

    assert "Extra Compose manifests" in component_task
    assert "keep workload scripts as files" in component_task
    assert "explicitly copy those assets" in component_task
    assert "WithPulumiDependsOn" in component_task
    assert "avoid using service images for helper containers" in component_task
    assert "seed data matching configured key patterns" in component_task

    assert "local scripts, config files, or build contexts" in review_task
    assert "explicitly copied to the remote Docker host" in review_task
    assert "helper containers do not use images that trigger unrelated Autodiscovery" in review_task
