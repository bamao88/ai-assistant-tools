# Prompt Assembly Guide

Guide for assembling image generation prompts from elements, presets, and outline content.

本包适配：本文的参数名仅表示创作选择，不是可执行CLI。下面伪代码描述组装逻辑，无需寻找脚本。画幅以本轮要求为准，3:4只是原例；原系列约4:5。中文清楚优先，正文标题不沿用封面比例。以大纲确定的阅读任务、图文分工和同屏关系为准，不按预设要点数量重新删写内容；人物、幽默和情绪停顿可以是画面的任务。工具操作见本包 [生成与交付](../generation.md)。

组装前确认大纲已写清已有理解、推进依据与预期新理解；若只有反复强调的结论，先回到该页大纲补依据或去复述，不交给生图模型现场编写知识。把理解推进和图文配合放入不上图的Context；逐字文案、示意标识和关系图含义明确给出。成图应保留这些关系，不要求每页采用相同结构。

当解释必须观察产物细节时，才放大例子，并写明需要实际看见的差别：如哪条边界、哪一部分超出、哪个结果改变动作，而不只写“画一张有问题的表格”。结论标签和圈注不能代替现象本身；小尺寸下复杂细节不清楚时，选择更清楚的参照表达同一关系。讲机制时，优先用简单关系图，把例子附在对应节点或短段；不能因“更具体”就自动画一整页界面。

把大纲的主次关系明确传入prompt：标题与主要节点表达什么，哪些文字仅是本例、哪些不需要画成产物。为每条有意义的箭头写清起点、终点及条件；交付节点不擅自加出边，正常继续操作不改成失败重试。参考图只继承明确指定的角色、笔触、字体或配色，不能连带复制内容骨架、人物摆放和每页问答。

## Base Prompt Structure

Every XHS infographic prompt follows this structure:

```
Create a Xiaohongshu (Little Red Book) style infographic following these guidelines:

## Image Specifications

- **Type**: Infographic
- **Orientation**: Portrait (vertical)
- **Aspect Ratio**: {aspect_ratio_from_outline}
- **Style**: {selected_style_from_outline}

## Core Principles

- Follow the selected rendering style; preserve supplied real artifacts when the outline needs them as evidence, and do not fabricate screenshots
- Use the characters and reference roles specified for this task; do not invent extra identities
- Preserve complete explanatory sentences from the outline; never replace them with slogans or labels to make space for character scenes
- Use spacing and hierarchy appropriate to this page; keep Chinese readable without dropping needed comparisons, character reactions, or emotional pauses
- Maintain clear visual hierarchy; prioritize complete prose and explanatory diagrams. Use lightweight hand-drawn speech bubbles for specified human–AI dialogue, with tails pointing to the correct speakers. Preserve engaging character interaction without crowding the explanation
- Identify speakers through their characters and bubble tails. Do not print redundant “人：” or “AI：” prefixes before dialogue; keep speaker attribution in separate, non-printed instructions
- Preserve the planned progression from prior understanding through the specified example or evidence to the new understanding. Do not add paraphrased conclusions, invented evidence, or a second explanation that merely repeats the approved content

## Text Style (CRITICAL)

- Preserve the selected lettering character; Chinese body text must remain clear and legible
- Main titles should be prominent and eye-catching
- Key text should be bold and enlarged
- Use highlighter effects to emphasize keywords
- Avoid decorative letterforms that make Chinese text hard to read

## Language

- Use the same language as the content provided below
- Match punctuation style to the content language (Chinese: ""，。！)

---

{STYLE_SECTION}

---

{LAYOUT_SECTION}

---

{CONTENT_SECTION}

---

{WATERMARK_SECTION}

---

Generate one complete card with the image tool available in this session.
```

## Style Section Assembly

选用本包预设时，从 `../presets/{style}.md` 提取下面的项目。使用 `style: custom` 时直接读取 outline 中已写明的画风和参考图约定，不寻找不存在的 custom.md；不要把自定义风格覆盖回某个预设。

