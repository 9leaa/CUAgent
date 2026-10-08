# 费用测试材料 v1

仅虚构测试数据，无真实支付、税务或个人信息。`cases.json`的预期分类/金额为助手独立编写，不由被测验证器生成，不是用户审核结果。`output/pdf/expense-v1/`保存8份实际PDF与原字节SHA/长度清单。

| 组 | 交易总额 | 原始已知票据合计（未去重） | 预期 |
|---|---:|---:|---|
| normal | 57.90 | 57.90 | 两笔唯一匹配，业务含义仍待审 |
| anomalies | 180.00 | 195.00 | 5.00差额、一组重复原票、多候选、缺票 |
| ambiguity | 70.00 | 40.00，另1张金额未知 | 两笔共享两张同额票，遮挡金额保持未知 |

金额均为CNY。anomalies/r2与r3为完全相同的PDF字节；ambiguity/r1与r2金额相同但票号不同，不能按同额直接去重。遮挡样本是原PDF的`[OBSCURED]`，不是测试程序隐藏一个仍可读取的真实金额。

生成器只渲染原票，不生成报告。需ReportLab；`review_pdf.py`另需pypdf/Pillow及Poppler，逐份解析并核对源文字后渲染所有页面。生成/渲染输出目录必须不存在，避免覆盖历史材料：

```sh
python backend/fixtures/expense-v1/generate.py --output /new/fixture-directory
python backend/fixtures/expense-v1/review_pdf.py --assets output/pdf/expense-v1 --output /new/review-directory
python -m pytest backend/tests/test_expense_contract.py backend/tests/test_expense_result.py backend/tests/test_expense_fixtures.py -q
```

本地作者工具可用独立文档运行时，不向生产后端安装PDF生成依赖。普通契约测试只用已提交的PDF字节及SHA，无模型、网络或VM访问。渲染后的接触图仍需实际查看，不把文本提取当作排版核验。

边界：单元测试从预期数据构造可信提取记录，仅用于核验验证器。实际执行不能把该记录当作模型识别结果或交给模型照抄答案；应只传原票与流水，独立验收侧保存预期。生产材料安装/提取证据、GUI保存重开/下载与语义审核均待实现。
