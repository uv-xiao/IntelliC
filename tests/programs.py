"""Shared stronger authored programs for high-level tests.

These helpers intentionally reuse the public example/programming surfaces
instead of rebuilding tiny raw payload dicts in every high-level suite.
Low-level contract tests may still use raw payloads directly where that is the
actual subject under test.
"""

from __future__ import annotations

from examples.csp_channel_pipeline.demo import token_pipeline
from examples.pto_pypto_vector_add.demo import vector_add
from examples.pto_pypto_vector_dag.demo import vector_dag
from examples.serving_routine.demo import serving_routine
from examples.wsp_littlekernel_pipelined_gemm.demo import littlekernel_pipelined_gemm


def portable_vector_add_program():
    """Return the simplest traced public kernel used where backends are narrower."""

    return vector_add


def portable_vector_add_payload(*, backend: str, option: str | None = None) -> dict[str, object]:
    """Return a vector-add payload annotated with an explicit target."""

    payload = vector_add.to_program()
    payload["target"] = {"backend": backend}
    if option is not None:
        payload["target"]["option"] = option
    return payload


def pto_vector_dag_program():
    """Return a non-trivial PyPTO-style elementwise DAG program."""

    return vector_dag


def pto_vector_dag_payload() -> dict[str, object]:
    """Return the canonical payload for the PyPTO-style DAG program."""

    payload = vector_dag.to_program()
    payload["target"] = {"backend": "pto", "option": "a2a3sim"}
    return payload


def nvgpu_serving_program():
    """Return a typed multi-task routine used as the default NVGPU test input."""

    return serving_routine


def nvgpu_serving_payload() -> dict[str, object]:
    """Return the canonical payload for the serving routine."""

    payload = serving_routine.to_program()
    payload["target"] = {"backend": "nvgpu", "option": "ampere"}
    return payload


def nvgpu_wsp_program():
    """Return the WSP pipelined GEMM example for schedule-heavy tests."""

    return littlekernel_pipelined_gemm


def nvgpu_wsp_payload() -> dict[str, object]:
    """Return the canonical payload for the WSP pipelined GEMM example."""

    payload = littlekernel_pipelined_gemm.to_program()
    payload["target"] = {"backend": "nvgpu", "option": "ampere"}
    return payload


def nvgpu_csp_program():
    """Return the CSP channel pipeline example for protocol-heavy tests."""

    return token_pipeline


def nvgpu_csp_payload() -> dict[str, object]:
    """Return the canonical payload for the CSP channel pipeline example."""

    payload = token_pipeline.to_program()
    payload["target"] = {"backend": "nvgpu", "option": "ampere"}
    return payload
