"""video-select · 第②环·选片（Eval Harness + 成片脚本产出）。

闭环：评测集 → Runner(topics+generate) → Gates(gates) → Scorer(score) → 人工评审 → 冻结 golden 参照。
设计真源：doc/plan/视频剪辑skill-第二环选片-plan.md。
"""
