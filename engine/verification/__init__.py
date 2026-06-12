"""Backend-agnostic verification problem IR."""

from engine.verification.inspection_adapter import (
    ADAPTER_NAME,
    ARTIFACT_PROBLEM_JSON,
    ARTIFACT_REPORT_MARKDOWN,
    InspectionAdapterReport,
    InspectionArtifact,
    REPORT_STATUS,
    render_inspection_markdown,
    write_inspection_artifacts,
)
from engine.verification.ir import (
    CandidateSpec,
    DynamicsSpec,
    ExpressionSpec,
    InputSpec,
    ObligationSpec,
    ParameterSpec,
    RegionSpec,
    SCHEMA_VERSION,
    VariableSpec,
    VerificationProblem,
)
from engine.verification.safety_adapter import (
    verification_problem_from_barrier,
    verification_problem_from_lyapunov,
    verification_problem_from_obligations,
)
from engine.verification.sympy_codec import expression_spec
from engine.verification.system_codec import (
    dynamics_spec_from_controlled,
    dynamics_spec_from_system,
)

__all__ = [
    "ADAPTER_NAME",
    "ARTIFACT_PROBLEM_JSON",
    "ARTIFACT_REPORT_MARKDOWN",
    "CandidateSpec",
    "DynamicsSpec",
    "ExpressionSpec",
    "InputSpec",
    "InspectionAdapterReport",
    "InspectionArtifact",
    "ObligationSpec",
    "ParameterSpec",
    "REPORT_STATUS",
    "RegionSpec",
    "SCHEMA_VERSION",
    "VariableSpec",
    "VerificationProblem",
    "dynamics_spec_from_controlled",
    "dynamics_spec_from_system",
    "expression_spec",
    "render_inspection_markdown",
    "verification_problem_from_barrier",
    "verification_problem_from_lyapunov",
    "verification_problem_from_obligations",
    "write_inspection_artifacts",
]
