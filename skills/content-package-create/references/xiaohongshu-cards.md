# 小红书卡片图文制作

本说明供 `content-package-create` 在本地生成卡片图使用；不操作小红书发布页。

## 账号卡片样式映射（长文卡片）

小红书长文卡片支持像公众号一样按账号绑定固定样式。账号配置存放在 `~/.xhs/accounts.json` 的 `card_config` 字段；生成卡片时把同一个账号 slot 传给 `markdown-to-cards`：

```bash
node /Volumes/ExtSSD2601/AI_Assistant/tools/engines/markdown-to-cards/cli.js \
  --account <ACCOUNT> \
  --input "<files.cards_md_file>" \
  --output-dir "$OUTDIR"
```

当前固定映射：

| 账号 slot | 固定正文风格 | 栏目/页眉标签 | 封面 |
|---|---|---|---|
| `张和_专业号` | `unified-claude` | `张和 AI 产品实战派` | `cover_template=default`，即正文用共用模板，封面使用默认小红书封面 |

如果用户没有明确要求实验风格，不要覆盖账号配置。需要临时测试其他风格时，显式传 `--style` / `--cover-template` 等参数，显式参数优先于账号默认配置。

---

