---
name: turbovec
description: >
  Air-gapped local vector search via turbovec, runtime-proven INSIDE the OpenShell ns-sandbox (default-deny
  egress) so "nothing leaves the machine" is a machine fact (count_metric==0), not prose.
  觸發詞（triggers）: vector-index, air-gapped-rag, turbovec, embedded-vector, local-rag, semantic-search.
allowed-tools: Bash(python3 *), Bash(openshell *), Bash(bash *)
---

# /turbovec — air-gapped local vector index, proven under containment

> 沙盒接口：本 SKILL.md 創建 `/turbovec` /command **又**用 `!`cmd`` dynamic context injection 把沙盒當前
> runtime 狀態即時注入。turbovec 是 instance #3，**compose** `openshell-containment`：其 runtime 在
> `ns-sandbox`（default-deny egress + fs 隔離）內跑，因此 turbovec 返回正確鄰居 + egress 被拒 = air-gapped
> RAG 機器證明。engine-locus 不破：人決定何時調用；本接口只是 LAND-EXECUTION 工具。

## 啟動前置（C5；fail-loud — 前置不滿足顯式錯誤，禁靜默偽完成）

- gateway 前置: !`bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status`

> ☝ 若上面顯示 gateway 非 Connected → 顯式報錯（`openshell_gateway_bootstrap.sh up` 起 gateway + ns-sandbox），
> **禁**降級偽 verdict（BS #339 / fail-loud）。turbovec 未 staged 進沙盒時，`/turbovec` 先跑
> `src/stage_turbovec_wheels.sh`（一次性、host-side、已授權的 offline wheel 注入）。

## 沙盒當前 runtime 狀態（C2 — MUST，≥1 個 live-state 注入）

```!
timeout 6 ls -1 sandboxes/turbovec/trace/ 2>/dev/null | tail -3 || echo "[no-trace-yet]"
timeout 12 openshell sandbox exec -n ns-sandbox --no-tty -- sh -c 'python3 -c "import turbovec; print(\"turbovec-staged-in-sandbox\")" 2>&1 | head -1' || echo "[turbovec-not-staged-in-sandbox exit=$?]"
```

> ⚠ C2：注入的是**當前 runtime 狀態**（trace tail + 沙盒內 turbovec 真實版本），非靜態文字。

## 能力與調用（沙盒做什麼）

被 `/turbovec` 調用時：跑 `src/containment_rag_probe.py -n ns-sandbox` — 在 ns-sandbox 內建一個 turbovec 索引
（deterministic seeded 向量，offline）+ self-query 驗 recall_at1=1.0，**且**驗 egress 被拒。`count_metric==0`
= air-gapped RAG 證明（exit 0）。任何 NOT-CONTAINED case → SURFACE 給人，**不 auto-fix**（engine-locus）。

## 因果鏈（C3 — 兩份分開，禁合併）

- 沙盒內因果鏈（技術落地脈絡）: [`causal-chain.md`](causal-chain.md)
- 吸收形式因果鏈（flywheel 吸收了什麼形式）: [`absorption-form.md`](absorption-form.md)

## 全景圖註冊（C4 — 存在 ≠ 接線，PG-157）

本沙盒須在 [`../PANORAMA.md`](../PANORAMA.md) 有對應 ```yaml sandbox``` block（fold-in gate 機械查）。
