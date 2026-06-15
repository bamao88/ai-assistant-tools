# 客户表数据体检/订正闭环（health-check 配方）

「整理客户资产」的真身。死脚本考古发现 `find_missing_wxid` / `update_existing_wxids` /
`fix_zh2_*` / `fix_friends_column_*` / `audit+merge_dup` 骨架完全相同——同一个反复出现的任务被
临时重写多遍。提炼成一等配方（resolve 能力 + 写入策略层），那些一次性脚本已删。

## 闭环

```
扫飞书表找出某类毛病的行（缺 wxid / 填错列 / 重复 / 昵称误填）
  → 出人读候选清单 → 你 dry-run 确认 → --apply 幂等批量改 → 归档 run
```

## 用法

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines
python3 -m customer-management health-check --list                       # 列出所有缺陷类
python3 -m customer-management health-check missing_wxid                  # dry-run（默认，只读镜像）
python3 -m customer-management health-check missing_wxid --source live    # 拉 live 飞书找候选
python3 -m customer-management health-check missing_wxid --apply          # 授权门：真写（须用户明说「同步飞书」）
python3 -m customer-management health-check weixin_name_to_nick --role zh2 # role-scoped 缺陷类
```

## 缺陷类（注册表）

| 缺陷类 | 含义 | 替代的旧死脚本 |
|---|---|---|
| `missing_wxid` | 飞书行缺 wxid（`--loose` 把 S5 成交时间也算学员信号）| find_missing_wxid / update_existing_wxids |
| `friends_column_misplaced` | 好友信息填错列 | fix_friends_column_misplacement（曾 deprecate）|
| `weixin_name_to_nick` | 「微信名称」误填 alias/wxid，应改昵称（role-scoped）| fix_zh2_weixin_name_to_nick |
| `duplicate_creates` | 建行后与空 wxid 老行重复（role-scoped）| audit_duplicate_creates + merge_duplicate_creates |

## 红线

- **默认 dry-run + 只读镜像**（`--source mirror`，不碰网络）。要 live 拉飞书须 `--source live`。
- `--apply` 是授权门，且须用户明说「同步飞书」。「修复/对不上/异常」≠ 授权 apply。
- 默认先读 plan（候选清单）；幂等回写，已 sync 的不重复写。
- run 归档落 `analytics/friends_index/{sync_runs,duplicate_audits,merges}/` 等对应目录。
