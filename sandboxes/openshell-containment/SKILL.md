---
name: openshell-containment
description: >
  Invoke the OpenShell runtime-containment sandbox — run agent-generated code under enforced
  default-deny egress + filesystem isolation, and adversarially verify the boundary actually FIRES
  via the containment_probe (egress/fs/legit cases, report-only, deterministic no LLM-judge).
  觸發詞（triggers）: containment, sandbox, egress, isolation, openshell, containment-probe, enforced exec.
allowed-tools: Bash(bash *), Bash(python3 *), Bash(openshell *)
triggers: [containment, sandbox, egress, isolation, openshell, containment-probe, enforced-exec]
---

# /openshell-containment — enforced runtime containment + adversarial verification

> 沙盒接口：本 SKILL.md 同時創建 `/openshell-containment` /command **又**用
> `!`cmd`` dynamic context injection 把 OpenShell gateway / sandbox 的**當前 runtime 狀態**即時注入 context。
> 本接口**直接使用**containment 能力（report-only — 永不 auto-fix；surfaced gap 交人）。人決定何時調用。

## 啟動前置（啟動方式；fail-loud — 前置不滿足顯式錯誤，禁靜默偽完成）

containment 能力要求 LIVE gateway + Ready sandbox。invocation-time 注入真狀態：

- 前置檢查（gateway Connected → exit 0；否則 bootstrap 的 `status` exit 2）: !`bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status`

> ☝ 若上面顯示 gateway **NOT running / 非 Connected** → 顯式報錯，跑
> `bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh up --sandbox ns-sandbox` 拉起；
> **禁**在 gateway down 時偽裝 contained（fail-loud；containment_probe 自身 RuntimeError→exit 1）。

## 沙盒當前 runtime 狀態（≥1 個 live-state 注入）

注入 gateway + sandbox + 最近 containment verdict 的真 stdout（接口級實現——基於真實狀態調用）：

```!
openshell status 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | grep -iE "status|version" || echo "gateway: unreachable"
openshell sandbox list 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' || echo "no sandboxes"
ls -1 sandboxes/openshell-containment/trace/ 2>/dev/null | tail -3 || echo "no trace yet"
```

> ⚠ 硬要求：上面注入的是**當前 runtime 狀態**（真 stdout），非靜態文字。

## 能力與調用（沙盒做什麼）

`/openshell-containment` 被調用時：
1. 確認 gateway Connected + `ns-sandbox` Ready（上方注入；缺則 bootstrap `up`）。
2. 跑 `python3 src/containment_probe.py --iso <iso>` —— 3 個確定性 case（legit /sandbox write 須 PASS；
   adversarial egress 非 allowlist 須 BLOCK 403/curl56；adversarial /Users host-home 須 NOT visible）。
3. `count_metric == 0` = fully contained（boundary 真 FIRE）；`> 0` = SURFACED gap（印 + record，交人，**不 auto-fix**）。
4. 真 verdict record 落 `data/production/containment/<iso>-containment-verdict.json` + trace 落 `trace/`。
   placebo-guard discrimination：permissive sandbox **不能** score 0（classifier 是 pure function，單元測雙向）。

底層能力：`src/sandbox_runner.py`（thin `openshell sandbox exec` wrapper，loosely-coupled 因 OpenShell alpha）
+ `src/openshell_gateway_bootstrap.sh`（idempotent macOS 9-layer same-path keystone fix）。

## 全景圖註冊（存在 ≠ 接線）

本沙盒在 [`../PANORAMA.md`](../PANORAMA.md) 有對應 ```yaml sandbox``` block（the validation gate 機械查）。
