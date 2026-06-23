# RUN — self-correcting-loop 的實際運作過程與結果

> 本檔 = 這個沙盒**在 Claude Code 裡的生產消費關係** + 一次**真實 live 運作**的完整 transcript（真命令、
> 真 stdout、真 exit code）。所有輸出採自本機真跑（python 3.14.3），非示意。

## 1. 在 Claude Code 的生產消費關係

這個沙盒與 Claude Code 之間是一條**雙向 producer↔consumer 鏈**，圍繞 `/command` 入口
（[`.claude/commands/self-correcting-loop.md`](../../.claude/commands/self-correcting-loop.md)）+ `!`cmd``
dynamic context injection：

```
   人提供 target+rubric
          │
          ▼
  /self-correcting-loop  ──①生產 runtime 狀態──►  Claude 消費注入
   （command 入口）         (!`loop_kernel.py state`)      │
          ▲                                          ②Claude 生產判斷
          │                                       PLAN→DO→VERIFY(評分)
   ④Claude 消費裁決                                       │
   FINAL→交付 / ITERATING→下輪聚焦最弱項                    ▼
          │                                    loop_kernel.py decide
          └──────③kernel 生產確定性裁決◄──────  (消費 scorecard)
                  FINAL(exit0) / ITERATING(exit3)+focus
```

| 半 | 誰生產 | 生產什麼 | 誰消費 |
|----|--------|---------|--------|
| ① | **沙盒** | `state --loop` 的真 stdout = 當前 loop 狀態快照（迭代數 / 上輪最弱項 / no-progress 旗標）注入 context | Claude |
| ② | **Claude（+人）** | PLAN（鎖上輪 focus）→ DO（改 artifact）→ VERIFY（對 rubric 每條給 1–10 分，寫 scorecard JSON） | 沙盒 kernel |
| ③ | **沙盒 kernel** | 確定性 verdict：`FINAL`(exit 0) iff ∀criterion ≥ threshold，否則 `ITERATING`(exit 3) + 最弱失敗項 | Claude |
| ④ | **Claude** | 消費 verdict 決定下一步：FINAL→回報終止；ITERATING→帶 focus 回 ② 下一輪 | （回到迴圈） |

**邊界原則**：沙盒只生產 ① 狀態 + ③ **確定性 DECIDE**；**評分（②的 VERIFY）由 LLM/人生產，
kernel 不代評分**；**target+rubric 由人提供、FINAL 結果由人接受**。kernel 回 `no_progress`/`exhausted`
= SURFACE 交人，**永不**自動接受結果、自動續跑。所以「FINAL」蘊含於真實分數，不是 agent 的散文宣稱
（確定性，零 LLM-judge）。

## 2. 實際運作過程與結果（真實 transcript）

### ① 生產半 — 調用瞬間注入的 runtime 狀態（首輪 sentinel）

`/command` body 的 `!`cmd`` 在調用瞬間執行，把當前 loop 狀態注入 Claude。首次調用尚無 state：

```console
$ python3 sandboxes/self-correcting-loop/src/loop_kernel.py state --loop default
[no-loop-state: default]          # exit 1 → 入口以 `|| echo "[no-loop-state exit=$?]"` 顯式處理
```
→ Claude 消費此注入，判定「這是第一輪」，據 rubric 規劃首版（而非用過時猜測）。

### ③ 生產半 — kernel 對 scorecard 的確定性裁決（兩個真結果）

VERIFY 寫好 scorecard 後，Claude 調 `decide`，kernel 消費 scorecard 生產 verdict。

**FINAL** — 三條 criterion 全 ≥ threshold(8)：
```console
$ (cd sandboxes/self-correcting-loop && python3 src/loop_kernel.py decide \
    --rubric src/fixtures/rubric.json --scorecard src/fixtures/scorecard-final.json \
    --loop demo --iso 2026-06-23)
{
  "verdict": "FINAL",  "focus": null,  "min_score": 8,  "failing": [],
  "per_criterion": {
    "professional": {"score": 9, "threshold": 8, "pass": true},
    "readability":  {"score": 8, "threshold": 8, "pass": true},
    "layout":       {"score": 9, "threshold": 8, "pass": true}
  },
  "loop_state": {"iterations": 1, "no_progress": false, "exhausted": false}
}
# exit 0  → Claude 消費：印 FINAL，回報終分 + scorecard，終止迴圈
```

**ITERATING** — readability=5 < threshold(8)，kernel 生產「下輪該聚焦哪一項」：
```console
$ (cd sandboxes/self-correcting-loop && python3 src/loop_kernel.py decide \
    --rubric src/fixtures/rubric.json --scorecard src/fixtures/scorecard-iterating.json \
    --loop demo --iso 2026-06-23)
{
  "verdict": "ITERATING",  "focus": "readability",  "min_score": 5,  "failing": ["readability"],
  "per_criterion": {
    "professional": {"score": 8, "threshold": 8, "pass": true},
    "readability":  {"score": 5, "threshold": 8, "pass": false},
    "layout":       {"score": 8, "threshold": 8, "pass": true}
  },
  "loop_state": {"iterations": 2, "no_progress": false, "exhausted": false}
}
# exit 3  → Claude 消費 focus="readability"，回 PLAN 下一輪、修復重點鎖 readability
```

### selftest — kernel 行為的確定性自驗（manifest `runtime_trace_cmd`）

```console
$ python3 sandboxes/self-correcting-loop/src/loop_kernel.py selftest --iso 2026-06-23
# loop_kernel selftest 2026-06-23 → 🟢
  PASS  final_verdict        PASS  final_focus_none
  PASS  iterating_verdict    PASS  iterating_focus
  PASS  malformed_failloud   PASS  out_of_range_failloud
# exit 0  (6/6)
```

### 測試套件 + LIVE 認證

```console
$ python3 -m pytest -q sandboxes/self-correcting-loop/tests/
......................... 25 passed in 0.15s          # exit 0
```
`trace/2026-06-23-fold-in-gate.record.json` → `verdict: LIVE`：static C1–C6 ✅ + qa 5/5 ✅ +
runtime selftest exit 0 ✅ + composition N/A。runtime-proven。

## 3. 誠實邊界

- **kernel 只機械化迴圈的 DECIDE 半**。PLAN/DO/VERIFY（含**評分本身**）= LLM 職責；kernel 不代生成分數，
  只裁分數是否達 threshold。
- 上面的 scorecard 取自 bundled fixtures（用戶範例 rubric：professional/readability/layout，threshold 8）。
  真實使用時 scorecard 由該輪 VERIFY 寫；rubric 由人提供。
- `src/loop_kernel.py` 是純函數 kernel（無 Ollama / 無網路 / 無 `datetime.now`，iso 由 caller 供）——
  故本沙盒**唯一沒有外部依賴**，`/command` 與底層能力在任何裝了 python3 的機器上即 live。
- loop-state 落 `state/<name>.json`（gitignored）。`decide` 會 advance 該 state；上面用 `--loop demo`
  示範，不污染 `default`。
