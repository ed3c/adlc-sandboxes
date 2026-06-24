// Real RIP harness (the WORKING composition).
//
// sandcastle `head`-run = container-isolated agent execution (the part that works on macOS) composed
// with host-side plain git (branch/commit = the "merge-back" OUTCOME) and a host-side exec-gate between
// stages. Deliberately AVOIDS sandcastle's worktree branch-merge-back: its gitdir correction is
// Windows-only (chunk-5VM5QZ26.js:26853 `if (platform !== "win32") return gitMounts`), so on macOS the
// in-container `git checkout --detach` fails ("not a git repository: .../.git/worktrees/<name>").
//
// Containment invariant: operates ONLY on TARGET (a throwaway repo under the OS temp dir), never the
// host's own working repo.
//
// Honest boundary: this Path A run needs Docker + Node + a Claude OAuth token (the in-container agent).
// The deterministic Path B half (src/boundary_adapter.py) runs green standalone with just python3.
//
// Run from the sandbox dir:  npx tsx src/run_sandcastle.ts
import { run, claudeCode } from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";
import { execFileSync } from "node:child_process";
import { writeFileSync, cpSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";

// All paths are repo-relative or under the OS temp dir — no hardcoded absolute paths.
const SANDBOX = dirname(dirname(fileURLToPath(import.meta.url))); // .../sandboxes/sandcastle-orchestration
const FIXTURE = join(SANDBOX, "fixture");
const RESULT_OUT = join(SANDBOX, "trace", "rip-result.json");
// Throwaway target repo: holds .sandcastle/.env (the OAuth token) + the seeded fixture. Outside the repo.
const TARGET = process.env.SANDCASTLE_TARGET ?? join(tmpdir(), "sandcastle-target");
const IMAGE = "sandcastle:sandcastle-orchestration";

const gitEnv = { ...process.env };
delete gitEnv.GIT_DIR;
delete gitEnv.GIT_WORK_TREE; // no parent-repo git env pollution
const git = (...args) =>
  execFileSync("git", ["-C", TARGET, ...args], { encoding: "utf8", env: gitEnv }).trim();

// Ensure the throwaway exists + is a git repo (idempotent). Auth: the inner agent needs your own Claude
// subscription token under the throwaway's .sandcastle config (run `claude setup-token`; see sandcastle docs).
// Provide it yourself — never commit it.
mkdirSync(TARGET, { recursive: true });
const gitTry = (...args) => {
  try {
    return git(...args);
  } catch {
    return "";
  }
};
if (!gitTry("rev-parse", "--is-inside-work-tree")) {
  git("init", "-q");
  git("config", "user.email", "seed@local");
  git("config", "user.name", "seed");
}

// sandcastle resolves git mounts from process.cwd() (the `cwd` run-option alone is insufficient in 0.10.0),
// so chdir into the throwaway. git()/cpSync/RESULT_OUT all use absolute paths and are unaffected.
process.chdir(TARGET);

// 1. Reset throwaway working tree to the fixture seed (idempotent; preserve .git + .sandcastle/.env)
gitTry("checkout", "-f", "main"); // normalize to main, discard prior working changes
gitTry("branch", "-D", "agent/fix-sum"); // drop a prior run's agent branch
writeFileSync(join(TARGET, ".gitignore"), ".sandcastle/\nnode_modules/\n");
for (const f of readdirSync(TARGET)) {
  if (f === ".git" || f === ".sandcastle" || f === ".gitignore") continue;
  rmSync(join(TARGET, f), { recursive: true, force: true });
}
cpSync(FIXTURE, TARGET, { recursive: true });
git("add", "-A");
if (git("status", "--porcelain")) {
  git("-c", "user.email=seed@local", "-c", "user.name=seed", "commit", "-q", "-m", "seed: sum fixture (buggy)");
}
const seedSha = git("rev-parse", "HEAD");

// 2. implement — container-isolated agent (head strategy, writes directly to bind-mounted TARGET)
const implement = await run({
  agent: claudeCode("claude-sonnet-4-6"),
  sandbox: docker({ imageName: IMAGE }),
  cwd: TARGET,
  branchStrategy: { type: "head" },
  prompt:
    "`node --test` is failing because sum.js has a bug (it subtracts instead of adds). " +
    "Fix sum.js so the test passes. Change nothing else. Then output <promise>COMPLETE</promise>.",
  maxIterations: 3,
  name: "implement",
});

// 3. exec-gate — host-side deterministic verify between stages
let gateExit = 0;
try {
  execFileSync("node", ["--test"], { cwd: TARGET, encoding: "utf8", env: gitEnv });
} catch (e) {
  gateExit = e.status ?? 1;
}

// 4. review — container-isolated agent, only when the gate is green
let review = null;
if (gateExit === 0) {
  review = await run({
    agent: claudeCode("claude-sonnet-4-6"),
    sandbox: docker({ imageName: IMAGE }),
    branchStrategy: { type: "head" },
    prompt:
      "Review sum.js for correctness and style. If it is already correct, change nothing. " +
      "Output <promise>COMPLETE</promise>.",
    maxIterations: 1,
    name: "review",
  });
}

// 5. host-git — land the container-isolated work on a branch (the "merge-back" outcome via plain git)
const branch = "agent/fix-sum";
git("checkout", "-B", branch);
git("add", "-A");
let commit = "";
if (git("status", "--porcelain")) {
  git("-c", "user.email=agent@local", "-c", "user.name=agent", "commit", "-q", "-m", "agent: fix sum bug");
  commit = git("rev-parse", "HEAD");
}
git("checkout", "main");

// 6. capture combined result
const out = {
  schema: "sandcastle-rip/v0",
  composition: "sandcastle-head-run + host-git + host-exec-gate",
  seed_sha: seedSha,
  implement,
  exec_gate: { command: "node --test", exit: gateExit, passed: gateExit === 0 },
  review,
  host_git: { branch, commit, landed: Boolean(commit) },
  target_repo: TARGET,
};
writeFileSync(RESULT_OUT, JSON.stringify(out, null, 2));
console.log(
  "=== RIP done | exec_gate:",
  gateExit === 0 ? "PASS" : `FAIL(${gateExit})`,
  "| landed:",
  Boolean(commit),
  "| commit:",
  commit.slice(0, 8),
);
console.log("=== implement result keys:", Object.keys(implement).join(", "));
console.log("=== wrote", RESULT_OUT);
