# MetaAutomate Open Source Governance

## Maintainer and reviews

Initial lead maintainer: @AhmadibOfficial. This is a maintainer-led project, not a foundation-managed project. Community proposals are welcome. Maintainers have final responsibility for changes merged into the canonical repository.

## Decision process

Use GitHub issues for feature proposals and pull requests for implementation. Significant cross-architecture decisions should first be recorded as a design note describing objectives, alternatives, permission boundaries, rollout and rollback. A merge requires review, tests and documentation.

The project will expand governance as more regular maintainers emerge; contributor roles and review permissions should be earned through consistent, trustworthy work.

## Release discipline

- Release planning core separately from production-private infrastructure.
- Tag only verified, documented code with known license and dependency provenance.
- Avoid enabling DRAFT capabilities as a shortcut to claims of autonomy.
- Never automatically deploy or migrate a real customer database from a community pull request.
- Maintain public changelogs and clearly distinguish future aspirations from actual features.

## Copyright and monetization

The currently checked-in LICENSE contains GNU GPL version 2. There is no blanket copyright assignment from outside contributors. Changing licensing or granting a separate proprietary/dual license on community-authored code may require permission from the relevant copyright holders.

An open-source codebase can still support paid operations, implementation services, support and hosted offerings; commercial arrangements do not diminish rights conferred by the applicable open-source license. Trademark/branding rights and assets require separate review. Do not claim a new license or exclusive brand permission solely through this document.
