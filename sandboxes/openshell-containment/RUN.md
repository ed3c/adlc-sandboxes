# RUN — openshell-containment 的實際運作過程與結果

> 本檔 = 這個沙盒**在 Claude Code 裡的生產消費關係** + 一次**真實 live 運作**的 transcript。下方
> containment_probe 的輸出採自本機**真跑**（OpenShell gateway `Connected` v0.0.59、`ns-sandbox` Ready），
> 非 mock。

## 1. 在 Claude Code 的生產消費關係

圍繞 `/command` 入口（真名 `/sandbox-openshell`）的雙向 producer↔consumer 鏈。消費的是
**「在受隔離 sandbox 內執行 untrusted 代碼」** 這個能力，裁決由 `containment_probe` 的 `count_metric` 生產。

```
   人決定何時調用
        │
        ▼
 /sandbox-openshell  ──①生產 runtime 狀態──►  Claude 消費注入
  （command 入口）     ①gateway/container status         │
        ▲             ②最新 containment verdict     ②Claude 生產驅動
        │             ③gateway container logs tail   確認 Connected+Ready
  ④Claude 消費裁決                                  （缺則 bootstrap up）
  count==0→交付 / >0→SURFACE 交人                         │
        │                                                ▼
        │                              sandbox_runner.py exec  或  containment_probe.py
        └──────③kernel 生產確定性裁決◄──────  （在 ns-sandbox 內消費待執行碼 / 跑 3-case）
                count_metric (0=fully contained) + per-case verdict
```

| 半 | 誰生產 | 生產什麼 | 誰消費 |
|----|--------|---------|--------|
| ① | **沙盒/gateway** | 3 段 `!`cmd`` 注入：gateway+container status、最新 containment verdict record、container logs tail | Claude |
| ② | **Claude** | launch contract：確認 gateway `Connected` ∧ `ns-sandbox` `Ready`（缺則 `bootstrap up`），選消費入口 | 沙盒 |
| ③ | **沙盒 probe** | 確定性裁決：3 個 case（legit 寫須 PASS、egress 須 BLOCK、host-fs 須不可見）→ `count_metric` | Claude |
| ④ | **Claude** | `count_metric==0`→fully contained 交付；`>0`→SURFACED gap **交人**（report-only，不 auto-fix） | （人） |

**紅線**：本接口只**啟動 + 注入狀態 + 消費**已落地能力，**永不** auto-build / auto-iterate /
改沙盒策略 / 自動重試。一個人決定何時調用；接口只跑確定性步驟。任何 `failure: true` case 一律 SURFACE 交人。

## 2. 實際運作過程與結果（真實 transcript）

### ① 生產半 — 調用瞬間注入的 gateway/sandbox 真狀態

```console
$ bash sandboxes/openshell-containment/src/openshell_gateway_bootstrap.sh status
  gateway container: running
  Server Status
    Status:  Connected
    Version: 0.0.59
# exit 0 → gateway LIVE

$ openshell sandbox list
  NAME        CREATED              PHASE
  ns-sandbox  2026-06-10 20:08:59  Ready
```
→ Claude 消費此注入：gateway `Connected` ∧ `ns-sandbox` `Ready` ⇒ 直接進消費入口（bootstrap 冪等，免重跑）。

### ③ 生產半 — 真 LIVE containment_probe 的確定性裁決

probe 在 `ns-sandbox`（default-deny egress + fs 隔離）內跑 3 個對抗式 case，kernel 數 `count_metric`：

```console
$ python3 sandboxes/openshell-containment/src/containment_probe.py --iso 2026-06-24 -n ns-sandbox
# containment-probe (iso=2026-06-24, sandbox=ns-sandbox) — REPORT-ONLY
  cases=3  containment_failures=0  ✅ fully contained
  ✅ [legit]       legit_write:           contained
       evidence: ns-contained-ok
  ✅ [adversarial] egress_exfil_blocked:  contained
       evidence: curl: (56) CONNECT tunnel failed, response 403   [exit=56]
  ✅ [adversarial] fs_host_home_isolated: contained
       evidence: ls: cannot access '/Users': No such file or directory   [exit=2]
# PROBE_EXIT=0   → count_metric==0 = 邊界真的 FIRE（egress 被拒、host home 不可見）
```
→ Claude 消費 `count_metric==0`：判定 fully contained，回報 verdict + record 路徑，終止。
（若任一 case `failure: true` → 印 + 寫 record + **交人**，不在 command 內修。）

manifest 的 `runtime_trace_cmd` 是同 probe 的「只印 metric」形（給 gate 機械消費）：
```console
$ (cd sandboxes/openshell-containment && python3 src/containment_probe.py -n ns-sandbox --count)
0          # exit 0 + 印 "0" = fully contained
```

### 測試套件 + LIVE 認證

```console
$ python3 -m pytest -q sandboxes/openshell-containment/tests/
........ 8 passed in 0.85s          # exit 0（測試把 OpenShell 邊界 mock 掉，無 infra 也綠）
```
`trace/2026-06-11-fold-in-gate.record.json` → `verdict: LIVE`：static 接口檢查 ✅ + qa 4/4 ✅ +
runtime containment_probe exit 0 ✅（gateway Connected、ns-sandbox Ready、3 cases 0 failures）。runtime-proven。

## 3. 誠實邊界

- **本次是真 live**：本機恰有 OpenShell gateway `Connected`（v0.0.59）+ `ns-sandbox` `Ready`，故 probe 真跑
  並真的觀測到 egress 被拒（curl 56 / 403）、host `/Users` 不可見。**換一台沒有 OpenShell CLI + Docker 的機器，
  live probe 跑不起來**（precondition fail-loud，exit 1）——但 `pytest` 仍綠（mock 外部邊界）。
- **命名**：真入口 = `/sandbox-openshell`。manifest/SKILL 寫的
  `/openshell-containment` 是 **DOC-ONLY 別名**（無對應 command 檔）——PANORAMA 已更正記錄。
- probe 會把 verdict record 寫到 `data/production/containment/<iso>-containment-verdict.json`（**gitignored**，不隨 commit）。
- `src/sandbox_runner.py` 是 `openshell sandbox exec` 的 thin wrapper（OpenShell 仍 alpha，故 loosely-coupled）；
  `openshell_gateway_bootstrap.sh` 是冪等的 macOS gateway 拉起腳本。
