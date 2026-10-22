# 通用台账数据合同

## 文件与身份

配置中的路径相对 `--root`；不推断当前目录就是项目。`platform_accounts` 是以稳定账号ID为键的字典，每项含 `name`、`platform`、`native_id`。观察窗口和项目库存备注只从配置读取。

可选paths.review_report指向当前复盘报告；`--init`从独立报告模板创建缺失文件并填入总表相对路径，不覆盖已有报告。正常刷新不自动生成内容结论；Agent按 [持续复盘方法](retrospective.md) 维护解释、稳定经验ID和历史版本。

可选paths.iteration_brief指向后续内容优化简报，`--init`只创建缺失文件。项目专属Skill组织复盘，读取共享references/content-review.md及retrospective.md；简报保存稳定action ID、review依据、制作输入、实际采用的item／版本、pub、观察窗口及结果，不复制指标台账。item的采用元数据位置可由项目约定，元数据标签不能代替实际改动和验收。

- 作品表：`id,topic_id,format,artifact_path,status,updated_at`；可加title，缺title时从artifact_path相邻item.json的copy.post_title读，仅用作制作包标题。
- 发布表：`id,item_id,platform_account_id,status,published_at,url,evidence_path`；可补 `title,content_type,native_id,planned_at,scheduled_at,submitted_at,last_verified_at,platform_review_status,verification_level,notes,scope,visibility,timestamp_precision,identity_basis`。
- 指标表：`id,subject_type,subject_id,metric,value,unit,captured_at,source,window`，可补 `window_kind,observation_target_hours,capture_precision,period_start,period_end,data_as_of,source_kind,quality,quality_reason,quality_evidence`。自有单条subject_type=publication；账号汇总用platform_account；对标sample保持独立。
- 后台核对：`id,platform_account_id,captured_at,observed_total,observed_published,observed_scheduled,observed_private,evidence_path,identity_evidence,notes`。每次核对追加，声明统计筛选口径；总量比较只含真实已提交稿，不含planned/cancelled。
- 维护待办：`id,platform_account_id,publication_id,kind,state,reason,next_action,next_check_at,evidence_path,updated_at`。state用open/deferred/needs-auth/resolved/unavailable；关闭必须有证据或具体平台限制，失败不能假关闭。

稳定ID不随标题、路径、状态变化而更换。新发现旧平台帖可以暂空item_id，scope=legacy-account，并记录“无本地制作包”；不得为补关联捏造一个作品。存在制作包的正式项目稿使用project范围。相同原生ID不能对应多条发布；无原生ID时须保存复合匹配依据。

## 时间、状态与可见性

状态planned、draft-uploaded、submitted、scheduled、published、failed、cancelled、removed与公开范围分开。visibility=public/private/friends/unknown；私密旧帖保留首次发布日，不计入项目公开内容效果。删除／下架有明确新证据时记removed，保留历史快照。

planned_at表示计划，scheduled_at表示平台确认定时，submitted_at表示接受提交，published_at表示平台显示的首次发表时间。页面仅精确到分钟时timestamp_precision=minute；用分钟证据不能截掉既有精确秒值。时间全部带配置时区。平台统计延迟与采集时间不是一回事，captured_at记录本次实际读取／下载时点；使用mtime代理必须披露。

## 指标

常用：impression_count、view_count、like_count、comment_count、favorite_count、share_count、follower_gain、cover_ctr；保留平台提供的completion_rate、completion_5s_rate、skip_2s_rate、average_play_ratio、avg_watch_seconds、profile_visit_count、coin_count、danmaku_count。

比例unit=ratio、存0—1；原生封面点击率直接保存，不用观看÷曝光替换。观看时长只有UI或正式说明标明秒后用avg_watch_seconds/unit=秒；否则avg_watch_duration_raw原值及单位待核。缺值或“-”不创建指标行；只录真实0。不同平台和统计窗口不拼总分。

