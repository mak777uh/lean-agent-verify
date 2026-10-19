"""preflight - cheap local checks for Lean proof-bounty artifacts.

The name of the game: a bounty pays only when the *checker* accepts the artifact,
and the checker rejects for reasons that have nothing to do with whether the
mathematics is right (a meta-command token in the file, a redeclared statement,
an axiom outside the allowlist, a build over the time budget). Those are the
failures this package catches locally, in seconds, before a claim is spent.
"""
from __future__ import annotations

__version__ = "0.1.0"

from .policy import Policy  # noqa: F401
from .compose import compose  # noqa: F401
from .tokens import scan as scan_tokens  # noqa: F401

__all__ = ["Policy", "compose", "scan_tokens", "__version__"]
