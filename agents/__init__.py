"""Saga X Agent Desk — agent layer.

Modules:
  config    — .env loading, constants, the five agents
  db        — PostgREST client bound to the `desk` schema
  preflight — verifies setup and, critically, that `desk` is NOT
              readable with the anon key
"""