```markdown
## Style: {style_name}

**Color Palette**:
- Primary: {colors}
- Background: {colors}
- Accents: {colors}

**Visual Elements**:
{visual_elements}

**Typography**:
{typography_style}
```

### Screen-Print Style Override

When `style: screen-print`, adapt rendering and typography with the following choices. Retain the general requirements for exact copy, readable Chinese, source boundaries and page purpose; a style override must not remove them:

```
## Core Principles

- Screen print / silkscreen poster art — flat color blocks, NO gradients
- Bold silhouettes and symbolic shapes over detailed rendering
- Negative space as active storytelling element
- Keep the specified character identity and relationships while simplifying their rendering
- One iconic focal point per image — conceptual, not literal

## Color Rules (CRITICAL)

- **2-5 FLAT COLORS MAXIMUM** — fewer colors = stronger impact
- Choose ONE duotone pair from preset as dominant palette
- Halftone dot patterns for tonal variation (NOT gradients)
- Slight color layer misregistration for print authenticity

## Text Style (CRITICAL)

- Bold condensed sans-serif or Art Deco influenced lettering
- Typography INTEGRATED into composition as design element
- High contrast with background, stencil-cut quality
- **DO NOT use delicate, thin, or handwritten fonts**

## Composition

- Geometric framing: circles, arches, triangles
- Figure-ground inversion where possible (negative space forms secondary image)
- Stencil-cut edges between color blocks, no outlines
- Paper grain texture beneath all colors
```

## Palette Override

When `--palette` is specified (or style has `default_palette` in frontmatter and no explicit `--palette`), palette colors **replace** the style's Color Palette in the prompt. Style rendering rules (Visual Elements, Typography, Style Rules) remain unchanged.

Load from `../palettes/{palette}.md` and override:

```markdown
## Palette Override: {palette_name}

**Background**: {palette background color and hex}

**Colors**:
- Text: {text color and hex}
- Secondary: {secondary text color and hex}
- Zone 1: {zone color and hex}
- Zone 2: {zone color and hex}
- Zone 3: {zone color and hex}
- Zone 4: {zone color and hex}
- Accent: {accent color and hex}

**Constraint**: {semantic constraint from palette}
```

**Override rules**:
1. Palette Background **replaces** style's background color (keep style's texture description)
2. Palette Colors **replace** style's Color Palette section entirely
3. Palette Semantic Constraint is appended to the style section
4. If no `--palette` and style has `default_palette` → load that palette
5. If no `--palette` and no `default_palette` → use style's built-in colors (no override)
6. Explicit `--palette` always overrides style's `default_palette`

## 图示与排版取舍

只组装大纲中已经通过必要性检查的图示，不替正文自动补图标、文件、书本或角色。保留阅读趣味与解释价值：对白、例子、人物反应、结构与流程图可以共同解释，也可以共同产生趣味，不固定各自只能承担一种作用。指定的角色对话用自然手绘气泡，用于明确说话关系，不等同于给每段文字套框。角色和气泡尾巴已经表明说话人，成图对白不再添加“人：”“AI：”标签；大纲里的说话归属放入不上图的提示说明，不混入逐字对白。正文以自然段落和小标题排列，边框与背景块只在确有分组需要时少量使用；关系清楚时可以没有框。参考图中较重的版式不能覆盖用户本轮轻排版要求。

## Layout Section Assembly

Load from `../elements/canvas.md` and extract relevant layout:

```markdown
## Layout: {layout_name}

**Information Density**: {density}
**Spacing**: {spacing_needed_for_the_approved_content}

**Structure**:
{structure_description}

**Visual Balance**:
{balance_description}
```

## Content Section Assembly

From outline entry:

