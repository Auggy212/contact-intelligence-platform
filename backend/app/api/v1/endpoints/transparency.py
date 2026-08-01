"""
Transparency endpoints — expose WHAT the analysis engine checks against, so a
reviewer can see the basis of every analysis:

  - the semantic concepts the engine detects (IP reversed, unlimited liability…)
  - the Indian-law corpus the Law Validator checks against (acts + sections)

Read-only. The data is projected directly from the engine's own definitions
(`_SEMANTIC_CONCEPTS`, `_RULES`), so this view is ALWAYS in sync with what the
engine actually runs — if an engineer adds a concept or law, it appears here
automatically. Internal regex patterns are deliberately NOT exposed.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_tenant_id

router = APIRouter(prefix="/transparency", tags=["Transparency"])


def _severity_str(sev) -> str:
    """FindingSeverity enum or str → plain lowercase label."""
    return getattr(sev, "value", str(sev)).lower()


@router.get("/concepts")
async def list_concepts(_tenant_id: str = Depends(get_tenant_id)) -> dict:
    """
    The semantic concepts the engine detects during template comparison —
    e.g. 'IP ownership reversed', 'Liability cap removed'. These are meaning-level
    checks, not keyword matches. Regex internals are not exposed.
    """
    from app.agents.template_comparison import _SEMANTIC_CONCEPTS

    concepts = [
        {
            "name": c.get("name", ""),
            "severity": _severity_str(c.get("severity")),
            "risk_score": c.get("risk_score"),
            "recommendation": c.get("recommendation", ""),
        }
        for c in _SEMANTIC_CONCEPTS
    ]
    return {"total": len(concepts), "concepts": concepts}


@router.get("/law-corpus")
async def list_law_corpus(_tenant_id: str = Depends(get_tenant_id)) -> dict:
    """
    The Indian-law corpus the Law Validator checks every contract against,
    grouped by statute. Each entry is a real, citable check with the section
    reference and the statutory text it is based on.
    """
    from app.agents.law_validator import _RULES

    checks = [
        {
            "id": r.get("id", ""),
            "title": r.get("title", ""),
            "act_name": r.get("act_name", ""),
            "section": r.get("section", ""),
            "severity": _severity_str(r.get("severity")),
            "law_text": r.get("law_text", ""),
            "recommendation": r.get("recommendation", ""),
            "jurisdiction": r.get("jurisdiction", "india"),
        }
        for r in _RULES
    ]

    # Group by statute so the UI can show "Indian Contract Act (5 checks)" etc.
    acts: dict[str, list[dict]] = {}
    for c in checks:
        acts.setdefault(c["act_name"], []).append(c)

    grouped = [
        {"act_name": act, "count": len(items), "checks": items}
        for act, items in sorted(acts.items())
    ]

    return {
        "total_checks": len(checks),
        "total_acts": len(grouped),
        "acts": grouped,
    }
