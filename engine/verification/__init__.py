"""Backend-agnostic verification problem IR."""

from engine.verification.ir import (
    ExpressionSpec,
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

__all__ = [
    "ExpressionSpec",
    "ObligationSpec",
    "ParameterSpec",
    "RegionSpec",
    "SCHEMA_VERSION",
    "VariableSpec",
    "VerificationProblem",
    "expression_spec",
    "verification_problem_from_barrier",
    "verification_problem_from_lyapunov",
    "verification_problem_from_obligations",
]
