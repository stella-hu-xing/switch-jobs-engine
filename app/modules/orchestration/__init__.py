"""Lightweight sequential orchestration tying the module services together.

v0 deliberately uses plain function calls (no LangGraph/agent graph) per the
locked-in tech plan. Each stage writes its own storage records, so the
pipeline can be resumed/inspected at any point via each module's own API.
"""
