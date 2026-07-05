# FinQA 1k Failure Labels

Status: first-pass human labels for the 32 priority rows in the 1k failure diagnosis pack.

## Label Counts

| Label | Count |
| --- | ---: |
| source_number_selection_error | 14 |
| formula_error | 9 |
| rounding_precision_error | 4 |
| percent_or_scale_error | 3 |
| ambiguous_gold_or_context | 2 |

## Transition Counts In Labeled Priority Rows

| Transition | Count |
| --- | ---: |
| both_wrong | 30 |
| regressed_vs_500 | 2 |

## Main Lesson

The 1k answerability-focused run mostly failed because the model selected the wrong source numbers or applied the wrong formula. The next paid run should teach evidence selection and compact calculation, not simply tell the model to answer more often.

## Labeled Examples

| ID | Label | Gold | Program | 500-SFT | 1k-SFT | Note |
| --- | --- | ---: | --- | --- | --- | --- |
| `GS/2013/page_152.pdf-2` | formula_error | 383.0 | `subtract(150, -233)` | Final answer: 383 | Final answer: 333 | Regression from 500-SFT. Required subtracting a negative value: 150 - (-233) = 383; 1k answered 333, suggesting sign handling/arithmetic failure. |
| `TROW/2010/page_22.pdf-3` | source_number_selection_error | 1.3 | `subtract(38.4, 37.1)` | Final answer: 1.3% | Final answer: 2.3% | Regression from 500-SFT. Correct evidence states 37.1% vs 38.4%, so the decrease is 1.3 percentage points; 1k likely selected a nearby unrelated rate. |
| `AES/2002/page_46.pdf-2` | source_number_selection_error | 6.36 | `add(9.17, 3.55), divide(#0, const_2)` | Final answer: $52.25, $39.95 | Final answer: 25.2 | Question asks average of 2002 Q2 high/low: (9.17 + 3.55) / 2 = 6.36. Models confuse adjacent 2001 columns or emit unsupported number. |
| `AES/2017/page_175.pdf-4` | formula_error | 0.61628 | `divide(53, 86)` | Final answer: not enough information | Final answer: 65% | Correct computation is 53 / 86 = 0.61628, about 61.6%. 1k answered 65%, a rough unsupported estimate rather than exact table/text calculation. |
| `BLK/2014/page_119.pdf-3` | rounding_precision_error | 0.15152 | `divide(750, 4950)` | Final answer: not enough information | Final answer: 0.16 | 1k moved in the right direction: 750 / 4950 = 0.15152. Answer 0.16 is too coarse for strict numeric EM. |
| `CDNS/2018/page_31.pdf-1` | source_number_selection_error | 18770.0 | `subtract(129.05, 110.28), divide(100000, const_100), multiply(#1, #0)` | Final answer: not enough information | Final answer: 110280 | Correct computation uses index change 129.05 - 110.28, scaled by 100000 / 100. 1k returned 110280, apparently the starting index value scaled by investment size. |
| `CME/2012/page_70.pdf-1` | formula_error | 0.4 | `subtract(const_7, const_5), divide(#0, const_5)` | Final answer: not enough information | Final answer: 140% | Correct increase over available line is (7 - 5) / 5 = 0.4. 1k answered 140%, likely using 7 / 5 instead of incremental increase. |
| `ETR/2008/page_355.pdf-4` | formula_error | 0.0814 | `subtract(93000, 86000), divide(#0, 86000)` | Final answer: not enough information | Final answer: 7.6% | Correct computation is (93000 - 86000) / 86000 = 0.0814. 1k answered 7.6%, likely wrong denominator or rough percentage. |
| `ETR/2011/page_324.pdf-3` | formula_error | -16402.0 | `multiply(118415, const_m1), add(#0, 49887), add(#0, 52807), add(#1, 61236), divide(#2, const_4)` | Final answer: not enough information | Final answer: 100.5 | Needs signed averaging across 2011 payable/receivable values. 1k ignored sign and multi-step aggregation. |
| `EW/2017/page_82.pdf-2` | rounding_precision_error | 0.29144 | `divide(53.1, 182.2)` | Final answer: 53.1% | Final answer: 29.4% | Correct computation is 53.1 / 182.2 = 0.29144. 1k answered 29.4%, directionally close but outside strict tolerance. |
| `HUM/2017/page_133.pdf-1` | source_number_selection_error | 0.66667 | `divide(1.5, 2.25)` | Final answer: not enough information | Final answer: 15.6% | Correct computation is 1.5 / 2.25 = 0.66667. 1k answered 15.6%, indicating unrelated number selection from context. |
| `IPG/2009/page_85.pdf-3` | percent_or_scale_error | 10.82621 | `divide(3.8, 35.1), multiply(#0, const_100)` | Final answer: not enough information | Final answer: 0.06 | Correct computation is 3.8 / 35.1 * 100 = 10.82621. 1k answered 0.06, missing the percent scale and likely using wrong numerator/denominator. |
| `JPM/2007/page_157.pdf-2` | source_number_selection_error | 994.0 | `subtract(3133, 2139)` | Final answer: 2139 | Final answer: 1144 | Correct difference is 3133 - 2139 = 994. 1k answered 1144, suggesting wrong row or nearby table value selection. |
| `LMT/2012/page_47.pdf-1` | source_number_selection_error | 0.01881 | `subtract(1083, 1063), divide(#0, 1063)` | Final answer: not enough information | Final answer: 1.5% | Correct growth is (1083 - 1063) / 1063 = 0.01881. 1k answered 1.5%, likely from a nearby percent or wrong operating-profit delta. |
| `LMT/2016/page_48.pdf-2` | source_number_selection_error | 0.98491 | `add(1.7, 290), add(#0, 250), divide(#1, 550)` | Final answer: not enough information | Final answer: 0.36 | Correct ratio uses increasing factors 1.7B + 290M + 250M over 550M. 1k answered 0.36, suggesting it selected only part of the factors. |
| `PM/2017/page_38.pdf-3` | formula_error | 0.02581 | `subtract(914, 23), divide(23, #0)` | Final answer: not enough information | Final answer: 1.5% | Correct increase is 23 / (914 - 23) = 0.02581. 1k answered 1.5%, not tied to the stated interest-expense increase formula. |
| `PM/2017/page_99.pdf-4` | percent_or_scale_error | 2.0 | `subtract(1551, 1549)` | Final answer: not enough information | Final answer: 0.001 | Correct difference is 1551 - 1549 = 2 million shares. 1k answered 0.001, a unit/scale failure. |
| `RE/2015/page_33.pdf-1` | rounding_precision_error | 0.99474 | `divide(264.9, 266.3)` | Final answer: not enough information | Final answer: 1.02 | Correct computation is 264.9 / 266.3 = 0.99474. 1k answered 1.02, close in spirit but likely rounded from wrong denominator. |
| `RSG/2009/page_100.pdf-2` | rounding_precision_error | 0.39349 | `divide(93.1, 236.6)` | Final answer: not enough information | Final answer: 39.7% | Correct computation is 93.1 / 236.6 = 0.39349. 1k answered 39.7%, close but not exact enough for current EM tolerance. |
| `RSG/2016/page_144.pdf-2` | formula_error | 14.0 | `divide(37.8, 2.7)` | Final answer: not enough information | Final answer: 0.008 | Correct ratio is 37.8 / 2.7 = 14.0. 1k answered 0.008, likely wrong direction or unrelated denominator. |
| `STZ/2006/page_68.pdf-4` | source_number_selection_error | 0.34308 | `divide(634203, 1848575)` | Final answer: not enough information | Final answer: 38.5% | Correct computation is goodwill 634203 / acquisition total 1848575 = 0.34308. 1k answered 38.5%, likely selected a wrong asset/total value. |
| `AMT/2005/page_54.pdf-2` | source_number_selection_error | 1.0499 | `divide(558360, 531822)` | Final answer: 55.84% | Final answer: 0.34 | Correct computation is 558360 / 531822 = 1.0499. 500 used 55.84%, 1k used 0.34; both selected or transformed the wrong cash-flow quantities. |
| `BLL/2007/page_35.pdf-1` | percent_or_scale_error | 37.75428 | `multiply(705292, 53.53), divide(#0, const_1000000)` | Final answer: $2,353,366 | Final answer: 3.5 | Correct cash outflow in millions is 705292 * 53.53 / 1,000,000 = 37.75428. 1k answered 3.5, a scale/order-of-magnitude error. |
| `BLL/2007/page_35.pdf-2` | source_number_selection_error | 58864176.24 | `multiply(1144772, 51.42)` | Final answer: $2,336,800 | Final answer: $2,333,600 | Correct total spend is 1,144,772 * 51.42 = 58,864,176.24. Both models selected much smaller nearby repurchase amounts. |
| `C/2017/page_328.pdf-2` | formula_error | 1.15615 | `subtract(193.5, const_100), subtract(208.1, const_100), divide(#1, #0)` | Final answer: 1.04 | Final answer: 1.04 | Correct comparison is cumulative gains ratio: (208.1 - 100) / (193.5 - 100) = 1.15615. Models used raw index ratio instead. |
| `CB/2010/page_200.pdf-3` | formula_error | 1063076.5 | `add(256868, 1230881), add(638401, #0), add(#1, const_3), divide(#2, const_2)` | Final answer: 425250 shares | Final answer: 1902790 | Needs average of three anti-dilutive share conversion values. 1k emitted a sum-like value rather than average. |
| `ETR/2011/page_376.pdf-1` | ambiguous_gold_or_context | 560.0 | `add(577.8, 540.2), add(#0, const_2), divide(#1, const_2)` | Final answer: $564.0 | Final answer: 564.0 | Evidence gives 2011 net revenue 577.8 and 2010 540.2; ordinary average is 559.0, gold/program yields 560.0, while models answer 564.0. Review gold/program quality. |
| `FIS/2007/page_94.pdf-4` | source_number_selection_error | 0.14162 | `divide(35269, 249038)` | Final answer: 35.27% | Final answer: 12.2% | Correct lease-payment share is 35269 / 249038 = 0.14162. 1k answered 12.2%, likely selected wrong year/payment bucket. |
| `GIS/2019/page_37.pdf-2` | source_number_selection_error | 0.10664 | `divide(1396.3, 13093.0)` | Final answer: 1.3963% | Final answer: 2.4% | Correct long-term debt due 2020 share is 1396.3 / 13093.0 = 0.10664. 1k answered 2.4%, likely selected unrelated table percentage. |
| `LMT/2015/page_99.pdf-2` | source_number_selection_error | 1.4847 | `subtract(15261, 6142), divide(#0, 6142)` | Final answer: 10.5% | Final answer: 10.5% | Correct debt-net change is (15261 - 6142) / 6142 = 1.4847. Models answered 10.5%, likely from nearby debt-rate text. |
| `PNC/2011/page_78.pdf-3` | source_number_selection_error | 0.2 | `subtract(13.2, 13.0)` | Final answer: $1.2 billion | Final answer: $1.2 | Correct change magnitude is 13.2 - 13.0 = 0.2 billion. 1k answered 1.2, likely wrong subtraction or digit selection. |
| `TROW/2010/page_22.pdf-1` | ambiguous_gold_or_context | -0.48214 | `subtract(2.9, 5.6), divide(#0, 5.6)` | Final answer: 66.7% | Final answer: 66.7% | Question asks capital gain distributions 2008 to 2009, evidence says 5.6 to 2.0, but program/gold uses 2.9 and gives -0.48214. Models also miss sign. Review gold/evidence alignment. |

## Recommended Next Dataset Change

- Add compact calculation supervision for answerable rows.
- Include the exact source numbers used before the final answer.
- Preserve strict `Final answer:` extraction for eval.
- Do not scale the current 2k file until this smaller ablation beats the 500-SFT smoke result.
