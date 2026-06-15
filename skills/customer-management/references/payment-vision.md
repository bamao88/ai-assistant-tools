# 付款金额视觉读卡（`cards/payment.md`）

付款金额常藏在微信付款截图（v4 加密 .dat）里。本卡是**视觉读卡**，**与就业/画像卡不同**：

> ⚠️ 由 **agent（Claude）用自己的视觉能力读图**，**不走** `analyze/core.call_llm`。本 engine 的
> LLM 机器核（`knowledge_ingest.core.call_llm`）是**纯文本**通道（无 image_url / 多模态），不能读图。
> 历史上「视觉读 extract_payments」也一直是人/agent 逐张看 montage 定位付款页，从不是 API 调用。
> 故本卡 flow = `vision_agent`：`payment` 配方负责把图解出来拼成 montage，agent 按本卡逐张读，
> 再把结论写进 worksheet 交 `intake` 配方 / `outputs.intake_writer`。

## 用法

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines
# 取图片解密 key（首次：弹钥匙串授权，点「始终允许」）+ 批量解 + 拼九宫格
python3 -m customer-management payment --term 5期
# 或单人
python3 -m customer-management payment --wxid <wxid>
```

产物 montage（`montage/<昵称>.png`，每格左上角标 `#序号` + 文件名）落付款产物目录。
然后 **agent 用 Read 工具看 montage**，按 `cards/payment.md` 的 `VISION_PROMPT` 逐张定位「付款交易页」，
读出：金额（取整）+ 付款方式（转账/小鹅通/微信支付）+ 凭证图路径。

判定（`cards/payment.md` 写回策略：`实付`/`付款方式`/`提成截图凭证` 均 fill_only_if_empty）：
- ✅ 交易详情页 / 支付成功页
- ❌ 收款码 QR / SZplayer / 课程页 / 群聊
- 金额带小数（7899.50/8599.75 是真实到账含手续费/零头）→ 取整填（7900/8600）。
- 收款方/金额看不清 → 标「待复核」、实付留空、传证据图让用户 review，别写死。

读出后回填路径：写进 worksheet 的 `pay{amt,method,img}` → `intake --apply`（飞书 + 本地 all_student.json）。
编辑 `cards/payment.md`（如调整排除规则、改输出字段）立刻改变 agent 读图口径，不需要改 Python。

技术细节（.dat 解密、imgkey）：见 assistant_zh 记忆 `reference_wechat_image_dat_decrypt`。
