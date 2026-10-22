# Canvas & Layout

Core canvas specifications and layout grids for Xiaohongshu infographics.

## Aspect Ratios

画幅优先按本轮要求与参考确定，同组一致；未指定的新系列先用约4:5试排，便于与本包历史样例比较，不代表最佳平台比例。

| Name | Ratio | 用途 |
|------|-------|------|
| portrait-4-5 | 4:5 | 延续本包历史系列时的起点 |
| portrait-3-4 | 3:4 | 可选竖版画幅 |
| square | 1:1 | 单张或方形构图 |
| portrait-2-3 | 2:3 | 需要更长纵向展开时试排 |

比例是构图要求，不是工具输出尺寸保证；实际生成后核对。不用“流量最高”等未经验证的判断选尺寸。

## Safe Zones

文字、气泡与关键对象离边缘留出阅读余量。若已提供目标平台的预览，按实际裁切和界面遮挡调整；没有预览时，不声称某个固定角落或底部百分比就是平台安全区。水印仅在本轮要求时预留，不挤占正文。

## Grid Layouts

### Density-Based Layouts

| Layout | 内容安排 | 可用情境 |
|--------|----------|----------|
| sparse | 单一焦点，周围留出呼吸空间 | 标题、态度、停顿或主视觉 |
| balanced | 文字、图示或情境共同解释，层次清楚 | 多数正文与经历展开 |
| dense | 多项相关内容同屏，分组清楚且文字可读 | 清单、对照、关系总览 |

密度描述内容的呈现，不规定要点数量与留白百分比。不因为选择dense就补满要点，也不因为选择sparse就删除必要对照或人物反应。

### Structure-Based Layouts

| Layout | Structure | 选择依据 |
|--------|-----------|----------|
| list | 并列条目 | 项目数来自材料；有先后才标步骤 |
| comparison | 左右或上下对照 | 同一维度、可比尺度，必要时多方同屏 |
| flow | 有方向的节点关系 | 确有时间、过程或因果依据 |
| mindmap | 中心与分支 | 真实层级或分类，不凑分支数 |
| quadrant | 四区/双轴 | 材料确实支持四类或两条判断轴 |

## Layout by Position

封面、正文、尾页都按本页的理解或感受任务选择布局。不要自动套“封面稀疏、正文列表、尾页CTA”。同一解释单元可跨页，不同页可以用不同布局；角色、标签与颜色的含义保持一致。

## Grid Cells

For multi-element compositions:

| Name | Cells | Use Case |
|------|-------|----------|
| single | 1 | Hero image, maximum impact |
| dual | 2 | Before/after, comparison |
| triptych | 3 | Steps, process flow |
| quad | 4 | Product showcase |
| six-grid | 6 | Checklist, collection |
| nine-grid | 9 | Multi-image gallery |

## Visual Balance

### Sparse Layout
- Single focal point centered
- Breathing room on all sides
- Symmetrical composition

### Balanced Layout
- Top-weighted title
- Evenly distributed content below
- Clear visual hierarchy

### Dense Layout
- Organized grid structure
- Clear section boundaries
- Compact but readable spacing

### List Layout
- Left-aligned items
- Clear number/bullet hierarchy
- Consistent item format

### Comparison Layout
- Comparable scale and matching dimensions
- Left/right or top/bottom arrangement as needed
- Separate groups clearly without requiring a boxed divider

### Flow Layout
- Directional flow (top→bottom or left→right)
- Use arrows only for supported direction, sequence or causality
- Do not turn parallel options into mandatory steps

### Mindmap Layout
- Central topic node
- Radial branches outward
- Hierarchical sub-branches
- Organic curved connections

### Quadrant Layout
- 4-section grid (2×2)
- Clear axis labels
- Each quadrant with distinct content
- Optional circular variant for cycles
