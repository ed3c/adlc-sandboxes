// Token-free narrow probe on sandcastle 0.10.0 (= npm latest = the prior water-test version).
// 0.10.0's high-level Sandbox has NO .exec() (added in 0.11.0), so we createWorktree(merge-to-head) +
// createSandbox(docker) to get sandcastle's REAL container + worktree mount, then use raw `docker exec`
// (no agent, no ANTHROPIC token) to run the EXACT 0.10.0 failure command `git checkout --detach` inside it.
// `safe.directory *` is set to isolate the ownership check, so a failure here = the gitdir-resolution
// failure the 0.10.0 water-test saw ("not a git repository: .../.git/worktrees/<name>"), not ownership.
// PASS here only proves the NARROW mount path: the container CAN resolve the worktree gitdir on macOS
//         (.git mounted source==target). It does NOT prove run() merge-back works -- the FULL run()
//         merge-to-head RIP (run-mtb.ts) reproduced it BROKEN on macOS @0.10.0 (worktree-id/session-capture).
//         Lesson: runtime behavior is settled only by a full RIP, never a narrow probe. See RUN.md section 4.
import { execSync } from "node:child_process";
import { createWorktree } from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";

const FIXTURE = process.env.SANDCASTLE_TARGET ?? "/tmp/sandcastle-target";
const IMAGE = "sandcastle:sandcastle-orchestration";
const sh = (c: string) => execSync(c, { encoding: "utf8" });
const log = (...a: unknown[]) => console.log(...a);
let verdict = "UNKNOWN";

const wt = await createWorktree({ branchStrategy: { type: "merge-to-head" }, cwd: FIXTURE });
log("[createWorktree] OK (merge-to-head, cwd=" + FIXTURE + ")");
try {
  const sb = await wt.createSandbox({ sandbox: docker({ imageName: IMAGE }) });
  log("[createSandbox] OK — container up, worktree mounted (worktreePath=" + (sb as { worktreePath?: string }).worktreePath + ")");
  try {
    const cid = sh(`docker ps --latest --filter ancestor=${IMAGE} -q`).trim();
    log("[container] id=" + cid);
    const workdir = sh(`docker inspect -f '{{.Config.WorkingDir}}' ${cid}`).trim();
    log("[container WorkingDir] " + workdir);
    log("[container mounts]\n" + sh(`docker inspect -f '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\\n"}}{{end}}' ${cid}`));
    const probe = sh(
      `docker exec ${cid} sh -lc 'git config --global --add safe.directory "*"; cd "${workdir}" 2>/dev/null || cd /; echo "PWD=$(pwd)"; ` +
      `git rev-parse --is-inside-work-tree; echo "INSIDE_EXIT=$?"; ` +
      `git status -b --porcelain=v1 2>&1 | head -3; echo "STATUS_EXIT=${"$"}{PIPESTATUS:-$?}"; ` +
      `git checkout --detach 2>&1 | head -3; echo "DETACH_EXIT=${"$"}{PIPESTATUS:-$?}"'`
    );
    log("[docker exec git ops]\n" + probe);
    const ok = /INSIDE_EXIT=0/.test(probe) && /DETACH_EXIT=0/.test(probe) && /STATUS_EXIT=0/.test(probe);
    const gitdirFail = /not a git repository/i.test(probe);
    verdict = ok
      ? "MERGEBACK_INFRA_OK_ON_MACOS_0.10.0 — container resolves worktree gitdir; checkout --detach succeeds (failure was usage/path-calc, NOT platform/win32)"
      : gitdirFail
        ? "MERGEBACK_INFRA_FAILS_ON_MACOS_0.10.0 — 'not a git repository' gitdir failure reproduced"
        : "INCONCLUSIVE — see exec output (non-zero exit, different cause)";
  } finally {
    await sb.close();
    log("[sandbox.close] OK");
  }
} catch (e) {
  log("PROBE_ERROR:", e instanceof Error ? (e.stack || e.message) : String(e));
  verdict = "PROBE_ERROR";
} finally {
  await wt.close();
  log("[worktree.close] OK");
}
log("VERDICT:", verdict);
