<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\AIDetector;
use TextHumanize\TextHumanize;

class ParityFixturesTest extends TestCase
{
    /**
     * @return list<array<string, mixed>>
     */
    private function cases(): array
    {
        $path = dirname(__DIR__, 2) . '/tests/fixtures/parity_cases.json';
        $payload = json_decode((string) file_get_contents($path), true, 512, JSON_THROW_ON_ERROR);

        $this->assertSame('text-humanize.parity.v1', $payload['schema_version']);
        return $payload['cases'];
    }

    public function testPhpContractMatchesSharedParityFixtures(): void
    {
        foreach ($this->cases() as $case) {
            $expected = $case['expected'];
            $preserve = $case['preserve'] ?? [];
            $brandTerms = $preserve['brand_terms'] ?? [];
            $keepKeywords = $preserve['keep_keywords'] ?? [];

            $result = TextHumanize::humanize(
                $case['text'],
                lang: $case['lang'],
                profile: $case['profile'],
                intensity: $case['intensity'],
                preserve: ['brand_terms' => $brandTerms],
                constraints: ['keep_keywords' => $keepKeywords],
                seed: $case['seed'],
            );

            $this->assertSame($expected['lang'], $result->lang, $case['id']);
            $this->assertSame($case['profile'], $result->profile, $case['id']);
            $this->assertNotSame('', trim($result->processed), $case['id']);

            foreach (array_merge($brandTerms, $keepKeywords) as $term) {
                $this->assertStringContainsString(
                    $term,
                    $result->processed,
                    sprintf('%s lost protected term %s', $case['id'], $term),
                );
            }

            $report = TextHumanize::analyze($case['text'], $case['lang']);
            $this->assertSame($expected['lang'], $report->lang, $case['id']);
            $this->assertGreaterThanOrEqual($expected['min_words'], $report->totalWords, $case['id']);
            $this->assertGreaterThanOrEqual($expected['min_sentences'], $report->totalSentences, $case['id']);
            $this->assertGreaterThanOrEqual(0.0, $report->artificialityScore, $case['id']);
            $this->assertLessThanOrEqual(100.0, $report->artificialityScore, $case['id']);

            $detection = AIDetector::detectAi($case['text'], $case['lang']);
            $this->assertContains($detection->verdict, ['human', 'mixed', 'ai', 'unknown'], $case['id']);
            $this->assertGreaterThanOrEqual(0.0, $detection->aiProbability, $case['id']);
            $this->assertLessThanOrEqual(1.0, $detection->aiProbability, $case['id']);
            $this->assertGreaterThanOrEqual(0.0, $detection->confidence, $case['id']);
            $this->assertLessThanOrEqual(1.0, $detection->confidence, $case['id']);
        }
    }
}
