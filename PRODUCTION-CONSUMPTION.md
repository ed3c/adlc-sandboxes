# 沙盒在 Claude Code 的生產消費關係（總覽）

> **這份檔回答一個問題**：這些沙盒在 Claude Code 裡到底是**怎麼被生產、怎麼被消費**的？
> 通用框架在此；每個沙盒的**真實 live 運作 transcript**在各自的 `RUN.md`。
>
> | 沙盒 | 真實運作記錄 | `/command` 入口 |
> |------|-------------|----------------|
> | self-correcting-loop | [RUN.md](sandboxes/self-correcting-loop/RUN.md) | [.claude/commands/self-correcting-loop.md](.claude/commands/self-correcting-loop.md) |
> | openshell-containment | [RUN.md](sandboxes/openshell-containment/RUN.md) | [.claude/commands/sandbox-openshell.md](.claude/commands/sandbox-openshell.md) |
> | turbovec | [RUN.md](sandboxes/turbovec/RUN.md) | [.claude/commands/turbovec.md](.claude/commands/turbovec.md)（compose openshell-containment） |
> | sandcastle-orchestration | [RUN.md](sandboxes/sandcastle-orchestration/RUN.md) | [.claude/commands/sandcastle-orchestration.md](.claude/commands/sandcastle-orchestration.md) |

## 通用框架 — 一條雙向 producer↔consumer 鏈

一個沙盒**不是**被 Claude 單向「呼叫的函式」。它與 Claude 之間是一條**雙向生產者-消費者**鏈，接合點是
`/command` 入口檔（`.claude/commands/<name>.md`）裡的 **`!`cmd`` dynamic context injection**：

```
   人決定 WHAT（target / rubric / 何時調用）
        │
        ▼
  /command 入口  ──①沙盒生產「runtime 狀態」──►  Claude 消費注入（基於真實狀態，非過時猜測）
   (.claude/                                            │
    commands/)                                    ②Claude 生產「驅動/判斷」
        ▲                                       （PLAN/DO/VERIFY 或 launch+exec）
        │                                                │
   ④Claude 消費「裁決」                                    ▼
   達標→交付 / 未達→下一輪 or SURFACE 交人          沙盒確定性 kernel
        │                                        （消費 Claude 的產出）
        └──────③沙盒生產「確定性裁決」◄───────────────────┘
                FINAL·ITERATING / count_metric / exit code
```

四個半，每半都有明確的**生產者**與**消費者**：

1. **① 沙盒生產 runtime 狀態 → Claude 消費**
   調用 `/command` 的瞬間，入口 body 的 `!`cmd`` 被執行，把沙盒**當前真實 runtime 狀態**的 stdout 注入
   Claude 的 context。這是「被調用才執行」的接口級實現——沙盒把「我現在是什麼狀態」生產出來餵給 Claude。
2. **② Claude（+人）生產驅動/判斷 → 沙盒消費**
   Claude 消費注入的狀態，依入口 body 的執行步驟驅動沙盒的 `src/` 能力（評分、launch、在沙盒內 exec 代碼）。
3. **③ 沙盒的確定性 kernel 生產裁決 → Claude 消費**
   kernel 消費 Claude 的產出（scorecard / 待執行碼），生產**確定性 verdict**（FINAL/ITERATING、
   count_metric、exit code）——不是 LLM 的散文宣稱。
4. **④ Claude 消費裁決決定下一步** → 達標交付；未達標下一輪 or `no_progress`/`exhausted`/`failure` → SURFACE 交人。

### 設計分工 — 生產的「分工」就是這套系統的核心約束

| 由**人 / Claude（LLM）**生產 | 由**沙盒 kernel**生產 |
|------------------------------|----------------------|
| WHAT：target、rubric、何時調用、是否接受結果 | 確定性 DECIDE/VERIFY：FINAL、`count_metric`、exit code |
| ② 的判斷：評分（VERIFY）、寫待執行碼 | ① 的真實 runtime 狀態快照 |

**沒有「沙盒自動接受結果、自動續跑」的循環。** 達標與否由確定性 kernel 裁；是否接受由人。
這就是為什麼**每個沙盒**的「達標」判定（FINAL / fully-contained / air-gapped / FEASIBLE / PASS）全部由**確定性 kernel**
（real scores / exit code / `count_metric`）裁，而不是 agent 說「我覺得可以了」。

