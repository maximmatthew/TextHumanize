"""Tests for domain dictionaries and domain-term preservation."""

from texthumanize import detect_domains, domain_terms_for_text, list_domains
from texthumanize.pipeline import Pipeline
from texthumanize.segmenter import Segmenter
from texthumanize.utils import HumanizeOptions


def test_supported_domain_list_contains_target_domains():
    domains = set(list_domains())
    assert {
        "saas",
        "ecommerce",
        "fintech",
        "legal",
        "education",
        "real_estate",
        "healthcare",
    } <= domains


def test_detect_domains_saas_from_markers():
    text = (
        "The SaaS team tracks ARR, churn rate, onboarding, and API key usage "
        "for each workspace."
    )
    assert detect_domains(text) == ["saas"]


def test_domain_terms_for_text_preserves_only_present_terms():
    text = "ARR and churn rate improved after onboarding."
    terms = domain_terms_for_text(text, domains="saas")
    assert "ARR" in terms
    assert "churn rate" in terms
    assert "onboarding" in terms
    assert "webhook" not in terms


def test_explicit_healthcare_domain_terms():
    text = "HIPAA rules protect PHI in every medical record."
    terms = domain_terms_for_text(text, domains=["healthcare"])
    assert {"HIPAA", "PHI", "medical record"} <= set(terms)


def test_segmenter_protects_longest_domain_terms_first():
    segmenter = Segmenter(preserve={"keep_keywords": ["API", "API key"]})
    segmented = segmenter.segment("Rotate the API key before deployment.")
    originals = [segment.original for segment in segmented.segments]
    assert "API key" in originals
    assert segmented.restore(segmented.text) == "Rotate the API key before deployment."


def test_pipeline_adds_detected_domain_terms_to_preserve_config():
    options = HumanizeOptions()
    pipeline = Pipeline(options)
    preserve = dict(options.preserve)
    terms = pipeline._apply_domain_dictionaries(
        "The SaaS dashboard tracks ARR, churn rate, onboarding, and API key usage.",
        preserve,
    )
    assert {"ARR", "churn rate", "onboarding", "API key"} <= set(terms)
    assert {"ARR", "churn rate", "onboarding", "API key"} <= set(
        preserve["keep_keywords"]
    )


def test_pipeline_respects_disabled_domain_terms():
    options = HumanizeOptions(preserve={"domain_terms": False})
    pipeline = Pipeline(options)
    preserve = dict(options.preserve)
    terms = pipeline._apply_domain_dictionaries(
        "The SaaS dashboard tracks ARR and churn rate.",
        preserve,
    )
    assert terms == []
    assert "keep_keywords" not in preserve
