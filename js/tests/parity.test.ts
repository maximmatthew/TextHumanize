/**
 * Contract parity tests backed by fixtures shared with Python and PHP.
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { analyze, detectAi, humanize } from '../src/core';
import type { Profile } from '../src/types';

interface ParityCase {
  id: string;
  lang: string;
  profile: Profile;
  intensity: number;
  seed: number;
  text: string;
  preserve: {
    brand_terms: string[];
    keep_keywords: string[];
  };
  expected: {
    lang: string;
    min_words: number;
    min_sentences: number;
  };
}

const fixturePath = resolve(__dirname, '../../tests/fixtures/parity_cases.json');
const payload = JSON.parse(readFileSync(fixturePath, 'utf8')) as {
  schema_version: string;
  cases: ParityCase[];
};

describe('cross-runtime parity fixtures', () => {
  it('uses the expected fixture schema', () => {
    expect(payload.schema_version).toBe('text-humanize.parity.v1');
    expect(payload.cases.length).toBeGreaterThan(0);
  });

  for (const testCase of payload.cases) {
    it(`matches shared contract for ${testCase.id}`, () => {
      const result = humanize(testCase.text, {
        lang: testCase.lang,
        profile: testCase.profile,
        intensity: testCase.intensity,
        seed: testCase.seed,
        preserve: {
          brandTerms: testCase.preserve.brand_terms,
        },
        constraints: {
          keepKeywords: testCase.preserve.keep_keywords,
        },
      });

      expect(result.lang).toBe(testCase.expected.lang);
      expect(result.profile).toBe(testCase.profile);
      expect(result.text.trim().length).toBeGreaterThan(0);

      for (const term of [
        ...testCase.preserve.brand_terms,
        ...testCase.preserve.keep_keywords,
      ]) {
        expect(result.text).toContain(term);
      }

      const report = analyze(testCase.text, testCase.lang);
      expect(report.lang).toBe(testCase.expected.lang);
      expect(report.totalWords).toBeGreaterThanOrEqual(testCase.expected.min_words);
      expect(report.totalSentences).toBeGreaterThanOrEqual(testCase.expected.min_sentences);
      expect(report.artificialityScore).toBeGreaterThanOrEqual(0);
      expect(report.artificialityScore).toBeLessThanOrEqual(100);

      const detection = detectAi(testCase.text, testCase.lang);
      expect(['human_written', 'mixed', 'ai_generated']).toContain(detection.verdict);
      expect(detection.score / 100).toBeGreaterThanOrEqual(0);
      expect(detection.score / 100).toBeLessThanOrEqual(1);
    });
  }
});
