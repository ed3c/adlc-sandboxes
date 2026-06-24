# RUN — sandcastle-orchestration 的實際運作過程與結果

> 本檔 = 這個沙盒**在 Claude Code 裡的生產消費關係** + 一次**真實 RIP run**的完整 transcript（真命令、
> 真 stdout、真 exit code、真 commit sha）。Path A（容器內 agent run）的輸出採自一次真跑（sum fixture）；
> Path B（確定性投影）的輸出採自本機真跑（python3），非示意。

## 1. 在 Claude Code 的生產消費關係

這個沙盒與 Claude Code 之間是一條**雙向 producer↔consumer 鏈**，圍繞 `/command` 入口
（[`.claude/commands/sandcastle-orchestration.md`](../../.claude/commands/sandcastle-orchestration.md)）+ `!`cmd``
dynamic context injection：

```
   人決定 WHAT（何時跑、哪個 fixture、是否接受哪個 delta）
          │
          ▼
  /sandcastle-orchestration ──①生產 runtime 狀態──►  Claude 消費注入
   （command 入口）            (!`docker info` + adapter 投影)      │
          ▲                                            ②Claude 生產驅動
          │                                       Path A RIP run（容器內 agent）
   ④人消費 observation-record                              │
   分流哪個 delta 真 land（人裁，非自動）                      ▼
          │                                    boundary_adapter.py（Path B）
          └──────③沙盒生產確定性 observation-record◄──── (純函數投影 result.json)
```

| 半 | 誰生產 | 生產什麼 | 誰消費 |
|----|--------|---------|--------|
| ① | **沙盒** | `docker info` 活否 + adapter 對最近 result 的首行投影注入 context（當前真實 runtime 狀態） | Claude |
| ② | **Claude（+人）** | Path A RIP run：`head` agent 容器內修 → 主機端 exec-gate → review agent → 主機端 plain git branch/commit；dump `result.json` | 沙盒 adapter |
| ③ | **沙盒 adapter** | 確定性 observation-record：container-isolation / exec-gate verdict / branch-merge-back-outcome / token / 多階段（純函數，零 LLM-judge） | 人 |
| ④ | **人** | 消費 observation-record，分流哪個 delta 真 land（**人裁，沙盒不自動接受**） | （回到迴圈） |

**邊界原則**：沙盒只生產 ① 狀態 + ③ **確定性投影**；agent run（②）非確定故只能真跑證明，不 mock；
**何時跑 + 哪個 delta land 由人定**。沙盒 auto-turn 鎖在 inner container + fixture/throwaway repo 邊界內，
**永不碰宿主自己的工作 repo**。所以「landed/contained」蘊含於真 commit sha 與真 exit code，不是 agent 的散文宣稱。

## 2. 實際運作過程與結果（真實 transcript）

### ② 生產半 — Path A 一次真實 RIP run（sum fixture）

可行組合 = sandcastle `head`-run（容器隔離跑）+ 主機端 plain git（merge-back OUTCOME）+ 主機端 exec-gate。
`fixture/sum.js` 故意 buggy（`a - b` 而非 `a + b`），`node --test` 失敗；implement agent 在容器內修：

```console
$ npx tsx src/run_sandcastle.ts
=== RIP done | exec_gate: PASS | landed: true | commit: 879cea7c
=== implement result keys: iterations, completionSignal, stdout, commits, branch, logFilePath
=== wrote .../trace/rip-result.json
```

一次真跑捕捉到的 `result.json`（節選真值）：

- **implement**（容器隔離 agent，head 策略）：1 iteration，`completionSignal: <promise>COMPLETE</promise>`，
  stdout = `Test passes. Fixed `a - b` to `a + b` in sum.js.`；usage = `{input:1, cache_creation:190, cache_read:22579, output:32}`。
  `commits: []`（head 策略不在容器內 commit——merge-back OUTCOME 由主機端 git 落）。
- **exec_gate**（主機端確定性）：`node --test` → `exit: 0, passed: true`。gate 綠才放行 review。
- **review**（容器隔離 agent，gate 綠後才跑）：1 iteration，`<promise>COMPLETE</promise>`，
  stdout = `Removed the stale/incorrect comment; the implementation was already correct.`
- **host_git**（merge-back OUTCOME via plain git）：`branch: agent/fix-sum`、`commit: 879cea7cb854c59dc25034fa7edcfaaaf978710e`、`landed: true`。

### ③ 生產半 — boundary adapter 的確定性投影（Path B，純 python3）

adapter 把上面那份 `result.json` 純函數投影成 observation-record（無 Docker/token，本機即可跑）：

```console
$ python3 src/boundary_adapter.py emit --result tests/fixtures/result.sample.json --iso 2026-06-24
{
  "schema": "sandcastle-observation-record/v1",
  "iso": "2026-06-24",
  "composition": "sandcastle-head-run + host-git + host-exec-gate",
  "capabilities_exercised": {
    "container_isolation": true,
    "exec_gate": {"ran": true, "verdict": "pass", "command": "node --test", "exit": 0},
    "branch_merge_back_outcome": {"landed": true, "branch": "agent/fix-sum",
                                  "commit": "879cea7cb854c59dc25034fa7edcfaaaf978710e", "via": "host-git"},
    "multi_stage": {"implement": true, "review": true}
  },
  "agent_runs": [
    {"stage": "implement", "iterations": 1, "completion_signal": "<promise>COMPLETE</promise>",
     "tokens": {"input": 1, "cache_creation": 190, "cache_read": 22579, "output": 32}},
    {"stage": "review", "iterations": 1, "completion_signal": "<promise>COMPLETE</promise>",
     "tokens": {"input": 1, "cache_creation": 549, "cache_read": 22258, "output": 27}}
  ],
  "containment": {"target_repo": "/tmp/sandcastle-target", "host_repo_touched": false}
}
# exit 0
```

