# video-compose

★ 组合层（新·薄）：整套视频剪辑的**唯一对外入口**，只指挥不产原子（迁移计划 §3.4 / D7）。

依赖单向 `video-compose → 各积木厂引擎`（video-slicer / video-framework-render / video-clip）；
各引擎互不依赖、只在自己的 `capabilities.json` 声明原子。

```
catalog.json      总能力表（真源·跨引擎聚合，build_catalog.py 从各引擎 capabilities.json 重建）
recipes.json      命名预设（zh_business / raw_quickcut / simple_concat / chaptered_growth）
selector.py         AI 读视频 → 选 recipe / 自由组合
run.py            按 recipe 解析能力链 → 跨引擎调原子
build_catalog.py  重建 catalog（新增原子 → 在所属引擎声明 → 重跑此脚本即并入）
```

## 用法

```bash
python build_catalog.py                       # 重建总能力表
python selector.py --list                       # 列能力 + 配方
python selector.py --describe "口播框架页切片"   # → zh_business
python run.py --plan zh_business              # 审能力链（每步原子+引擎+entry）
python run.py --run zh_business --selection sel.json --profile zh_main
```

## 模型四层（§3.4）

1. 能力 catalog（原子，AI 可单选/组合）：剪辑策略 `cut_sentence`(句级·线上) │ `cut_word`(词级·方案B) **共存**；改造 `framework_reframe` │ `raw`；叠加 `progress_bar`/`endcard`/`subtitle_*`/`speed_adapt`/`name_mask`/`concat`/`cover_frame` …
2. 配方 recipes（命名预设）：一条 = 能力有序组合；`zh_business` = 当前线上业务流。
3. 选择 select：AI 读视频选 recipe 或自由组合。
4. 引擎布局（§3.1）：原子物理分布在三个积木厂。

## 现状与待办

- `zh_business` 当前为 **delegate**（委派已装配的 `run_pipeline.py`）。渲染核心已拆原子入
  `video-framework-render`（`framework_reframe`）；升级为 atom 级 chain 待 **G4 逐帧回归**
  （BLOCKED_NEEDS_LOCAL_VALIDATION：需渲染 venv + puppeteer + 字体实跑比对）就绪。
- `video-clip` 旧 `catalog.json`/`recipes.json` 内容已上移到此（真源唯一）。
