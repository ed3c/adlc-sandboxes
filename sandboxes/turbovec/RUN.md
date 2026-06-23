# RUN — turbovec 的實際運作過程與結果

> 本檔 = 這個沙盒的**消費關係** + 一次**真實 live 運作**的 transcript。下方
> containment_rag_probe 採自本機**真跑**（turbovec 已 staged 進 `ns-sandbox`，`recall_at1=1.0`），非 mock。

## 1. 消費關係

turbovec **compose `openshell-containment`**——它沒有自己獨立的 `/command` 入口檔，
消費路徑**嫁接**在 openshell 的 `ns-sandbox` 之上：

- **無獨立 command 入口**：SKILL.md frontmatter 宣告 `/turbovec` 並含 `!`cmd`` 注入契約，但本 repo
  **沒有** `commands/turbovec.md`（DOC-ONLY，誠實標記）。故 `/turbovec` 不會被動
  載入。它的真實消費路徑有二：(a) 經 `/sandbox-openshell` 的 `--exec` 在 `ns-sandbox` 內跑 turbovec；
  (b) 直接跑 host-side orchestrator `containment_rag_probe.py`
  （它內部用 `openshell sandbox exec` 進 sandbox）。
- **compose 而非新引擎**：turbovec 的 runtime **住在 openshell-containment 的 sandbox 裡**——所以「air-gapped」
  不是 turbovec 自稱，是 openshell 的 default-deny egress 邊界**替它**保證的。

```
   人決定何時調用
        │
        ▼
  （無獨立 /command；經 /sandbox-openshell --exec 嫁接 或 直接 containment_rag_probe.py）
        │
   ①生產 runtime 狀態 ── SKILL.md !`cmd`：trace tail + ns-sandbox 內 `import turbovec` 探測
        │
   ②Claude 消費 → 確認 openshell gateway/ns-sandbox 就緒（compose openshell-containment 的前置）
        │
   ③containment_rag_probe：在 ns-sandbox 內 build turbovec 索引 + self-query（offline）+ 試 egress
        │
   ④kernel 生產 count_metric（0 = recall 對 AND egress 被拒 = air-gapped RAG 機器事實）
        │
   ⑤Claude 消費：count==0→air-gapped 交付 / >0→NOT-CONTAINED 交人（不 auto-fix）
```

| 半 | 誰生產 | 生產什麼 | 誰消費 |
|----|--------|---------|--------|
| ① | **沙盒** | SKILL.md `!`cmd`` 注入：turbovec trace tail + `ns-sandbox` 內 turbovec staged 探測 | Claude |
| ② | **Claude** | 確認 compose 前置（openshell gateway `Connected` ∧ `ns-sandbox` `Ready`；未 staged 則先 `stage_turbovec_wheels.sh`） | 沙盒 |
| ③ | **沙盒 probe** | 在 sandbox 內 build index + self-query 驗 `recall_at1`，**且**試 egress；數 `count_metric` | Claude |
| ④ | **Claude** | `count_metric==0`（recall 對 ∧ egress 拒）→ air-gapped 交付；`>0`→交人 | （人） |

## 2. 實際運作過程與結果（真實 transcript）

### ① 生產半 — 調用瞬間注入的前置與 runtime 狀態

```console
# 前置（compose openshell-containment）：
$ bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status
    Status:  Connected     Version: 0.0.59      # gateway LIVE, ns-sandbox Ready

# SKILL.md C2 注入：turbovec trace tail
$ ls -1 sandboxes/turbovec/trace/ | tail -3
  2026-06-18-fold-in-gate.record.json
```

### ③ 生產半 — 真 LIVE containment_rag_probe 的確定性裁決

```console
$ python3 sandboxes/turbovec/src/containment_rag_probe.py -n ns-sandbox
# containment-rag-probe (iso=n/a, sandbox=ns-sandbox) — REPORT-ONLY
  cases=2  count_metric=0  ✅ air-gapped RAG proven
  ✅ [legit]       rag_works_offline:  contained
       evidence: RAG_OK recall_at1=1.0 n=2000 dim=64 bit=4
  ✅ [adversarial] rag_egress_denied:  contained
       evidence: curl: (56) CONNECT tunnel failed, response 403   [exit=56]
# RAGPROBE_EXIT=0   → count_metric==0 = turbovec 在沙盒內正確檢索(recall=1.0) 且 沒有東西離開機器
```
→ Claude 消費 `count_metric==0`：判定 air-gapped RAG 成立（**檢索能跑** ∧ **egress 被拒**兩個條件
同時為真才 0），回報終止。`recall_at1=1.0` 於 2000 條 64 維向量、4-bit 量化的 deterministic seeded 集。

### 測試套件 + LIVE 認證

```console
$ python3 -m pytest -q sandboxes/turbovec/tests/
..... 5 passed in 0.11s          # exit 0（mock 沙盒邊界，無 infra 也綠）
```
`trace/2026-06-18-fold-in-gate.record.json` → `verdict: LIVE`：static C1–C5 ✅ + qa 3/3 ✅ +
runtime containment_rag_probe exit 0 ✅。runtime-proven。

## 3. 誠實邊界

- **本次是真 live**：turbovec 已 staged 進本機 `ns-sandbox`（probe 測得 `recall_at1=1.0`），故真跑成功。
  **full live 較重**：需 (1) openshell-containment gateway 就緒 + (2) 一次性
  `bash src/stage_turbovec_wheels.sh`（host-side、已授權的 **offline abi3 wheel** 注入沙盒）。缺任一 → probe
  precondition fail-loud。無 infra 時 `pytest` 仍綠（mock）。
- **`/turbovec` 是 DOC-ONLY**：沒有 `commands/turbovec.md`，不會被動載入。消費走 `/sandbox-openshell`
  嫁接或直接 probe（見上）。本沙盒**不為它偽造 command 入口**（honest boundary）。
- **air-gapped 由 compose 保證**：egress-deny 是 openshell-containment 的邊界；turbovec 只負責「在裡面能正確
  檢索」。兩條件 AND 成立才 `count_metric==0`——任一破即非 air-gapped。