```markdown
## Content

**Position**: {Cover/Content/Ending}
**Core Message**: {message}

**Text Content**:
{text_list}

**Visual Concept**:
{visual_description}

**Context (not printed on the card)**:
{page_group_relation_and_reference_roles}
{prior_understanding_example_or_evidence_and_intended_new_understanding_from_outline}
{how_the_planned_text_dialogue_and_visuals_advance_that_understanding_without_redundant_restatements}
{source_boundaries_and_which_artifacts_are_actual_or_illustrative}
**Speaker attribution (not printed on the card)**:
{speaker_and_bubble_tail_target_for_each_utterance_in_order}
Keep this attribution separate from the exact dialogue text. Show speakers through characters and bubble tails, without printing “人：” or “AI：” before their words.
Keep recurring examples, labels and color meanings consistent. Preserve source and uncertainty boundaries; do not turn parallel options into causal steps.
```

## Watermark Section (if enabled)

```markdown
## Watermark

Include a subtle watermark "{content}" positioned at {position}. The watermark should
be legible but not distracting from the main content.
```

## Assembly Process

### Step 0: Resolve Style Preset (if `--preset` used)

If user specified `--preset`, resolve to style + layout + palette from `../style-presets.md`:

```python
# e.g., --preset hand-drawn-edu → style=sketch-notes, layout=flow, palette=macaron
style, layout, palette = resolve_preset(preset_name)
```

Explicit `--style`/`--layout`/`--palette` flags override preset values.

### Step 1: Load Style Definition

```python
preset = outline.custom_style if style_name == "custom" else load_preset(style_name)
```

