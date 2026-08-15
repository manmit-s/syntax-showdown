"""
core package — re-export the public API so callers can write
    from core import ai_engine, db_client, code_sandbox
or
    from core.ai_engine import generate_problem
"""
from core import ai_engine, db_client, code_sandbox

__all__ = ["ai_engine", "db_client", "code_sandbox"]
