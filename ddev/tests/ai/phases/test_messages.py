# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from ddev.ai.phases.messages import (
    PhaseCompleteMessage,
    PhaseFailedMessage,
    PipelineStartMessage,
    make_phase_complete_type,
)


def test_same_name_returns_same_class():
    t1 = make_phase_complete_type("alpha")
    t2 = make_phase_complete_type("alpha")
    assert t1 is t2


def test_different_names_return_different_classes():
    t1 = make_phase_complete_type("phase_x_unique")
    t2 = make_phase_complete_type("phase_y_unique")
    assert t1 is not t2


def test_generated_class_is_subclass_of_phase_complete_message():
    t = make_phase_complete_type("sub_test")
    assert issubclass(t, PhaseCompleteMessage)


def test_generated_class_name_reflects_phase_name():
    t = make_phase_complete_type("my_phase")
    assert "my_phase" in t.__name__


def test_pipeline_start_message_stores_fields():
    msg = PipelineStartMessage(
        id="start_1",
        checkpoint_path="/tmp/checkpoints.yaml",
        metadata={"project": "myapp"},
    )
    assert msg.id == "start_1"
    assert msg.checkpoint_path == "/tmp/checkpoints.yaml"
    assert msg.metadata == {"project": "myapp"}


def test_phase_complete_message_stores_fields():
    msg = PhaseCompleteMessage(
        id="done_1",
        phase_name="analyze",
        checkpoint_path="/tmp/checkpoints.yaml",
        metadata={"k": "v"},
    )
    assert msg.phase_name == "analyze"
    assert msg.checkpoint_path == "/tmp/checkpoints.yaml"
    assert msg.metadata == {"k": "v"}


def test_phase_failed_message_stores_fields():
    msg = PhaseFailedMessage(
        id="fail_1",
        phase_name="transform",
        checkpoint_path="/tmp/checkpoints.yaml",
        error="Agent returned invalid YAML",
    )
    assert msg.phase_name == "transform"
    assert msg.error == "Agent returned invalid YAML"