Extract:
- Color palette (may be overridden by palette)
- Visual elements
- Typography style
- Best practices (do/don't)
- `default_palette` from frontmatter (if present)

### Step 1.5: Apply Palette Override (if applicable)

```python
# Priority: explicit --palette > preset palette > style default_palette > none
palette = resolve_palette(cli_palette, preset_palette, style_default_palette)
if palette:
    palette_def = load_palette(palette)  # e.g., "macaron"
    # Replace style colors with palette colors
    # Keep style rendering rules (visual elements, typography, style rules)
```

### Step 2: Load Layout

```python
layout = get_layout_from_canvas(layout_name)  # e.g., "dense"
```

Extract:
- Information density guidelines
- Spacing needed to preserve reading order and legibility
- Structure description
- Visual balance rules

### Step 3: Format Content

From outline entry, format:
- Position context (Cover/Content/Ending)
- Text content with hierarchy
- Visual concept description
- Page-group relation, fixed references, source boundaries and reference-image roles (for context, not printed text)
- Understanding progression and the role of each planned text/visual component, from outline Context (not printed); do not invent missing explanations or require every page to use questions or reversals
- Exact illustrative labels for hypothetical documents or interfaces; distinguish them from actual artifacts used as evidence

### Step 4: Add Watermark (if applicable)

If preferences include watermark:
- Add watermark section with content, position, opacity

### Step 5: Visual Consistency — Reference Image Chain

When generating multiple images in a series:

1. **Visual anchor**: Choose a representative page for this task. It can be a body card when character interaction and text density need to be established; it need not be the cover. Use supplied style or character references where applicable.
2. **Remaining pages**: Provide the anchor through the current image tool's reference-image input, adding an appropriate body or cover reference only as needed. State each image's role and preserve final page numbering even if generation order differs. Use this package's `../generation.md` for tool handling; do not invoke another skill.
3. Preserve character and rendering consistency while allowing each page its own layout. Check the actual result; the reference chain is not a consistency guarantee.

### Step 6: Combine

Assemble all sections into final prompt following base structure.

## Example: Assembled Prompt

仅示范字段组装；真实任务替换内容、画幅、风格和署名，不能把示例自动补入成图。

```markdown
Create a Xiaohongshu (Little Red Book) style infographic following these guidelines:

## Image Specifications

- **Type**: Infographic
- **Orientation**: Portrait (vertical)
- **Aspect Ratio**: {aspect_ratio_from_outline}
- **Style**: {selected_style_from_outline}

## Core Principles

- Follow the selected rendering style; preserve supplied real artifacts when the outline needs them as evidence, and do not fabricate screenshots
- Use the characters and reference roles specified for this task; do not invent extra identities
- Preserve complete explanatory sentences from the outline; never replace them with slogans or labels to make space for character scenes
- Use spacing and hierarchy appropriate to this page; keep Chinese readable without dropping needed comparisons, character reactions, or emotional pauses
- Maintain clear visual hierarchy; prioritize complete prose and explanatory diagrams. Use lightweight hand-drawn speech bubbles for specified human–AI dialogue, with tails pointing to the correct speakers. Preserve engaging character interaction without crowding the explanation

## Text Style (CRITICAL)

- Preserve the selected lettering character; Chinese body text must remain clear and legible
- Main titles should be prominent and eye-catching
- Key text should be bold and enlarged
- Use highlighter effects to emphasize keywords
- Avoid decorative letterforms that make Chinese text hard to read

## Language

- Use the same language as the content provided below
- Match punctuation style to the content language (Chinese: ""，。！)

---

## Style: Notion

**Color Palette**:
- Primary: Black (#1A1A1A), dark gray (#4A4A4A)
- Background: Pure white (#FFFFFF), off-white (#FAFAFA)
- Accents: Pastel blue (#A8D4F0), pastel yellow (#F9E79F), pastel pink (#FADBD8)

**Visual Elements**:
- Simple line doodles, hand-drawn wobble effect
- Geometric shapes, stick figures
- Spacing fitted to the approved content, single-weight ink lines
- Clean, uncluttered compositions

**Typography**:
- Clean hand-drawn lettering
- Simple sans-serif labels
- Minimal decoration on text

---

## Layout: Dense

**Information Density**: Match the approved outline; do not invent or remove points to meet a quota
**Whitespace**: Enough separation to read the actual content on a phone; no fixed percentage

**Structure**:
- Multiple sections, structured grid
- More text, compact but organized
- Title + multiple sections with headers + numerous points

**Visual Balance**:
- Organized grid structure
- Clear section boundaries
- Compact but readable spacing

---

## Content

**Position**: Content (Page 3 of 6)
**Core Message**: ChatGPT 使用技巧

**Text Content**:
- Title: 「ChatGPT」
- Subtitle: 可以尝试的任务
- Points:
  - 写文案：提供背景与要求，请它起草
  - 改文章：润色、翻译、总结
  - 编程：写代码、找 bug
  - 学习：解释概念、出题练习

**Visual Concept**:
四项任务在浅色背景中清楚分组；各用小幅动作示意配合文字，沿用本例的黑灰线条与浅色强调，不另加深色霓虹画风。

---

## Watermark

Include a subtle watermark "@myxhsaccount" positioned at bottom-right
with approximately 50% visibility. The watermark should
be legible but not distracting from the main content.

---

Generate one complete card with the image tool available in this session.
```

## Prompt Checklist

Before generating, verify:

- [ ] Style matches the selected preset or the custom style recorded in the outline
- [ ] Palette override applied (if `--palette` specified or style has `default_palette`)
- [ ] Layout section matches outline specification
- [ ] Content accurately reflects outline entry
- [ ] For mechanism explanations, titles and main diagrams carry the general relationship; example details stay attached to the relevant part and retain their scope
- [ ] Diagram actors, edge direction and conditions are specified; normal continuation is not mislabeled as error correction
- [ ] The intended new understanding has a specified example, evidence or relationship; the prompt preserves it without adding repetitive conclusions
- [ ] Language matches source content
- [ ] Watermark included (if enabled in preferences)
- [ ] Page relationships, reference roles, humor and emotional pauses are preserved where planned
- [ ] Exact approved copy is used; no invented claims, dialogue or quota-driven omissions
- [ ] Speaker attribution stays outside printed dialogue; hypothetical artifacts retain the required “示意” label
- [ ] No conflicting instructions
