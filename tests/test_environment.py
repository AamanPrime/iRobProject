from __future__ import annotations

import numpy as np

from reacher_id.environment import assert_runtime, inspect_runtime, model_xml_bytes


def test_runtime_matches_pinned_contract(phase1_config):
    info = inspect_runtime(phase1_config.runtime.seed)
    assert_runtime(info, phase1_config.runtime)
    assert info.xml_type == "bytes"
    assert isinstance(model_xml_bytes(), bytes)
    assert info.joint_names == ("shoulder", "wrist")
    assert np.allclose(info.actuator_gears, [0.05, 0.05])
