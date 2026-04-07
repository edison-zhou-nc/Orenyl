# Compliance Readiness

## Scope

This document summarizes Orenyl's public-launch posture for privacy, auditability, and governed-memory operations.

## GDPR-aligned coverage

- Erasure is supported through deterministic delete-and-recompute workflows and subject-level erasure flows.
- Export is supported through domain and subject portability endpoints.
- Article 30 style reporting is available through the processing record generator.

## Consent lifecycle

- Consent status changes are stored as explicit records.
- Consent checks are available for processing decisions by subject and purpose.
- Consent withdrawal is covered by the existing integration tests and documented operator flow.

## Retention

- Event expiration and TTL sweep behavior are configurable.
- Retention-oriented deletion can run in soft or hard modes.
- Tombstones and deletion proofs preserve governance evidence after erasure operations.

## Audit integrity

- Security decisions are audit logged.
- Lineage traces preserve derivation visibility from events to facts.
- Audit anomaly scanning supports post hoc investigation of suspicious access patterns.

## Remaining SOC 2 gaps

- SOC 2 evidence collection is not yet automated.
- Change management, key-management operations, and incident response runbooks need fuller operator packaging.
- Third-party vendor and infrastructure controls remain deployment-specific rather than product-enforced.
- Orenyl is not yet externally certified as an enterprise compliance product.
