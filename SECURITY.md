# Security Policy

TextHumanize processes user text locally and is designed to avoid network calls
in the default path. Security reports are still important because the project
ships parsers, CLI tools, web/API examples, PHP and TypeScript ports, and text
normalization logic that may be embedded in production systems.

## Supported Versions

| Version | Status |
| ------- | ------ |
| `0.28.x` | Supported |
| `< 0.28` | Best-effort fixes only |

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.

Preferred reporting channels:

- GitHub private vulnerability reporting, if available for this repository.
- Email: ksanyok@me.com

Include as much detail as you safely can:

- Affected package or surface: Python, PHP, TypeScript, WordPress plugin, CLI,
  REST API, Docker image, documentation example, or build/release tooling.
- A minimal proof of concept or reproduction steps.
- Expected impact, such as denial of service, data exposure, path traversal,
  code execution, dependency confusion, or unsafe HTML/Markdown handling.
- Version, commit hash, operating system, and runtime versions.

Do not include confidential third-party text unless you have permission to share
it. Redacted or synthetic samples are preferred.

## Response Targets

- Initial acknowledgement: within 7 days.
- Triage decision: within 14 days when enough information is provided.
- Fix timeline: depends on severity, exploitability, and release scope.

## Scope

In scope:

- ReDoS or CPU/memory exhaustion from crafted text inputs.
- Unsafe file, path, archive, or model-weight handling.
- Unsafe HTML, Markdown, or Unicode normalization behavior that can cause XSS,
  spoofing, data loss, or security boundary confusion in integrations.
- CLI, REST API, Docker, WordPress, PHP, TypeScript, or CI/CD vulnerabilities.
- Supply-chain issues in release artifacts or package metadata.

Out of scope:

- Generic requests to bypass external AI detectors.
- Claims that a detector verdict is inaccurate without a security impact.
- Social engineering, spam, or automated abuse against project maintainers.
- Denial-of-service tests against public project infrastructure without prior
  approval.

## Safe Harbor

Good-faith security research is welcome when it avoids privacy violations,
service disruption, data destruction, and public disclosure before maintainers
can investigate. We will not pursue action against researchers who follow this
policy and report responsibly.