## 原 3 沙盒對照（同一框架，三種裁決度量）

| | self-correcting-loop | openshell-containment | turbovec |
|---|---|---|---|
| **① 注入（生產什麼狀態）** | `loop_kernel.py state` → loop 狀態快照（迭代數/最弱項/守衛旗標） | gateway+container status、最新 verdict、container logs tail | SKILL.md：trace tail + `ns-sandbox` 內 turbovec 探測 |
| **② 消費驅動** | PLAN（鎖最弱項）→ DO → VERIFY（評分寫 scorecard） | launch contract → `sandbox_runner` exec 代碼 / `containment_probe` | compose openshell 前置 → `containment_rag_probe` |
| **③ 裁決度量** | `FINAL`(exit0) / `ITERATING`(exit3)+focus | `count_metric`（0 = 3-case 全 contained） | `count_metric`（0 = recall 對 ∧ egress 拒） |
| **④ 真實 live 結果** | selftest 6/6；decide `FINAL`✓ / `ITERATING` focus=readability | `cases=3 failures=0`；egress→curl56/403、`/Users` 不可見 | `count_metric=0`；`recall_at1=1.0 n=2000`、egress 拒 |
| **live 依賴** | 無（純 python3，到處可 live） | OpenShell CLI + Docker | 上者 + 一次性 staged abi3 wheels |
| **入口形態** | `.claude/commands/self-correcting-loop.md` | `.claude/commands/sandbox-openshell.md`（`/openshell-containment` 為 DOC-ONLY 別名） | `.claude/commands/turbovec.md`（compose openshell-containment） |

> 三沙盒在本機**全部真跑出 exit 0 / count==0**（見各 RUN.md）；測試層在無 Docker/OpenShell 的機器上仍
> 一鍵全綠（`bash run-tests.sh`，mock 外部邊界）。

## 其餘 4 沙盒（同一框架，各自的裁決度量）— 條列式

後加入的 4 個沙盒套同一條「Claude 生產 ↔ 沙盒確定性 kernel 生產裁決」鏈，只是裁決度量不同：

- **sandcastle-orchestration** — ① 注入 sandcastle run 狀態 → ② host-run 容器隔離 agent（Path A）/ Path B 純函數投影 →
  ③ 裁決度量 = `observation-record`（container-isolation / exec-gate verdict / branch-merge-back-outcome，純函數零 LLM）→
  入口 `.claude/commands/sandcastle-orchestration.md`。live：Path B 純 python3；Path A 另需 Docker + Node + 一次性 token。
- **DR-judge fleet（純 python3，DECIDE 復用 `self-correcting-loop` kernel）** — ① 注入 Judge 當前 rubric/狀態 →
  ② Claude 對 target 評分 / 量測 → ③ 裁決度量各異，全確定性：
  - `arch-fitness` — `verdict=PASS iff 0 hard 違規` + `focus`（Clean-Arch 分層 / module-boundary / Martin I/A/D / AST 壞味道）。
  - `capacity-estimation` — `FEASIBLE(exit0)/INFEASIBLE(exit3)` + 綁定約束 + 宏觀/微觀槓桿（5 DR 容量指標 vs budget）。
  - `fullstack-design-judge` — `FINAL/ITERATING` over 10 macro + 11 micro 軸；runtime trace 印 `CONSUMED:self-correcting-loop`。
  - 入口：`.claude/commands/{arch-fitness,capacity-estimation,fullstack-design-judge}.md`；live 全部只需 python3。

> 7 沙盒一鍵全綠（`bash run-tests.sh` → ALL GREEN，169 passing）；裁決全由確定性 kernel 產，非 agent 散文宣稱。

## 一鍵重現

```bash
# 測試層（任何裝了 python3+pytest 的機器）：
bash run-tests.sh          # → ALL GREEN（selftest 6/6 + pytest 25/8/5）

# live 層（self-correcting-loop 純 python3 即可；另兩個需 OpenShell+Docker）：
(cd sandboxes/self-correcting-loop && python3 src/loop_kernel.py selftest --iso 2026-06-23)
python3 sandboxes/openshell-containment/src/containment_probe.py --iso <ISO> -n ns-sandbox
python3 sandboxes/turbovec/src/containment_rag_probe.py -n ns-sandbox
```
