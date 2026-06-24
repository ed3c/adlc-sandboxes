// Probe: does branch-merge-back (git-worktree strategy) work under containment when the throwaway
// repo is process.cwd() (NO `cwd` option)?  Hypothesis: the `cwd` option broke sandcastle's
// bind-mount path calc; process.chdir() aligns it so the worktree .git gitdir resolves in-container.
// node_modules still resolves from THIS script's dir (sandbox), not cwd. Run from the sandbox dir.
import { run, claudeCode } from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";

process.chdir(process.env.SANDCASTLE_TARGET ?? "/tmp/sandcastle-target"); // throwaway repo (override via SANDCASTLE_TARGET); process.cwd() = throwaway, no `cwd` option below

const result = await run({
  agent: claudeCode("claude-sonnet-4-6"),
  sandbox: docker({ imageName: "sandcastle:sandcastle-orchestration" }),
  branchStrategy: { type: "merge-to-head" }, // the strategy that failed with the cwd option
  prompt:
    "You are in a git repository. Create a new file named GREETING2.txt whose only content is the single line:\n" +
    "merge-back probe\n" +
    "Do not modify any other files. When finished, output <promise>COMPLETE</promise>.",
  maxIterations: 1,
  name: "mtb",
});

console.log("=== MTB RESULT KEYS:", Object.keys(result).join(", "));
console.log("commits:", JSON.stringify(result.commits));
console.log("branch:", JSON.stringify(result.branch));