window_kind=cumulative / daily / rolling / unknown；window保留平台原口径、实际稿龄和备注。observation_target_hours只在真实采集落入配置目标窗口（含容差）且是累计值时填写，不能把后来的累计值补成旧D+N。生成器只在配置headline_window指定的同类窗口里选最新（默认cumulative；可为rolling），require_official_exports默认开启；每项指标单独追踪最后可得值，旧值标采集时间，不能因为新快照缺列而删掉旧列，也不能把不同时点伪装成同次采集。

## 快照导入

JSON结构：

```json
{
  "schema_version": 1,
  "snapshot_id": "有日期和运行标识的唯一ID",
  "sources": [{"path": "日期化原始证据路径", "sha256": "原件的SHA-256"}],
  "publications": [{"id": "稳定pub ID", "last_verified_at": "带时区时间", "status": "published", "evidence_path": "来源路径"}],
  "metrics": [{"subject_type": "publication", "subject_id": "对应pub ID", "metric": "view_count", "value": "真实数字", "unit": "次", "captured_at": "带时区时间", "source": "来源路径", "window": "累计；真实稿龄及条件", "window_kind": "cumulative"}],
  "checks": [],
  "maintenance": []
}
```

上述代码仅示意结构，不能当真实输入。需要完整来源、可解析关联、实际时间及数值才可导入；每个非空evidence_path/source必须包含在sources哈希清单。导入前验证全部内容；相同快照重复导入应不改数据、不增行，同键包含发布ID、指标、采集时间、原件、窗口类型与起止日，同键不同值报冲突。旧观察不能覆盖新状态；新证据更正状态需保留变更回执。历史原始证据不覆盖。

日常命令：不带选项刷新；`--queue`输出待办及应采集窗口JSON；`--import-snapshot`入库后刷新；`--check`核对事实与生成同步；`--init`从模板创建缺少的总表／空台账，绝不覆盖现有文件。全部命令只操作本地文件，不连接平台、不投稿。

原生导出可能包含合计行及逐日行。合计行的“累计”仅代表表内选择范围时，window_kind=rolling并保留period_start/end，不能标生命周期累计。逐日行用window_kind=daily、period_start=end=该日；原表全部保留，可归档每日值，不与合计行重复相加。source_kind=official-export；data_as_of记录平台更新截止日，与captured_at分开。

## 官方导出处理清单

`normalize_exports.py` 用标准库只读解析小红书／抖音XLSX及B站CSV；不修改原表、不联网。输入manifest包含：snapshot_id；inventories（platform_account_id、captured_at、source_path、identity_evidence、observed_total、check_id、notes、cards）；exports（platform_account_id、path、captured_at，B站另有native_id）；可选maintenance、extra_sources、metric_availability。

每张card必须有title、status、visibility及真实published_at或scheduled_at；原生ID／链接可选，时间精度明确。来源须为本轮保存的真实页面清单；cards数量与observed_total核平。缺原生ID不能拿账号ID顶替；旧记录已确认重复误填账号ID时清空稿件ID并保留变更回执。

XLSX的观看时长单位未载明时保留原值；取得官方单位说明后，在export配置watch_duration_unit=seconds及unit_evidence_path，才能用avg_watch_seconds。没有配置legacy_before或card.scope时，新出现无作品关联的稿件不会偷偷归档为历史；它应进入待关联。

metric_availability每项包含账号、title或native_id、metrics数组、quality、reason、evidence_path。仅据明确缺失／未更新证据标pending-platform-update或conflicting；原表数值仍保留，生成成绩表跳过不可用值。不能仅凭0、题材或观看时长长短判为无效。

证据确认的元数据可用metric_metadata_corrections修正：按subject_id、source、captured_at、match匹配，set只允许data_as_of、capture_precision、window或quality相关字段；必须有reason和哈希证据。数值、身份及窗口起止不可借此覆盖。修正的旧值和新值写入导入回执。

同一次采集已经产生并导入快照时，后续直接重放该冻结快照，不能改写它；新的采集或后续证据使用新运行ID。脚本校验通过只证明本地处理，不能冒充真实平台导出或调度运行成功。
