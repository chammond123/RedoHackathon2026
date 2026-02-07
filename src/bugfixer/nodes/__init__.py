"""Graph nodes – one module per phase of the agent workflow."""

from bugfixer.nodes.intake import intake_context
from bugfixer.nodes.hypothesis import hypothesis_generation
from bugfixer.nodes.reproduce import reproduction_attempt
from bugfixer.nodes.analyze import reproduction_analysis
from bugfixer.nodes.root_cause import root_cause_analysis
from bugfixer.nodes.verify_hypothesis import verify_hypothesis, run_verification_after_patch
from bugfixer.nodes.patch import patch_generation
from bugfixer.nodes.validate import validation
from bugfixer.nodes.complete import completion

__all__ = [
    "intake_context",
    "hypothesis_generation",
    "reproduction_attempt",
    "reproduction_analysis",
    "root_cause_analysis",
    "verify_hypothesis",
    "run_verification_after_patch",
    "patch_generation",
    "validation",
    "completion",
]
