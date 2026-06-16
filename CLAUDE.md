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

## Video editing skill (口播切片成片)

To update or iterate the video editing skill — the 口播 → 框架页竖版切片成片 line, built as four engines (`video-compose` 组合层 + `video-slicer` / `video-framework-render` / `video-clip` 积木厂) — **read [`doc/video-skill-architecture.md`](doc/video-skill-architecture.md) first**. It is the maintenance runbook: where files live, how to add a capability / change per-account customization (`profiles/`) / onboard a new account / change visual layout, the entry commands (`engines/video-compose/{selector,run}.py`), and how to verify no-regression (G4 baseline in `var/zh_main/baseline/`). Design decisions and migration history: `doc/plan/video-tools-migration-plan.md`.

## Customer management skill (学员管理)

To update or iterate the customer-management skill — the 微信现场 ↔ 飞书客户管理表对齐这条线, built as one engine (`engines/customer-management/`) organized as **4 capabilities + task cards + 7 recipes** — **read [`doc/customer-management-architecture.md`](doc/customer-management-architecture.md) first**. It is the maintenance runbook: where code (tools) vs business data (`assistant_zh/student_manage/`, bridged by `config.py`) live, how to change a 判定口径 by editing `cards/*.md` (no code) / add a task card / change write-back policy (`write_policy.py`) / add a command (`__main__.py` `_DISPATCH`), the entry commands (`python3 -m customer-management <cmd>`), the 写回授权门 red lines (`--apply`, employment/profile `--dry-run` first), and the pending acceptance gates. Migration history: memory `customer-management-migration`.

## Plan location

All maintenance / iteration plans for any skill or engine live under **`doc/plan/`** (kebab-case `.md`, one file per effort, e.g. `doc/plan/video-tools-migration-plan.md`). Before starting work, write the plan there; do not scatter plan docs into skill/engine dirs, `var/`, or the repo root. `doc/` itself holds cross-cutting runbooks (e.g. `video-skill-architecture.md`); `doc/plan/` holds the planning/migration docs.

## Maintenance workflow

1. Read pending reports under `feedback/`.
2. Reproduce against the owning engine/skill.
3. Patch only the relevant tool + its docs; update `registry.yaml` if structure changes.
4. Run `scripts/check-tools.py` (and `sync-skills.py` if skill links changed).
5. Record the outcome in the feedback file.

Do not modify unrelated tools or other agents' `CLAUDE.md` files while maintaining this directory.
