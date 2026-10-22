# assistant_zh｜多源深度研究

本目录是 `assistant_zh_deep-research` 的唯一维护源。Codex 项目原入口 `.agents/skills/deep-research` 以软链继续兼容；业务资料和报告留在 assistant_zh 项目。完整运行规则见 [SKILL.md](SKILL.md)。

## 来源与授权

基于 [199-biotechnologies/claude-deep-research-skill](https://github.com/199-biotechnologies/claude-deep-research-skill) 的本地项目定制版；迁移前本地仓库 HEAD `5d83cd7beaf3a1b1f6de020ccda2d84872a1e575`（含本地定制，文件快照见 [SOURCE.json](SOURCE.json)）。原 README 声明 MIT，原包未附单独 LICENSE 文件；保留文末原授权声明。迁移时保留 references、脚本、模板、schemas 和 tests，未复制嵌套 `.git`、Python 缓存或研究业务产物。

## 依赖

基础脚本主要使用 Python 标准库；按实际输出需要读取 [requirements.txt](requirements.txt)，HTML / PDF 相关依赖为可选。搜索必须使用本会话实际提供的工具，下面保留上游的可选搜索 CLI 说明；配置密钥仅存本地。

### Optional: search-cli (multi-provider search)

For aggregated search across Brave, Serper, Exa, Jina, and Firecrawl:

```bash
brew tap 199-biotechnologies/tap && brew install search-cli
search config set keys.brave YOUR_KEY  # configure at least one provider
```

## Usage

```
deep research on the current state of quantum computing
```

```
deep research in ultradeep mode: compare PostgreSQL vs Supabase for our stack
```

## Research Modes

| Mode | Phases | Duration | Best For |
|------|--------|----------|----------|
| Quick | 3 | 2-5 min | Initial exploration |
| Standard | 6 | 5-10 min | Most research questions |
| Deep | 8 | 10-20 min | Complex topics, critical decisions |
| UltraDeep | 8+ | 20-45 min | Comprehensive reports, maximum rigor |

## Pipeline

Scope &rarr; Plan &rarr; **Retrieve** (parallel search + agents) &rarr; Triangulate &rarr; Outline Refinement &rarr; Synthesize &rarr; Critique (with loop-back) &rarr; Refine &rarr; Package

Key features:
- **Step 0**: Retrieves current date before searches (prevents stale training-data year assumptions)
- **Parallel retrieval**: 5-10 concurrent searches + 2-3 focused sub-agents returning structured evidence objects
- **First Finish Search**: Adaptive quality thresholds by mode
- **Critique loop-back**: Phase 6 can return to Phase 3 with delta-queries if critical gaps found
- **Multi-persona red teaming**: Skeptical Practitioner, Adversarial Reviewer, Implementation Engineer (Deep/UltraDeep)
- **Disk-persisted citations**: `sources.json` survives context compaction and continuation agents

## Output

Reports are saved to the active output directory:
- `content/deep_research/<YYYYMMDDHHMM>/`

Use local time and minute precision, for example:
- `content/deep_research/202605052104/`

Writing workflow invocations keep article files in `content/<persona>/items/<content_id>/` and write deep-research artifacts only to `content/deep_research/<YYYYMMDDHHMM>/`.

Artifacts:
- `report.md` (primary source of truth)
- `sources.jsonl`
- `evidence.jsonl`
- `claims.jsonl`
- `run_manifest.json`
- HTML (McKinsey-style, auto-opened in browser)
- PDF (professional print via WeasyPrint)

Reports >18K words auto-continue via recursive agent spawning with context preservation.

## Quality Standards

- 10+ sources, 3+ per major claim
- Executive summary 200-400 words
- Findings 600-2,000 words each, prose-first (>=80%)
- Full bibliography with URLs, no placeholders
- Automated validation: `validate_report.py` (9 checks) + `verify_citations.py` (DOI/URL/hallucination detection)
- Validation loop: validate &rarr; fix &rarr; retry (max 3 cycles)

## Search Tools

| Tool | Priority | Setup |
|------|----------|-------|
| search-cli | **Primary** — all searches go here first | `brew install search-cli` + API keys |
| WebSearch | Fallback — if search-cli fails or rate-limited | None (built-in) |
| Exa MCP | Optional — semantic/neural search alongside search-cli | MCP config |

## Architecture

```
assistant_zh_deep-research/
├── SKILL.md                          # Skill entry point (lean, ~100 lines)
├── reference/
│   ├── methodology.md                # 8-phase pipeline details
│   ├── report-assembly.md            # Progressive generation strategy
│   ├── quality-gates.md              # Validation standards
│   ├── html-generation.md            # McKinsey HTML conversion
│   ├── continuation.md               # Auto-continuation protocol
│   └── weasyprint_guidelines.md      # PDF generation
├── templates/
│   ├── report_template.md            # Report structure template
│   └── mckinsey_report_template.html # HTML report template
├── scripts/
│   ├── validate_report.py            # 9-check structure validator
│   ├── verify_citations.py           # DOI/URL/hallucination checker
│   ├── source_evaluator.py           # Source credibility scoring
│   ├── citation_manager.py           # Citation tracking
│   ├── md_to_html.py                 # Markdown to HTML converter
│   ├── verify_html.py                # HTML verification
│   └── research_engine.py            # Core orchestration engine
└── tests/
    └── fixtures/                     # Test report fixtures
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.3.1 | 2026-03-19 | Template/validator harmonization, structured evidence, critique loop-back, multi-persona red teaming |
| 2.3 | 2026-03-19 | Contract harmonization, search-cli integration, dynamic year detection, disk-persisted citations, validation loops |
| 2.2 | 2025-11-05 | Auto-continuation system for unlimited length |
| 2.1 | 2025-11-05 | Progressive file assembly |
| 1.0 | 2025-11-04 | Initial release |

## License

MIT - modify as needed for your workflow.
