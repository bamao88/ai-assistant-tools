# profiles/zh_main —— 张和（assistant_zh）渲染定制层

定制层①（迁移计划 §3.2）：account=zh_main 的渲染侧定制，集中在工具内、按 account 组织，**不散回项目**。引擎 `--profile zh_main` 读取。

| 项 | 位置 | 状态 |
|---|---|---|
| ASR 术语纠错映射 | `fixes.json` | ✅ 已外置（`render.load_fixes(profile)` 读） |
| 锁定几何 GEOM/SUB/ACCEL | `render.py` 内置默认 | §3.1：张和=内置默认；其它账号可在此放 `render_geom.json` 覆盖（阶段5 留钩，值外置待 G4 逐帧验证后做） |
| 页面版式 PAGE_CSS / ARROW / HTML 模板 | `render.py` 内置默认 + `../../templates/` | §3.1：张和=内置默认；外置同上待帧验证 |

> 视觉常量（GEOM/PAGE_CSS）的**值外置**会改像素核心，须 G4 逐帧回归兜底（当前
> BLOCKED_NEEDS_LOCAL_VALIDATION）。在帧验证就绪前保持「张和=内置默认」，多租户通过
> 可选 profile 覆盖实现——zh_main 不放覆盖文件即用默认，行为零变化。

相关：选题/文案 persona 在 `engines/video-slicer/personas/zh_main.md`；分页/纠错 prompt 在
`engines/video-slicer/profiles/zh_main/{pages,srt_fix}_system_prompt.txt`（阶段2 已外置）。
