# Time Series Forecasting Papers

导出论文数：2

## 1. Uncertainty-Driven Anomaly Detection for Psychotic Relapse Using Smartwatches: Forecasting and Multi-Task Learning Fusion

- ID: `2605.13816v1`
- Source: `arxiv`
- Published: `2026-05-13`
- Authors: Nikolaos Tsalkitzis, Panagiotis P. Filntisis, Petros Maragos, Niki Efthymiou
- Categories: cs.LG
- Tags: Transformer, Probabilistic, Benchmark, Anomaly, Probabilistic forecasting, Anomaly detection, source:arxiv
- Priority: `medium`
- Citations: `0`
- PDF: https://arxiv.org/pdf/2605.13816v1

**摘要速览**：这篇论文关注“Uncertainty-Driven Anomaly Detection for Psychotic Relapse Using Smartwatches: Forecasting and Multi-Task Learning Fusion”。从摘要看，它的核心问题是基于时间序列信号进行异常检测或风险预警，主要方法线索包括Transformer、Probabilistic、Benchmark。阅读时可以重点看作者如何定义预测目标、如何把模型输出转化为可评估的结果，以及实验是否证明这种设计比基线更可靠。

**相关性判断**：和时间序列建模或预测有明显关联，可作为补充阅读；关键词方向：Transformer, Probabilistic, Benchmark。

**要点**：
- 研究问题：论文试图解决基于时间序列信号进行异常检测或风险预警，重点不只是预测数值本身，也包括预测结果如何服务后续判断或决策。
- 方法主线：摘要中出现的关键技术标签是Transformer, Probabilistic, Benchmark, Anomaly，说明论文大概率围绕模型结构、表示学习或不确定性估计展开。
- 方法细节：论文提出或组合了一个模型流程，用预测偏差、异常信号或多任务表示来形成最终判断。原文线索是：Consequently, we propose a late-fusion strategy that synergistically combines the anomaly signals from both architectures into a unified decision score.
- 实验设计：论文使用公开数据集或基准任务验证方法效果，重点应核对数据规模、评价指标、对比基线和消融实验。原文线索是：We benchmark our methodology on the 2nd e-Prevention Grand Challenge dataset, where our fused model achieves a 8% relative improvement over the competition-winning baseline.
- 结果解读：摘要声称方法相对基线有提升，阅读正文时需要确认提升幅度是否稳定、是否来自关键模块，以及是否有统计或消融支撑。原文线索是：We benchmark our methodology on the 2nd e-Prevention Grand Challenge dataset, where our fused model achieves a 8% relative improvement over the competition-winning baseline.
- 阅读重点：建议先看问题定义和数据构造，再看模型结构，最后核对实验指标、消融实验和失败案例。

**深度总结**：这篇论文可以先理解为一项围绕基于时间序列信号进行异常检测或风险预警的建模研究。它不是只给出一个预测模型，而是试图把时间序列预测、特征表示和不确定性估计结合起来，让模型输出能够被用于实际判断。从摘要可见，论文的技术重点集中在Transformer、Probabilistic、Benchmark、Anomaly。如果你做时间序列预测，可以把它当作一个案例：看作者如何从连续观测数据中构造监督信号，如何处理多变量或跨模态信息，以及如何证明预测结果确实带来任务收益。

**局限性**：仅凭摘要还无法判断数据规模、跨数据集泛化、模型复杂度和真实场景鲁棒性。如果实验只覆盖单一数据集或单一应用场景，就需要谨慎看待结论的普适性。

## 2. MILM: Large Language Models for Multimodal Irregular Time Series with Informative Sampling

- ID: `2605.13711v1`
- Source: `arxiv`
- Published: `2026-05-13`
- Authors: Hsing-Huan Chung, Shijun Li, Yoav Wald, Xing Han, Suchi Saria, Joydeep Ghosh
- Categories: cs.LG
- Tags: Foundation model, Benchmark, source:arxiv
- Priority: `medium`
- Citations: `0`
- PDF: https://arxiv.org/pdf/2605.13711v1

**摘要速览**：这篇论文关注“MILM: Large Language Models for Multimodal Irregular Time Series with Informative Sampling”。从摘要看，它的核心问题是时间序列预测或时序建模，主要方法线索包括Foundation model、Benchmark。阅读时可以重点看作者如何定义预测目标、如何把模型输出转化为可评估的结果，以及实验是否证明这种设计比基线更可靠。

**相关性判断**：和时间序列建模或预测有明显关联，可作为补充阅读；关键词方向：Foundation model, Benchmark。

**要点**：
- 研究问题：论文试图解决时间序列预测或时序建模，重点不只是预测数值本身，也包括预测结果如何服务后续判断或决策。
- 方法主线：摘要中出现的关键技术标签是Foundation model, Benchmark，说明论文大概率围绕模型结构、表示学习或不确定性估计展开。
- 方法细节：论文提出或组合了一个模型流程，用预测偏差、异常信号或多任务表示来形成最终判断。原文线索是：We introduce MILM (Multimodal Irregular time series Language Model), which represents MITS as time-ordered triplets in Extensible Markup Language (XML) format and fine-tunes an LLM through a two-stage strategy for MITS classification.
- 实验设计：论文使用公开数据集或基准任务验证方法效果，重点应核对数据规模、评价指标、对比基线和消融实验。原文线索是：In the value pending evaluation we introduce, where some values are unavailable at prediction time, MILM-2S outperforms MILM-Direct by a larger margin compared to standard evaluation.
- 结果解读：摘要声称方法相对基线有提升，阅读正文时需要确认提升幅度是否稳定、是否来自关键模块，以及是否有统计或消融支撑。原文线索是：In the value pending evaluation we introduce, where some values are unavailable at prediction time, MILM-2S outperforms MILM-Direct by a larger margin compared to standard evaluation.
- 阅读重点：建议先看问题定义和数据构造，再看模型结构，最后核对实验指标、消融实验和失败案例。

**深度总结**：这篇论文可以先理解为一项围绕时间序列预测或时序建模的建模研究。它不是只给出一个预测模型，而是试图把时间序列预测、特征表示和预测误差和泛化能力结合起来，让模型输出能够被用于实际判断。从摘要可见，论文的技术重点集中在Foundation model、Benchmark。如果你做时间序列预测，可以把它当作一个案例：看作者如何从连续观测数据中构造监督信号，如何处理多变量或跨模态信息，以及如何证明预测结果确实带来任务收益。

**局限性**：仅凭摘要还无法判断数据规模、跨数据集泛化、模型复杂度和真实场景鲁棒性。如果实验只覆盖单一数据集或单一应用场景，就需要谨慎看待结论的普适性。
