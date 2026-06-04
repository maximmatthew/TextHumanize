"""Domain dictionaries for preserving specialist terminology.

These dictionaries are intentionally small and curated. They are not used for
replacement; they protect domain terms from being simplified by generic
humanization stages.
"""

from __future__ import annotations

import re
from functools import lru_cache

_DOMAIN_ALIASES: dict[str, str] = {
    "saas": "saas",
    "software": "saas",
    "b2b": "saas",
    "ecommerce": "ecommerce",
    "e-commerce": "ecommerce",
    "commerce": "ecommerce",
    "retail": "ecommerce",
    "fintech": "fintech",
    "finance": "fintech",
    "banking": "fintech",
    "legal": "legal",
    "law": "legal",
    "education": "education",
    "edtech": "education",
    "real_estate": "real_estate",
    "real-estate": "real_estate",
    "real estate": "real_estate",
    "property": "real_estate",
    "healthcare": "healthcare",
    "health": "healthcare",
    "medical": "healthcare",
}

_DOMAIN_TERMS: dict[str, tuple[str, ...]] = {
    "saas": (
        "SaaS", "ARR", "MRR", "churn", "churn rate", "retention",
        "activation", "onboarding", "workspace", "tenant", "seat",
        "subscription", "usage-based billing", "feature flag", "API",
        "API key", "webhook", "SSO", "SAML", "OAuth", "RBAC",
        "multi-tenant", "service-level agreement",
    ),
    "ecommerce": (
        "SKU", "cart", "checkout", "conversion rate", "AOV",
        "average order value", "inventory", "fulfillment", "shipping",
        "returns", "order", "marketplace", "payment gateway",
        "abandoned cart", "product feed", "variant", "coupon",
        "merchant", "last-mile delivery",
    ),
    "fintech": (
        "KYC", "AML", "PCI DSS", "chargeback", "settlement",
        "ledger", "wallet", "payment rail", "ACH", "SEPA",
        "interchange", "underwriting", "risk score", "tokenization",
        "open banking", "credit limit", "FX", "IBAN",
    ),
    "legal": (
        "clause", "indemnity", "liability", "jurisdiction",
        "arbitration", "compliance", "contract", "agreement",
        "data processing agreement", "DPA", "SLA", "NDA",
        "intellectual property", "force majeure", "governing law",
        "warranty", "breach", "notice period",
    ),
    "education": (
        "curriculum", "syllabus", "rubric", "assessment",
        "learning outcome", "LMS", "course", "module", "lesson",
        "quiz", "assignment", "enrollment", "student", "instructor",
        "cohort", "grade", "credit", "accreditation",
    ),
    "real_estate": (
        "listing", "MLS", "mortgage", "escrow", "appraisal",
        "closing", "lease", "tenant", "landlord", "cap rate",
        "net operating income", "NOI", "occupancy", "zoning",
        "property management", "HOA", "down payment", "square footage",
    ),
    "healthcare": (
        "EHR", "EMR", "HIPAA", "patient", "clinical", "diagnosis",
        "treatment", "care plan", "triage", "referral", "provider",
        "payer", "claim", "prior authorization", "ICD-10", "CPT",
        "telehealth", "medical record", "PHI",
    ),
}

_DOMAIN_MARKERS: dict[str, tuple[str, ...]] = {
    domain: tuple(term.lower() for term in terms[:14])
    for domain, terms in _DOMAIN_TERMS.items()
}


def normalize_domain(domain: str) -> str | None:
    """Normalize a domain name or alias to a known dictionary key."""
    key = domain.strip().lower().replace("_", " ")
    return _DOMAIN_ALIASES.get(key) or _DOMAIN_ALIASES.get(key.replace(" ", "_"))


def list_domains() -> list[str]:
    """Return supported domain dictionary names."""
    return sorted(_DOMAIN_TERMS)


def get_domain_terms(domain: str) -> tuple[str, ...]:
    """Return terms for a supported domain or an empty tuple."""
    normalized = normalize_domain(domain)
    if not normalized:
        return ()
    return _DOMAIN_TERMS.get(normalized, ())


@lru_cache(maxsize=512)
def _term_re(term: str) -> re.Pattern[str]:
    prefix = r"(?<!\w)" if term[:1].isalnum() else ""
    suffix = r"(?!\w)" if term[-1:].isalnum() else ""
    return re.compile(prefix + re.escape(term) + suffix, re.IGNORECASE)


def _term_present(text: str, term: str) -> bool:
    return bool(_term_re(term).search(text))


def detect_domains(
    text: str,
    *,
    max_domains: int = 2,
    min_hits: int = 2,
) -> list[str]:
    """Detect likely domains from marker terms present in text."""
    if not text.strip():
        return []

    scores: list[tuple[str, int]] = []
    for domain, markers in _DOMAIN_MARKERS.items():
        hits = sum(1 for marker in markers if _term_present(text, marker))
        if hits >= min_hits:
            scores.append((domain, hits))

    scores.sort(key=lambda item: (-item[1], item[0]))
    return [domain for domain, _hits in scores[:max_domains]]


def _normalize_domains(domains: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if domains is None:
        return []
    if isinstance(domains, str):
        raw = [domains]
    else:
        raw = list(domains)

    normalized: list[str] = []
    for item in raw:
        domain = normalize_domain(str(item))
        if domain and domain not in normalized:
            normalized.append(domain)
    return normalized


def domain_terms_for_text(
    text: str,
    *,
    domains: str | list[str] | tuple[str, ...] | None = None,
    max_terms: int = 80,
) -> list[str]:
    """Return domain terms present in text for explicit or detected domains."""
    selected = _normalize_domains(domains)
    if not selected:
        selected = detect_domains(text)

    terms: list[str] = []
    seen: set[str] = set()
    for domain in selected:
        for term in _DOMAIN_TERMS[domain]:
            key = term.casefold()
            if key in seen:
                continue
            if _term_present(text, term):
                seen.add(key)
                terms.append(term)

    terms.sort(key=lambda term: (-len(term), term.lower()))
    return terms[:max_terms]
