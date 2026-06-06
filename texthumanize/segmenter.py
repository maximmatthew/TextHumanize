"""Сегментатор текста — защита блоков, которые не должны изменяться."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Placeholder sentinel ──────────────────────────────────────
# Null-byte framing is used to mark protected tokens.
PLACEHOLDER_PREFIX = "\x00THZ_"
PLACEHOLDER_SUFFIX = "\x00"
_PLACEHOLDER_RE = re.compile(r'\x00THZ_[A-Z_]+_\d+\x00')
_PLACEHOLDER_KIND_RE = re.compile(r'\x00THZ_([A-Z_]+)_\d+\x00')
_INLINE_SAFE_PLACEHOLDER_KINDS = {
    "HTML_TAG",
    "NUMBER",
    "DATE",
    "CURRENCY",
    "VERSION",
    "IDENTIFIER",
    "NAMED_ENTITY",
    "BRAND_TERM",
    "KEEP_KEYWORD",
}

# ── Placeholder-aware helpers (used by ALL pipeline stages) ───


def has_placeholder(text: str) -> bool:
    """Return True if *text* contains any placeholder token."""
    return "\x00" in text


def is_placeholder_word(word: str) -> bool:
    """Return True if a whitespace-delimited word contains a placeholder."""
    return "\x00" in word


def skip_placeholder_sentence(sentence: str) -> bool:
    """Return True when a sentence should be skipped by word-level stages.

    HTML inline tags are safe to keep during sentence-level processing:
    they protect markup while still allowing transformations in visible text.
    Other protected kinds (URLs, code, emails, etc.) still trigger skip.
    """
    if "\x00" not in sentence:
        return False

    kinds = {
        m.group(1)
        for m in _PLACEHOLDER_KIND_RE.finditer(sentence)
    }
    if not kinds:
        return True
    return any(kind not in _INLINE_SAFE_PLACEHOLDER_KINDS for kind in kinds)


def _inside_existing_placeholder(text: str, start: int, end: int) -> bool:
    """Return True if a regex match points inside an existing placeholder."""
    return any(
        match.start() <= start and end <= match.end()
        for match in _PLACEHOLDER_RE.finditer(text)
    )


@dataclass
class ProtectedSegment:
    """Защищённый сегмент текста."""
    placeholder: str
    original: str
    kind: str  # code_block, inline_code, url, email, html_tag, hashtag, mention, number


@dataclass
class SegmentedText:
    """Текст с защищёнными сегментами."""
    text: str
    segments: list[ProtectedSegment] = field(default_factory=list)

    def restore(self, processed_text: str) -> str:
        """Восстановить защищённые сегменты в обработанном тексте.

        Handles both exact matches and case-corrupted placeholders
        (e.g. lowercased by sentence-join logic).
        """
        result = processed_text
        # Pass 1: exact match (fast path)
        for seg in reversed(self.segments):
            result = result.replace(seg.placeholder, seg.original)

        # Pass 2: if any \x00 markers remain, try case-insensitive recovery
        if "\x00" in result:
            for seg in reversed(self.segments):
                # Build case-insensitive pattern from exact placeholder
                pat = re.compile(re.escape(seg.placeholder), re.IGNORECASE)
                result = pat.sub(seg.original, result)

        # Pass 3: last resort — strip any orphaned placeholder tokens
        if "\x00" in result:
            result = _PLACEHOLDER_RE.sub("", result)
            # Also handle lower-cased remnants
            result = re.sub(r'\x00thz_[a-z_]+_\d+\x00', '', result, flags=re.IGNORECASE)
            # Remove lone null bytes
            result = result.replace("\x00", "")

        return result


# Регулярные выражения для защищаемых элементов
_MONTH_NAMES = (
    "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    "jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    "dec(?:ember)?|"
    "января|февраля|марта|апреля|мая|июня|июля|августа|сентября|"
    "октября|ноября|декабря|"
    "січня|лютого|березня|квітня|травня|червня|липня|серпня|"
    "вересня|жовтня|листопада|грудня"
)

_PATTERNS = {
    "code_block": re.compile(
        r'```[\s\S]*?```'
        r'|'
        r'~~~[\s\S]*?~~~',
        re.MULTILINE,
    ),
    "inline_code": re.compile(r'`[^`\n]+?`'),
    # HTML block: protect entire paired tag + content (p, div, ul, ol, li, h1-h6, etc.)
    "html_block": re.compile(
        r'<(ul|ol|table|thead|tbody|tr|pre|code|script|style|blockquote)'
        r'(?:\s[^>]*)?>[\s\S]*?</\1\s*>',
        re.IGNORECASE,
    ),
    # URL: handles multi-level TLDs like .com.ua, .kh.ua, .co.uk
    "url": re.compile(
        r'https?://[^\s<>\[\]()\"\']+[^\s<>\[\]()\"\'.,;:!?)]'
        r'|'
        r'www\.[^\s<>\[\]()\"\']+[^\s<>\[\]()\"\'.,;:!?)]',
        re.IGNORECASE,
    ),
    # Bare domain: site.com, site.com.ua, site.kh.ua (without http prefix)
    "bare_domain": re.compile(
        r'\b[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?'
        r'\.(?:com|net|org|info|biz|io|dev|app|pro|me|ua|ru|de|fr|es|it|pl|pt|uk|eu|us|co|in|br)'
        r'(?:\.(?:ua|uk|br|au|nz|za|ar|mx|jp|kr|cn|tw|hk|sg|my|in|il|tr))?'
        r'(?:/[^\s<>\[\]()\"\']*[^\s<>\[\]()\"\'.,;:!?)])?',
        re.IGNORECASE,
    ),
    "email": re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'),
    "html_tag": re.compile(r'</?[a-zA-Z][^>]*?>'),
    "hashtag": re.compile(r'#[a-zA-Zа-яА-ЯёЁіІїЇєЄґҐ0-9_]+'),
    "mention": re.compile(r'@[a-zA-Z0-9_]+'),
    "markdown_link": re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
    "markdown_image": re.compile(r'!\[([^\]]*)\]\(([^)]+)\)'),
    "markdown_heading": re.compile(r'^#{1,6}\s+', re.MULTILINE),
    "markdown_bold": re.compile(r'\*\*[^*]+?\*\*|__[^_]+?__'),
    "markdown_italic": re.compile(r'(?<!\*)\*[^*]+?\*(?!\*)|(?<!_)_[^_]+?_(?!_)'),
    "quoted_text": re.compile(
        r'"[^"\n]{2,240}"'
        r'|“[^”\n]{2,240}”'
        r'|«[^»\n]{2,240}»'
        r'|„[^“\n]{2,240}“',
    ),
    "date": re.compile(
        rf'\b(?:'
        rf'\d{{4}}[-/.]\d{{1,2}}[-/.]\d{{1,2}}'
        rf'|\d{{1,2}}[-/.]\d{{1,2}}[-/.]\d{{2,4}}'
        rf'|\d{{1,2}}\s+(?:{_MONTH_NAMES})(?:\s+\d{{2,4}})?'
        rf'|(?:{_MONTH_NAMES})\s+\d{{1,2}}(?:,?\s+\d{{2,4}})?'
        rf')\b',
        re.IGNORECASE,
    ),
    "currency": re.compile(
        r'(?<!\w)(?:'
        r'[$€£₴₽]\s?\d+(?:[.,]\d+)*(?:\.\d+)?'
        r'|\d+(?:[.,]\d+)*(?:\.\d+)?\s?'
        r'(?:USD|EUR|GBP|UAH|RUB|грн|руб|долл|евро|uah|usd|eur)'
        r')(?!\w)',
        re.IGNORECASE,
    ),
    "version": re.compile(
        r'(?<![\w])v?\d+\.\d+(?:\.\d+){1,3}'
        r'(?:[-+][0-9A-Za-z][0-9A-Za-z._-]*)?(?![\w])',
        re.IGNORECASE,
    ),
    "identifier": re.compile(
        r'\b(?:'
        r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
        r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
        r'|(?:ORD|ORDER|INV|INVOICE|SKU|TICKET|CASE|REQ|TXN|PAY|SUB|ID)'
        r'[-_ ]?[A-Z0-9][A-Z0-9_-]{2,}'
        r'|[A-Z]{2,}[A-Z0-9_]*[-_]\d[A-Z0-9_-]*'
        r')\b',
    ),
    "named_entity": re.compile(
        r'\b(?:'
        r'[A-ZА-ЯІЇЄҐ][A-Za-zА-Яа-яЁёІіЇїЄєҐґ0-9&.\'-]+'
        r'(?:\s+(?:'
        r'[A-ZА-ЯІЇЄҐ][A-Za-zА-Яа-яЁёІіЇїЄєҐґ0-9&.\'-]+'
        r'|&|and|of|the|for|de|du|von|van'
        r')){1,5}'
        r')\b',
    ),
    # HTML list items: protect <li>...</li> individually
    "html_list_item": re.compile(r'<li\b[^>]*>[\s\S]*?</li\s*>', re.IGNORECASE),
    # Leader dots (TOC, оглавления): "Глава 1 .......... 5"
    "leader_dots": re.compile(r'^.*\.{4,}.*\d+\s*$', re.MULTILINE),
}

_HTML_BLOCK_CLOSE_MARKERS = (
    "</ul",
    "</ol",
    "</table",
    "</thead",
    "</tbody",
    "</tr",
    "</pre",
    "</code",
    "</script",
    "</style",
    "</blockquote",
)

# Паттерн для чисел с единицами измерения
_NUMBER_PATTERN = re.compile(
    r'\b\d+(?:[.,]\d+)?(?:\s*(?:руб|грн|USD|EUR|%|°[CF]?'
    r'|кг|г|мг|т|км|м|см|мм|л|мл|шт|чел|раз'
    r'|KB|MB|GB|TB|px|em|rem|pt))?\.?\b',
    re.IGNORECASE,
)


class Segmenter:
    """Сегментатор для защиты неизменяемых частей текста."""

    def __init__(self, preserve: dict | None = None):
        """
        Args:
            preserve: Словарь настроек защиты.
                code_blocks, urls, emails, hashtags, mentions,
                markdown, html, numbers, dates, prices, identifiers,
                quoted_text, named_entities, brand_terms.
        """
        self.preserve = preserve or {
            "code_blocks": True,
            "urls": True,
            "emails": True,
            "hashtags": True,
            "mentions": True,
            "markdown": True,
            "html": True,
            "numbers": True,
            "dates": True,
            "prices": True,
            "identifiers": True,
            "quoted_text": True,
            "named_entities": True,
            "brand_terms": [],
        }
        self._counter = 0

    def _make_placeholder(self, kind: str) -> str:
        """Создать уникальный placeholder."""
        self._counter += 1
        return f"\x00THZ_{kind.upper()}_{self._counter}\x00"

    def segment(self, text: str) -> SegmentedText:
        """Разобрать текст и защитить неизменяемые части.

        Args:
            text: Исходный текст.

        Returns:
            SegmentedText с placeholders вместо защищённых элементов.
        """
        self._counter = 0
        segments: list[ProtectedSegment] = []
        result = text

        # Порядок важен: сначала крупные блоки, потом мелкие

        # 1. Блоки кода
        if self.preserve.get("code_blocks", True):
            result = self._protect(result, "code_block", segments)

        # 2. Inline-код
        if self.preserve.get("code_blocks", True):
            result = self._protect(result, "inline_code", segments)

        # 3. HTML blocks (ul, ol, table, pre, etc.) — before individual tags
        if self.preserve.get("html", True):
            result = self._protect(result, "html_block", segments)

        # 4. HTML list items (<li>...</li>) — protect individually
        if self.preserve.get("html", True):
            result = self._protect(result, "html_list_item", segments)

        # 5. Markdown-изображения (до ссылок!)
        if self.preserve.get("markdown", True):
            result = self._protect(result, "markdown_image", segments)

        # 6. Markdown-ссылки
        if self.preserve.get("markdown", True):
            result = self._protect(result, "markdown_link", segments)

        # 6b. Exact quoted text — preserve citations/testimonials verbatim
        if self.preserve.get("quoted_text", True):
            result = self._protect(result, "quoted_text", segments)

        # 7. URL (with http/https/www prefix)
        if self.preserve.get("urls", True):
            result = self._protect(result, "url", segments)

        # 8. Email (BEFORE bare_domain so full email is protected as one unit)
        if self.preserve.get("emails", True):
            result = self._protect(result, "email", segments)

        # 9. Bare domains (site.com.ua, example.kh.ua, etc.)
        if self.preserve.get("urls", True):
            result = self._protect(result, "bare_domain", segments)

        # 10. HTML-теги (individual opening/closing tags)
        if self.preserve.get("html", True):
            result = self._protect(result, "html_tag", segments)

        # 8. Хэштеги
        if self.preserve.get("hashtags", True):
            result = self._protect(result, "hashtag", segments)

        # 9. Упоминания
        if self.preserve.get("mentions", True):
            result = self._protect(result, "mention", segments)

        # 10. Leader dots (оглавления, TOC)
        result = self._protect(result, "leader_dots", segments)

        # 11. Semantic values: dates, prices, versions, IDs, then generic numbers
        if self.preserve.get("prices", True):
            result = self._protect(result, "currency", segments)

        if self.preserve.get("dates", True):
            result = self._protect(result, "date", segments)

        if self.preserve.get("identifiers", True):
            result = self._protect(result, "version", segments)
            result = self._protect(result, "identifier", segments)

        # 12. Числа с единицами
        if self.preserve.get("numbers", True):
            result = self._protect_numbers(result, segments)

        # 13. Брендовые термины
        brand_terms = self.preserve.get("brand_terms", [])
        if brand_terms:
            result = self._protect_terms(result, brand_terms, segments, kind="brand_term")

        # 14. Ключевые слова для SEO
        keep_keywords = self.preserve.get("keep_keywords", [])
        if keep_keywords:
            result = self._protect_terms(result, keep_keywords, segments, kind="keep_keyword")

        # 15. Auto-detected multi-token entities. Run after explicit terms so
        # user-provided brand/keyword locks win over heuristic detection.
        if self.preserve.get("named_entities", True):
            result = self._protect(result, "named_entity", segments)

        return SegmentedText(text=result, segments=segments)

    def _protect(
        self,
        text: str,
        kind: str,
        segments: list[ProtectedSegment],
    ) -> str:
        """Защитить все вхождения паттерна."""
        pattern = _PATTERNS.get(kind)
        if not pattern:
            return text
        text_lower = text.lower()
        if kind == "html_block" and not any(
            marker in text_lower for marker in _HTML_BLOCK_CLOSE_MARKERS
        ):
            return text
        if kind == "html_list_item" and "</li" not in text_lower:
            return text
        placeholder_spans = [
            (match.start(), match.end())
            for match in _PLACEHOLDER_RE.finditer(text)
        ] if "\x00" in text else []

        def replacer(match: re.Match) -> str:
            start, end = match.start(), match.end()
            if placeholder_spans and any(
                span_start <= start and end <= span_end
                for span_start, span_end in placeholder_spans
            ):
                return match.group(0)
            placeholder = self._make_placeholder(kind)
            segments.append(ProtectedSegment(
                placeholder=placeholder,
                original=match.group(0),
                kind=kind,
            ))
            return placeholder

        return pattern.sub(replacer, text)

    def _protect_numbers(
        self,
        text: str,
        segments: list[ProtectedSegment],
    ) -> str:
        """Защитить числа."""
        def replacer(match: re.Match) -> str:
            if _inside_existing_placeholder(text, match.start(), match.end()):
                return match.group(0)
            placeholder = self._make_placeholder("number")
            segments.append(ProtectedSegment(
                placeholder=placeholder,
                original=match.group(0),
                kind="number",
            ))
            return placeholder

        return _NUMBER_PATTERN.sub(replacer, text)

    def _protect_terms(
        self,
        text: str,
        terms: list[str],
        segments: list[ProtectedSegment],
        *,
        kind: str = "brand_term",
    ) -> str:
        """Защитить конкретные термины."""
        unique_terms = dict.fromkeys(term for term in terms if term)
        for term in sorted(unique_terms, key=len, reverse=True):
            if not term:
                continue
            escaped = re.escape(term)
            pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)

            def make_replacer(source: str) -> Callable[[re.Match[str]], str]:
                def replacer(match: re.Match) -> str:
                    if _inside_existing_placeholder(source, match.start(), match.end()):
                        return match.group(0)
                    placeholder = self._make_placeholder(kind)
                    segments.append(ProtectedSegment(
                        placeholder=placeholder,
                        original=match.group(0),
                        kind=kind,
                    ))
                    return placeholder
                return replacer

            text = pattern.sub(make_replacer(text), text)
        return text