### selftest + 測試套件（確定性那半，一鍵可跑綠）

```console
$ python3 src/boundary_adapter.py selftest --iso 2026-06-24
# boundary_adapter selftest 2026-06-24 → 🟢
  PASS  record_well_formed       PASS  schema_id_ok
  PASS  host_repo_untouched      PASS  exec_gate_verdict_in_enum
  PASS  container_isolation_is_bool   PASS  merge_back_landed_is_bool
  PASS  roundtrip_json
# exit 0  (manifest runtime_trace_cmd)

$ python3 -m pytest -q tests/
.......................................... 42 passed          # exit 0
```

## 3. 誠實邊界

- **誠實薄 delta**：可行的那半（容器隔離跑）≈ 一般 containment 沙盒；真 delta = sandcastle 的**編排設計契約**
  （provider-agnostic + implement→exec-gate→review + iteration/prompt ergonomics）。本沙盒**不**宣稱 sandcastle
  自有 worktree merge-back 為能力——它在 macOS docker 下 run() **真跑壞**（成因 = worktree-id/session-capture，**非** win32 gitdir patch；真跑驗證見下方 §4），故組合**刻意繞開**它，
  改用主機端 plain git；「merge-back」在此是 OUTCOME（一個 branch + commit），≈ host git merge，不是 sandcastle 的能力宣稱。
- **Path A（RIP run）需 Docker + Node + 一次性 Claude OAuth token**（容器內 agent）。token 放在 throwaway repo 的
  `.sandcastle/.env`（gitignored）；目標 repo 預設在 `$TMPDIR/sandcastle-target`，可用 `SANDCASTLE_TARGET` 覆寫。
  agent run 非確定，故 Path A 靠**真跑一次**證明，不 mock。
- **Path B（boundary adapter）純 python3、無外部依賴**——`/command` 與這半在任何裝了 python3 的機器上即 live，
  `bash run-tests.sh` 跑的就是這半（42 tests + selftest，全綠、無 Docker/token）。
- adapter 是純函數投影（無 Ollama / 無網路 / 無 `datetime.now`，iso 由 caller 供）；`trace/*.log` gitignored，
  committed observation-record 是凍結 fixture（`tests/fixtures/result.sample.json`）。
- **沙盒不自動接受結果**：observation-record 只遞給人分流，哪個 delta 真 land = 人類 LAND-DECISION，非自動續跑。

## 4. 招牌 merge-back 真跑驗證（RIP — macOS 上 reproduced-BROKEN，含誠實過程）

sandcastle 的**招牌特性** = 自有 worktree branch-merge-back（`branchStrategy: merge-to-head / branch`）。本沙盒的可行組合
**刻意繞開**它、改用主機端 plain git——這節用一條**真跑鏈**記錄「為什麼」，並誠實記下我們一度判錯、又被真跑糾正。

**三步真跑（每步都是真命令、真 exit code）：**

1. **窄 probe（token-free）** `src/gitdir-probe.ts`：`createWorktree(merge-to-head) + createSandbox + 原生 docker exec`。
   容器把 host `.git` 掛在**同一絕對路徑**（mount source==target），故 worktree gitdir 解析得了、`git checkout --detach`
   **exit 0**。→ 一度據此推論「merge-back 在 macOS 可用」。**但這是過度推論——窄 probe ≠ 完整 `run()`。**

2. **完整 run() merge-to-head（真 agent）** `src/run-mtb.ts`（需 Docker + 一次性 OAuth token；agent 達
   `<promise>COMPLETE</promise>`）：

   ```console
   $ npx tsx src/run-mtb.ts
   [mtb] Started on branch sandcastle/mtb/...-d29484
   Agent started → <promise>COMPLETE</promise> → Agent stopped → Capturing session
   ExecError: Command failed (exit 128): git checkout --detach
   fatal: not a git repository: <repo>/.git/worktrees/sandcastle-mtb-...-d59026
   ```

   → **REPRODUCIBLY FAILS on macOS @0.10.0**：在 "Capturing session" 後跑 `git checkout --detach` 撞 **worktree-id 不匹配**
   （容器 ref `d59026` ≠ run branch `d29484`），**零 commit 落地**、fixture 保持乾淨。重現了招牌 merge-back 的失敗。

3. **裁定**：招牌 worktree merge-back 在 macOS @0.10.0 **真壞**——成因是 **worktree-id / session-capture 路徑**，
   **不是** `patchGitMountsForWindows`（那只是 Windows 磁碟機冒號的 mount 修補，posix 上 no-op 是正確的）。host 端
   `git merge` 本身平台無關，但 run() 撞容器端 `checkout --detach` 先掛、根本到不了 host merge。

**方法論教訓（RIP-study 的精華）**：**runtime 行為只能靠完整 RIP 真跑定案。** 步驟 1 的窄 probe 一度誤推「works」，
若就此收手會把錯結論當事實——只有步驟 2 的完整 `run()` 才釘死真相。**源碼讀 + 窄 probe 對 runtime 行為系統性
over-reach；真跑（RIP）才是行為的權威。** 這正是本沙盒「可行組合走 head-run + 主機端 git」的硬理由。
