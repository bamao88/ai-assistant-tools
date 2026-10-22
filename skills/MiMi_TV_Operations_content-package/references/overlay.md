# 视频叠字

被动节目成片**只在开篇**有一处叠字，写给**主人**：提醒他把猫叫过来看。它不是字幕，不对猫说话，也不引导游戏或评论（那些放在正文结尾段和置顶评论里）。工具：[add_overlay.py](../scripts/add_overlay.py)。

## 写什么

每条 item 在 `video.overlay_phrases` 写 1 句，不超过 12 个字。换位思考：主人躺在家里刷手机，一句什么话能让他起身把猫叫过来？最有用的是**给他一个叫猫的理由**——想知道自家猫的反应。不写「游戏」「评论」「链接」（`--check` 会拦）；不写效果承诺，不说猫一定会来或一定会喜欢；不鼓励猫扑向屏幕，设备要放稳。

当前使用 E；其余版本留作备选，换版本只改 `overlay_phrases` 后重新运行脚本。

| 版本 | 文案 | 打动主人的点 |
| --- | --- | --- |
| A | 猫猫在吗？快叫它来看！ | 一句话让主人想起「我家猫在哪」 |
| B | 别刷啦，叫猫猫来看 | 说中主人正在刷手机，带点撒娇 |
| C | 手机放稳，叫猫猫来看 | 先让主人立好手机，更安全 |
| D | 小丑鱼来啦！猫猫呢？ | 先勾出画面，再问猫在哪（对象随当期改） |
| **E** | **快叫猫猫来，看它啥反应** | 给主人一个理由：好奇自家猫的反应 |
| F | 给猫猫一个小惊喜 | 温柔，从主人宠猫的心态出发 |

## 样式与位置

画面**顶部居中**，暖黄粗体 76px、深棕描边、轻微上下跳动，淡入淡出 0.4 秒；每条成片只在开篇出现一次（约 1.0—4.4 秒，主人还没离开时）；后面不再出现，节目主体不被打扰。左右上角是作者标识，素材底部有时还有很小的 Copyright 行（例如 item-028）：叠字不得遮挡或移除它们。换字号或位置后，抽取带标识的素材核对一次。叠字有时会盖住画面里的小动物，目前接受，必要时在 `overlay_phrases` 之外调整出现位置。

## 流程

```bash
python3 .codex/skills/MiMi_TV_Operations_content-package/scripts/add_overlay.py content/items/item-0xx/item.json
python3 .codex/skills/MiMi_TV_Operations_content-package/scripts/add_overlay.py --check content/items/item-0xx/item.json
```

- 未叠字的原片保存为 `work/video-no-overlay.mp4`，重复运行始终从它出发，不会叠两层；音频流原样复制。
- 脚本写回 `video.sha256`、`video.duration_seconds`、`video.clean_file`、`video.clean_sha256`、`video.overlay`，并把 `video.edit` 改为「仅在开篇增加一处给猫看的顶部提示叠字」。
- 叠字后抽取开篇出现时和之后一帧（确认已消失）目视检查；仍需原速有声审看，脚本和抽帧不替代。
- 只改本地文件，不上传、不发布。叠字版即平台使用的成片；批次包 `package.zip` 内的旧文件是历史版本，需要时重新 bundle。
