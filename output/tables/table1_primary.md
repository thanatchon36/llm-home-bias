| Specification                                         | Coefficient           |   Estimate (pp) | SE             | p      |     N |   Clusters |   Models |
|:------------------------------------------------------|:----------------------|----------------:|:---------------|:-------|------:|-----------:|---------:|
| Pooled (primary)                                      | β Home (model origin) |           -0.42 | 0.09           | <0.001 | 23008 |        240 |       12 |
| Pooled (primary)                                      | γ InvestorHome        |            1.88 | 0.21           | <0.001 | 23008 |        240 |       12 |
| Pooled (primary)                                      | λ LanguageHome        |            0.46 | 0.13           | <0.001 | 23008 |        240 |       12 |
| Pooled, wild cluster bootstrap by template            | β Home                |           -0.42 | [-0.75, -0.09] | 95% CI | 23008 |          8 |       12 |
| By origin group                                       | β Home × China        |            0.6  | 0.15           | <0.001 | 23008 |        240 |       12 |
| By origin group                                       | β Home × Europe       |           -2.07 | 0.13           | <0.001 | 23008 |        240 |       12 |
| By origin group                                       | β Home × Korea        |           -0.4  | 0.16           | 0.014  | 23008 |        240 |       12 |
| By origin group                                       | β Home × Thailand     |            0.07 | 0.12           | 0.573  | 23008 |        240 |       12 |
| By origin group                                       | β Home × UnitedStates |           -0.17 | 0.26           | 0.513  | 23008 |        240 |       12 |
| H2: English × unspecified investor                    | β Home                |           -1.02 | 0.29           | <0.001 |  1152 |         12 |       12 |
| H3: typhoon2-8b vs llama3.1-8b (Thailand weight)      | δ fine-tune           |           -1.04 | 0.26           | <0.001 |   480 |        240 |        2 |
| H3: openthaigpt1.5-7b vs qwen2.5-7b (Thailand weight) | δ fine-tune           |            1.26 | 0.27           | <0.001 |   480 |        240 |        2 |
| Cash currency (LPM, pp of probability)                | β Home                |           -2.18 | 0.48           | <0.001 | 23008 |        240 |       12 |