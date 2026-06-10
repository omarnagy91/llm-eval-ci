"""llm-eval-ci: golden-set regression evaluation + CI quality gate for LLM systems.

The judgment-heavy asset is the *golden set*: real production failures curated into
trusted regression cases. The graders score a system's current outputs against that set;
the CI gate fails the build when quality silently regresses.
"""

__version__ = "0.1.0"
