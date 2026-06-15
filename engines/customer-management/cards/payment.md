---
name: payment
flow: vision_agent
gate: none
write_back:
  实付: fill_only_if_empty
  付款方式: fill_only_if_empty
  提成截图凭证: fill_only_if_empty
---

# 付款金额视觉读 — 任务卡（三要素，视觉读卡）

> 任务卡 = 怎么读（## VISION_PROMPT，下方）+ 要什么（## OUTPUT_CONTRACT 的 JSON 字段）+ 写回规矩（顶部 front-matter `write_back`，落 outputs/intake_writer 的 pay 字段）。
>
> **⚠️ 与就业/画像卡不同：这是一张「视觉读卡」，由 agent（Claude）用自己的视觉能力读图，
> 不走 `analyze/core.call_llm`。** 本 engine 的 LLM 机器核（knowledge_ingest.core.call_llm）
> 是**纯文本**通道（messages.content 只接受字符串，无 image_url / 多模态），不能读图。
> 历史上「视觉读 extract_payments」也一直是人/agent 逐张看 montage 定位付款页，从不是 API 调用。
> 故本卡的 flow = `vision_agent`：`recipes.payment` 负责把图解出来拼成 montage，agent 按本卡
> 逐张读 montage 出结论，再把结论写进 worksheet 交 `recipes.intake` / `outputs.intake_writer`。
> 编辑本卡（如调整排除规则、改输出字段）立刻改变 agent 的读图口径，不需要改 Python。
>
> **先过滤（gate=none）**：无确定性预过滤；recipes.payment 已按 学期/wxid 把目标学员的图解全、
> 拼成 montage/<昵称>.png，agent 只需对这些 montage 逐张视觉定位。

## VISION_PROMPT

```
你在看某学员微信里解密出来的图片九宫格拼图 montage/<昵称>.png（每格左上角标了 #序号 与文件名）。
目标：找出「付款交易页」并读出金额 + 渠道。

判定「付款交易页」的正向特征（命中任一即高度可疑）：
  - 页面标题含「交易详情 / 支付成功 / 已支付 / 转账」
  - 有一个醒目的大额数字（￥xxxx），通常居中
  - 收款方 = 「张和 / All in AI / AI产品训练营」相关字样

排除（这些不是学员付款，绝不取数）：
  - 助理/张和的「收款码 / 二维码 QR」截图
  - SZplayer / 课程播放页 / 课程目录页
  - 群聊截图 / 入群邀请卡片 / 名片
  - 学员自己发的无关生活图

定位到候选格后，去 out/<昵称>/ 找该格对应的高清(_h.png)或缩略(_t.jpg)原图放大读准
金额数字与付款方式（转账 / 小鹅通 / 微信支付）。
```

## OUTPUT_CONTRACT

```json
{
  "wxid": "<该学员 wxid>",
  "name": "<昵称，日志用>",
  "found": true,
  "pay": {
    "amt": 7900,
    "method": "微信支付",
    "img": "payment_proof/out/<昵称>/<文件名>.png",
    "evidence": "#3 交易详情，收款方 All in AI，金额 ￥7900"
  }
}
```

- `found=false` 时 `pay` 省略：本批 montage 里没有可信的付款交易页（agent 不得臆测金额）。
- `pay` 直接对应 `outputs/intake_writer` worksheet 的 `pay` 字段（{amt, method, img}），由 intake_writer 以 fill_only_if_empty 写「实付/付款方式」+ 上传「提成截图凭证」。
