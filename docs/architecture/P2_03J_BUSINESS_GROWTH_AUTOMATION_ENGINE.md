# P2-03j — Business Growth Automation Engine

**Engineering status: SOURCE_ONLY / OPERATIONAL NO-GO.**
Extends P2-03h with deterministic goal-relevant workflow proposals, source-only provider integration contracts, and subscription-readiness evidence. No authenticated client, deployed connector, billing, marketing or customer action.

## Customer-value contract

Product direction: businesses specify a measurable goal (contribution after costs, repeat orders, or completed orders); a governed engine identifies relevant journey events, distinguishes a review-worthy next action from unsupported or inappropriate activity, and produces a readable scorecard. The product must deliver verifiable efficiency or contribution before subscription billing can be offered.

Five bounded engineering work streams:

1. **Goals to workflows:** \`CONTRIBUTION\`, \`RETENTION\`, \`COMPLETED_ORDERS\`. The engine maps allowlisted synthetic events to proposed actions, deferrals, or suppressions. No runtime policy administration.
2. **Orchestration:** deterministic idempotency-like plan IDs, no delivery queue, task runner, provider calls, outbound messages or orders. All proposed work remains unapproved and non-executable.
3. **Provider contracts:** Selar commerce, Metricool publishing, and MailerLite communications are future-only contract sketches, requiring approved tenant identity and authorization, scopes, consent, deduplication and provider-specific behavior. Selar's provider-owned native abandoned-checkout follow-ups are always suppressed rather than duplicated.
4. **Economic measures:** invented gross sales minus variable costs minus marketing spend, contribution gap to a configured invented target, order and repeat counts. *No* actual profit, verified conversions, visit denominator, customer lifetime value or incremental-sales attribution.
5. **Commercial readiness:** Starter, Growth and Team research archetypes, without price, entitlement, service activation or billing. Validate time saved, controlled incremental contribution, subscription willingness-to-pay, consent compliance, support cost and customer retention before commercial offers.

## Verify source

\`\`\`bash
python -m pytest -q tests/test_synthetic_growth_orchestration.py
python scripts/verify_synthetic_growth_orchestration.py --report artifacts/validation/p2-03j-growth-orchestration-source.json
\`\`\`

All inputs come from committed bounded synthetic fixtures already validated by \`synthetic_growth_autopilot.parse_growth_fixture\`. No arbitrary customer files, tokens or provider credentials accepted.

**The website's polished Product Preview is distinct from live service claims.** P2-03j does not change the existing public website, interface code, capability registry, capability lifecycle history, billing, Render, migrations, tenant database or activated endpoints. Internal evidence uses explicit synthetic labels.

Foundational controls F04–F09 remain unverified; Phase 01 3/9. Phases 02–03 operational NO-GO; no live deployment or customer activation authorized. Source verification does not change release permissions.
