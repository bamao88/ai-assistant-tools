# 平台巡看与选题证据

这是 content-topic-planning 的可选采集分支；仅在用户要浏览推荐/关注/搜索流找题，或现有资料不足且平台信号能影响取舍时读取。它不独立确定账号定位，不替代选题判断。

先按当前项目入口读取定位、受众、已做内容和素材库，记录真实路径。项目已提供定位时直接使用；不要因为找不到某个固定文件名就重新询问。未指定平台则按项目已接入且有价值的平台选择。

按本次范围低频只读浏览。当前可执行能力为小红书测试号推荐流、关键词搜索与候选详情/作者主页二次核验；公众号、微博仅为可能扩展，不宣称已经支持。认证、验证页或采集异常保留现场，按现有登录流程恢复，不盲目重试。

下方数量与关键词是命令示例，按任务调整；候选分数只用于检索排序，不作为选题质量、固定赞粉比或爆款率门槛。清楚报告平台、时间窗口、列表与正文实际读取范围、缺失和抽样局限。

候选按内容方向比较。图文、文章、视频均可进入推荐；仅当目标为视频时才增加拍法、开头、镜头或录屏素材与制作成本判断。按需要二次核验最影响决定的样本，不要求固定候选数、固定截图数或每条读完全部历史作品。

把证据带回 content-topic-planning 的研究、比较和交付流程。产出主推/备选/暂缓理由、依据和待补证项；采集 report.md 是来源记录，不能代替选题结论。没有可信推荐时继续补关键证据或明确阻塞，不凑题。

账号与动作边界：以下 CLI 巡看默认 --account 测试号；只读推荐、搜索、详情、作者页，不包含点赞、收藏、评论、关注、私信或发布授权。已有输出先复用，按项目保存来源，不另建平行素材库。

## 已有命令与输出


MVP 支持三种小红书执行入口：

### 广泛采集：首页推荐流

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/platform-scout/scripts/xhs_recommend_scout.py \
  xhs-recommend \
  --account 测试号 \
  --limit 50 \
  --min-candidates 30 \
  --scroll-rounds 4 \
  --dwell-seconds 2 \
  --inspect-top 0 \
  --brief-file /absolute/path/to/current-project/doc/account-positioning.md
```

### 广泛采集：关键词搜索热门内容

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/platform-scout/scripts/xhs_recommend_scout.py \
  xhs-search-keywords \
  --account 测试号 \
  --keyword AI产品经理 \
  --keyword Codex \
  --keyword Agent工作流 \
  --limit 60 \
  --min-candidates 30 \
  --per-keyword-limit 20 \
  --inspect-top 0 \
  --sort-by 最多点赞 \
  --publish-time 一周内 \
  --brief-file /absolute/path/to/current-project/doc/account-positioning.md
```

### 拍法核验：从候选池挑指定选题深挖

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/platform-scout/scripts/xhs_recommend_scout.py \
  xhs-inspect-candidates \
  --account 测试号 \
  --candidates-file /absolute/path/to/candidates.json \
  --rank-range 1-12 \
  --brief-file /absolute/path/to/current-project/doc/account-positioning.md
```

关键词多时，优先写入文件，一行一个：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/platform-scout/scripts/xhs_recommend_scout.py \
  xhs-search-keywords \
  --account 测试号 \
  --keywords-file /absolute/path/keywords.txt \
  --limit 80 \
  --min-candidates 30 \
  --per-keyword-limit 20 \
  --inspect-top 0 \
  --brief-file /absolute/path/to/current-project/doc/account-positioning.md
```

输出目录默认在：

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/var/data/platform-scout/xiaohongshu/<timestamp>/
```

每次运行会生成：

- `raw.json`：本次推荐流或搜索结果卡片原始摘要，并记录本轮使用的项目定位 brief。
- `candidates.json`：打分后的候选选题。
- `report.md`：平台证据报告，包含项目定位文件路径、安全摘要、时间范围二次校验和“图文 / 视频”内容形态。它不是最终选题结论。
- `screen_*.png`：推荐流截图留痕。
- `candidate_*_detail.png`：逐条打开候选笔记详情后的截图。
- `candidate_*_profile.png`：逐条打开作者主页后的截图。
- 按 [选题交付模板](templates.md) 形成推荐、比较或单题简报；视频任务按需补拍法与素材判断。`report.md` 只提供平台证据，不能替代最终选题判断。

