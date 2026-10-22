---
name: assistant_wxp_self_xhs-cover
description: Generate, edit, and package Xiaohongshu cover images for WXP's personal account using the established black + hot-pink cute-cool personal IP style. Use when the user asks to make, revise, choose, or finalize a 小红书封面 for WXP AI workflow, Skill 拆解, Codex, automation, or personal AI practice notes.
---

# WXP 小红书封面

## Overview

Use this skill to keep WXP personal-account Xiaohongshu covers consistent: huge title first, tool relationship second, person third, black + hot pink as the series identity.

When the task requires image generation or image editing, also use the system `imagegen` skill/tool. Treat this skill as WXP-specific cover direction, not as a replacement for `imagegen`.

## Default Output

For a new cover, generate three variants unless the user asks for only one:

1. Personal IP variant: person larger, clear face, phone or prop in hand.
2. Workflow variant: WeChat/tool -> AI -> result relationship most readable.
3. Alternate composition: person position and gesture changed from recent covers.

For edits to a chosen cover, make the smallest targeted change and preserve all text/layout invariants.

## Visual Rules

- Palette: near-black/black background, hot pink `#ff4fa3` or `#ff2f8f`, large white text, tiny green only for WeChat.
- Style: cute but cool, personal creator account, not enterprise SaaS.
- Hierarchy: title takes 45%-60% of the cover; icon relationship comes second; person is the anchor but not the main information.
- Structure: show a simple relationship such as WeChat -> AI robot -> customer list/result card.
- Person: keep WXP-like personal IP feeling; rotate person position, scale, expression, and gesture across posts.
- Identity reference: when a cover includes WXP's face, use original real WXP photos/video stills as `referenced_image_paths`; do not use a previous AI-generated cover as the person identity reference. AI cover-to-cover chaining causes identity drift.
- Portrait generation mode: for new covers, treat original WXP images as feature references to understand and redraw WXP; do not paste, trace, freeze, or directly reuse face pixels from the original photo. Preserve the recognizable feature set instead of locking a literal photo cutout.
- Portrait retouching mode: for edits to an already selected cover, preserve face shape, eyes, nose, lips, glasses, bangs, and hair identity. Skin may be naturally improved, and clothing may change to fit the cover style. Avoid idol-face beautification, V-shaped chin, big eyes, heavy makeup, glossy lips, or changing glasses shape.
- Eyes/expression: keep WXP's natural eye shape, but add subtle natural catchlights, focused gaze, and a slight warm expression. Avoid dull empty stare, over-bright anime eyes, thick lashes, or changing eye size.
- Avoid repeating the same hand gesture or person position across consecutive covers.
- Avoid office scenes, desks, laptops, corporate dashboards, stock-photo lighting, and overly realistic customer-data screens.
- Do not copy another creator's exact layout, costume, prop, or visual assets. Extract only broad principles.

## Copy Rules

Keep cover copy short. Prefer two-line main titles.

Do not put these words on the cover or in public CTA copy:

- 评论区
- 留言
- 关键词
- 领取
- 私信
- 扫码

Use safer resource CTAs:

- `附Skill资料包`
- `附资料包`
- `附搭建清单`

Historical example — WeChat customer-management note (use only for that item; new topics use their own confirmed brief):

- Main title: `2000+微信客资` / `AI帮我管`
- Small label: `客户管理Skill`
- Bottom CTA: `附Skill资料包`
- Publish title: `我做了个 Skill，让 AI 管 2000+ 客资`

## Workflow

1. Locate the active content item if working inside `assistant_wxp_self`: check `state/content_index.yaml` and `content/items/<content_id>/`.
2. Read the current account’s `publish_<account>.md` first when present; it is the editable source for title, body, tags and selected cover. Legacy `publish_assets/xiaohongshu/{title.txt,description.txt,publish_command.md}` files are historical input or derived exports only; do not maintain a second publishing-field copy.
3. Align copy first. Confirm or choose main title, small label, CTA, and publish title before generating final cover.
4. Locate identity references before generating a person cover. Prefer `content/materials/identity_reference/` and the current item `publish_assets/xiaohongshu/identity_reference/`; if no original WXP reference exists, stop and ask for one instead of using old AI covers.
5. Use `imagegen` for raster generation/editing. For local edit targets, inspect the image with `view_image` before calling `imagegen`.
6. Generate three variants for new covers. For selected-cover edits, edit only the requested region and repeat invariants in the prompt.
7. Save project-bound results into `content/items/<content_id>/publish_assets/xiaohongshu/`.
8. Create both source PNG and Xiaohongshu upload JPG:
   - source: descriptive `.png`
   - upload: same stem with `_upload.jpg`
   - upload size: `1080x1440`
9. Inspect the final image visually and verify dimensions with `sips -g pixelWidth -g pixelHeight`.
10. Write the selected upload JPG path back to the current account’s `publish_<account>.md` (or its existing canonical project field). Regenerate any needed export files from that source. If the task only asks for local cover creation, report the selected asset without inventing or uploading a publishing package.

## Prompt Template

For a new cover:

```text
Use case: ads-marketing
Asset type: Xiaohongshu vertical video cover, 3:4 portrait.
Primary request: Create a WXP personal-account cover in the established black + hot-pink cute-cool style for: <topic>.
Input images: Image 1/2 are original real WXP identity references. Use them only for WXP's face identity. Do not infer identity from any previous AI-generated cover.
Generation mode: understand WXP's feature set from the input images, then redraw a polished cover portrait. Do not paste, trace, freeze, or directly reuse the original face pixels.
Scene/backdrop: near-black background, hot-pink neon glow, small cute doodles, no office or corporate dashboard.
Subject: WXP from the original references, round brown metal glasses, straight black bangs, natural tied-back dark hair, soft round face, natural eyelids and eye shape with subtle catchlights, focused gaze, natural nose and lips; clothing may change to fit the cover; <variant-specific pose/position>.
Composition: huge title in the upper 45%-60%; show <tool/source> -> AI robot -> <result> relationship with pink arrows; person is third priority.
Color palette: black, white, hot pink; tiny green only for WeChat if needed.
Text (verbatim): main title "<line 1>" and "<line 2>"; small label "<label>"; bottom CTA "<CTA>".
Typography: oversized bold Chinese display font, white with black shadow and hot-pink neon outline; highlight "AI" or "Skill" in pink.
Constraints: preserve recognizable WXP identity as a feature set; natural skin may be improved and clothing may change; eyes should look alive with natural catchlights and a slight warm expression; exact text only; no extra text; no real customer data, names, phone numbers, QR codes, watermarks, or sensitive CTA words.
Avoid: 评论区, 留言, 关键词, 领取, 私信, 扫码, old AI covers as person references, direct photo cutout, frozen original face pixels, office scenes, repeated pose from recent covers, idol-face beautification, V-shaped chin, big eyes, heavy makeup, dull empty stare.
```

For a local edit:

```text
Use case: precise-object-edit
Asset type: Xiaohongshu cover image edit.
Input image: Image 1 is the edit target.
Primary request: Edit only <requested region/change>.
Constraints: change only <region>; keep face identity, pose, text, icons, arrows, typography, layout, colors, and 1080x1440 composition unchanged. Skin can be naturally improved and clothing can change only if requested. If editing eyes, keep the original eye shape while adding subtle natural catchlights and a focused gaze.
Text invariants: preserve all visible text exactly: "<text 1>", "<text 2>", "<label>", "<CTA>".
Avoid: changing identity, moving elements, adding text, misspelling Chinese text, changing the selected cover's overall style, dull empty stare, oversized anime eyes.
```
