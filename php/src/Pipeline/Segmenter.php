<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

/**
 * Protected segment info.
 */
class ProtectedSegment
{
    public function __construct(
        public readonly string $placeholder,
        public readonly string $original,
        public readonly string $kind,
    ) {
    }
}

/**
 * Text with protected segments replaced by placeholders.
 */
class SegmentedText
{
    /** @var ProtectedSegment[] */
    public readonly array $segments;
    public readonly string $text;

    /**
     * @param ProtectedSegment[] $segments
     */
    public function __construct(string $text, array $segments)
    {
        $this->text = $text;
        $this->segments = $segments;
    }

    /**
     * Restore protected segments into processed text.
     */
    public function restore(string $processedText): string
    {
        // Pass 1: exact replacement (fast path)
        $segments = array_reverse($this->segments);
        foreach ($segments as $seg) {
            $processedText = str_replace($seg->placeholder, $seg->original, $processedText);
        }

        // Pass 2: tolerant recovery if placeholders were case-mutated or
        // null-byte wrappers were dropped by downstream string operations.
        foreach ($segments as $seg) {
            $bare = trim($seg->placeholder, "\x00");
            $pattern = '/(?:\x00)?' . preg_quote($bare, '/') . '(?:\x00)?/iu';
            $processedText = preg_replace($pattern, $seg->original, $processedText) ?? $processedText;
        }

        // Pass 3: strip orphaned placeholders/null bytes.
        $processedText = preg_replace('/(?:\x00)?THZ_[A-Z_]+_\d+(?:\x00)?/iu', '', $processedText) ?? $processedText;
        $processedText = str_replace("\x00", '', $processedText);

        return $processedText;
    }
}

/**
 * Segmenter — protects code blocks, URLs, emails, etc. from modification.
 */
class Segmenter
{
    private const INLINE_SAFE_PLACEHOLDER_KINDS = ['HTML'];

    private array $preserve;
    private int $counter = 0;

    public function __construct(array $preserve = [])
    {
        $this->preserve = array_merge([
            'code_blocks' => true,
            'urls' => true,
            'emails' => true,
            'hashtags' => true,
            'mentions' => true,
            'markdown' => true,
            'html' => true,
            'numbers' => false,
            'brand_terms' => [],
            'keep_keywords' => [],
        ], $preserve);
    }

    /**
     * Segment text, replacing protected elements with placeholders.
     *
     * @param string[] $keepKeywords
     * @param string[] $brandTerms
     */
    public function segment(string $text, array $keepKeywords = [], array $brandTerms = []): SegmentedText
    {
        $segments = [];
        $this->counter = 0;

        if (!empty($keepKeywords)) {
            $existing = $this->preserve['keep_keywords'] ?? [];
            $this->preserve['keep_keywords'] = array_values(array_unique([...$existing, ...$keepKeywords]));
        }
        if (!empty($brandTerms)) {
            $existing = $this->preserve['brand_terms'] ?? [];
            $this->preserve['brand_terms'] = array_values(array_unique([...$existing, ...$brandTerms]));
        }

        // Code blocks
        if ($this->preserve['code_blocks']) {
            $text = $this->protect($text, '/```[\s\S]*?```|~~~[\s\S]*?~~~/u', 'code_block', $segments);
            $text = $this->protect($text, '/`[^`\n]+`/u', 'inline_code', $segments);
        }

        // Markdown images (before links)
        if ($this->preserve['markdown']) {
            $text = $this->protect($text, '/!\[[^\]]*\]\([^)]+\)/u', 'md_image', $segments);
            $text = $this->protect($text, '/\[[^\]]*\]\([^)]+\)/u', 'md_link', $segments);
        }

        // URLs
        if ($this->preserve['urls']) {
            $text = $this->protect($text, '#https?://[^\s<>\])"\']+#u', 'url', $segments);
        }

        // Emails
        if ($this->preserve['emails']) {
            $text = $this->protect($text, '/[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/u', 'email', $segments);
        }

        // HTML tags
        if ($this->preserve['html']) {
            $text = $this->protect($text, '/<[^>]+>/u', 'html', $segments);
        }

        // Hashtags
        if ($this->preserve['hashtags']) {
            $text = $this->protect($text, '/#[a-zA-Z0-9_\p{L}]+/u', 'hashtag', $segments);
        }

        // Mentions
        if ($this->preserve['mentions']) {
            $text = $this->protect($text, '/@[a-zA-Z0-9_]+/u', 'mention', $segments);
        }

        // Brand terms
        if (!empty($this->preserve['brand_terms'])) {
            foreach ($this->preserve['brand_terms'] as $term) {
                $pattern = '/\b' . preg_quote($term, '/') . '\b/ui';
                $text = $this->protect($text, $pattern, 'brand', $segments);
            }
        }

        // Keep keywords (for SEO)
        $keepKeywords = $this->preserve['keep_keywords'] ?? [];
        if (!empty($keepKeywords)) {
            foreach ($keepKeywords as $kw) {
                $pattern = '/' . preg_quote($kw, '/') . '/ui';
                $text = $this->protect($text, $pattern, 'keyword', $segments);
            }
        }

        return new SegmentedText($text, $segments);
    }

    /**
     * Replace matches with placeholders.
     * @param ProtectedSegment[] $segments
     */
    private function protect(string $text, string $pattern, string $kind, array &$segments): string
    {
        return preg_replace_callback($pattern, function (array $m) use ($kind, &$segments): string {
            $this->counter++;
            $placeholder = "\x00THZ_" . strtoupper($kind) . "_{$this->counter}\x00";
            $segments[] = new ProtectedSegment($placeholder, $m[0], $kind);
            return $placeholder;
        }, $text) ?? $text;
    }

    /**
     * Return true when a line contains placeholders that should block
     * sentence-level stages. Inline HTML placeholders are allowed.
     */
    public static function hasBlockingPlaceholder(string $text): bool
    {
        if (!str_contains($text, "\x00THZ_")) {
            return false;
        }

        if (!preg_match_all('/\x00THZ_([A-Z_]+)_\d+\x00/iu', $text, $matches)) {
            // If markers are corrupted, be conservative.
            return true;
        }

        foreach ($matches[1] as $kind) {
            $kind = strtoupper((string) $kind);
            if (!in_array($kind, self::INLINE_SAFE_PLACEHOLDER_KINDS, true)) {
                return true;
            }
        }

        return false;
    }
}
