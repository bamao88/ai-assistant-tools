# AI_Assistant tools

Shared tool layer for the `AI_Assistant` workspaces. Business agents call tools from here instead of keeping private copies.

## Source of Truth

`registry.yaml` (schema v2) is canonical: skills, engines, vendor, var, and deprecated triggers. This `CLAUDE.md` is the agent-facing guide; `README.md` is the human-facing tour. Keep both aligned with the registry — do not duplicate the inventory into prose.

Validate inventory + skill install state:

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/scripts/check-tools.py
```

Install / repair `~/.claude/skills` symlinks (idempotent):

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/scripts/sync-skills.py
```

## Four-tier layout

```
skills/   first-party triggerable skills (each a dir with SKILL.md)
engines/  code/CLIs the skills call — NOT triggerable on their own
vendor/   external clones (own upstream git); some expose a skill
var/      runtime: state, output, data, logs, drafts, review (gitignored)
```

- **Skills live only in `skills/`** (first-party) or `vendor/` (external clones). `~/.claude/skills` holds **only symlinks**, created by `sync-skills.py` from the registry. Never hand-edit `~/.claude/skills`; edit the source under `skills/` and re-run sync.
- **`engines/` is code, never a trigger.** A skill references its engine by absolute path. Engine-local runtime (`data/`, `output/`) stays beside the engine but is gitignored.
- **`var/` is the only home for runtime/scratch/credentials.** Nothing under `var/` is code; all of it is gitignored.
- **`vendor/` clones keep their own upstream git** and are gitignored by the parent repo (avoid nested-repo conflicts).
- Naming: directories are kebab-case; the single skill file is always `SKILL.md` (no `.claude.md` / `.openclaw.md` variants).
- Business agents are read-only against tools unless the user explicitly asks for a tool fix.

## Skill layering

- **L1 verb routers** (cross-platform entry points): `platform-fetch` (抓取), `platform-publish` (发布). These are thin routers — a `SKILL.md` + `references/<platform>.md` that dispatch to engines. They are the ONLY entry for their verb.
- **L2 workflows**: `blogger-research`, `xhs-ops`, `video-content`, `deep-research`.
- **atomic / util**: `xhs-auth`, `xhs-interact`, `markdown-to-cards`, `find-images`, `humanizer`.

Trigger competition is fixed only by "super-skill + remove lower triggers" (changing descriptions does not work). Do not re-create deprecated triggers (see `registry.yaml: deprecated`): the publish skills `xhs-publish` / `gzh-publish` / `wechatsync` were folded into `platform-publish`; the fetch skills `xhs-fetch` / `gzh-scraper` / `tencent-meeting-downloader` / `content-research-hub` into `platform-fetch`.

## Maintenance workflow

1. Read pending reports under `feedback/`.
2. Reproduce against the owning engine/skill.
3. Patch only the relevant tool + its docs; update `registry.yaml` if structure changes.
4. Run `scripts/check-tools.py` (and `sync-skills.py` if skill links changed).
5. Record the outcome in the feedback file.

Do not modify unrelated tools or other agents' `CLAUDE.md` files while maintaining this directory.
