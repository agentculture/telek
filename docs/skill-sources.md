# Skill sources

Provenance ledger for the skills vendored under `.claude/skills/`. AgentCulture
follows a **cite, don't import** policy: each repo owns its copy and may
diverge intentionally. This file records who upstream is and whether the
local copy has drifted, so a future re-sync is a deliberate diff.

The canonical map across the whole AgentCulture mesh lives at
[`agentculture/steward` → `docs/skill-sources.md`](https://github.com/agentculture/steward/blob/main/docs/skill-sources.md).

| Skill           | Upstream                                                                                                | Vendored at | Local divergence |
|-----------------|---------------------------------------------------------------------------------------------------------|-------------|------------------|
| `cicd`          | [`steward/.claude/skills/cicd/`](https://github.com/agentculture/steward/tree/main/.claude/skills/cicd)                 | 0.1.0       | None (initial vendor). |
| `communicate`   | [`steward/.claude/skills/communicate/`](https://github.com/agentculture/steward/tree/main/.claude/skills/communicate)   | 0.1.0       | None (initial vendor). |
| `run-tests`     | [`steward/.claude/skills/run-tests/`](https://github.com/agentculture/steward/tree/main/.claude/skills/run-tests)       | 0.1.0       | None (initial vendor). |
| `sonarclaude`   | [`steward/.claude/skills/sonarclaude/`](https://github.com/agentculture/steward/tree/main/.claude/skills/sonarclaude)   | 0.1.0       | None (initial vendor). |
| `version-bump`  | [`steward/.claude/skills/version-bump/`](https://github.com/agentculture/steward/tree/main/.claude/skills/version-bump) | 0.1.0       | None (initial vendor). |
| `telegram`      | Original to telek — no upstream.                                                                                         | v0.2        | N/A (original).        |

## Re-sync procedure

To pull a fresh copy of a skill:

```bash
cp -r ../steward/.claude/skills/<name>/ .claude/skills/<name>/
bash .claude/skills/cicd/scripts/portability-lint.sh
```

Any local divergence (deliberate edit to a vendored script) must be
documented in the table above with a one-line reason — otherwise the next
re-sync will silently wipe it.
