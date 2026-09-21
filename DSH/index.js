import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { parse } from "yaml";

const DEFAULT_RULE_FILE = join(homedir(), ".config", "dsh", "bash-policy.yml");
const TIERS = new Set(["allow", "ask", "deny"]);

function normalizeRule(rule, index) {
  if (!rule || typeof rule !== "object") throw new Error(`bash-policy: rule ${index + 1} must be an object`);
  const tier = rule.tier;
  if (!TIERS.has(tier)) throw new Error(`bash-policy: rule ${index + 1} has invalid tier ${JSON.stringify(tier)}`);
  const patterns = Array.isArray(rule.patterns) ? rule.patterns.filter((value) => typeof value === "string" && value.length > 0) : [];
  if (patterns.length === 0) throw new Error(`bash-policy: rule ${index + 1} must contain a non-empty patterns array`);
  return {
    id: typeof rule.id === "string" && rule.id.length > 0 ? rule.id : `rule-${index + 1}`,
    tier,
    reason: typeof rule.reason === "string" && rule.reason.length > 0 ? rule.reason : undefined,
    patterns
  };
}

function compilePattern(pattern) {
  // Patterns are intentionally literal, case-sensitive substrings. This avoids
  // shell parsing surprises and makes the policy file easy to audit.
  return pattern;
}

function loadRules(path) {
  let source;
  try {
    source = readFileSync(path, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw new Error(`bash-policy: cannot read ${path}: ${String(error)}`);
  }
  let document;
  try {
    document = parse(source) ?? {};
  } catch (error) {
    throw new Error(`bash-policy: invalid YAML in ${path}: ${String(error)}`);
  }
  if (!document || typeof document !== "object" || !Array.isArray(document.rules)) {
    throw new Error(`bash-policy: ${path} must contain a rules array`);
  }
  return document.rules.map(normalizeRule).map((rule) => ({
    ...rule,
    patterns: rule.patterns.map(compilePattern)
  }));
}

function matchingRules(command, rules) {
  return rules.filter((rule) => rule.patterns.some((pattern) => command.includes(pattern)));
}

function decisionFor(command, rules) {
  const matches = matchingRules(command, rules);
  const deny = matches.filter((rule) => rule.tier === "deny");
  if (deny.length > 0) return {
    kind: "deny",
    reason: `Command review denied by ${deny.map((rule) => rule.id).join(", ")}: ${deny[0].reason ?? "this command matches a denied operation"}.`
  };
  const allow = matches.filter((rule) => rule.tier === "allow");
  if (allow.length > 0) return { kind: "allow" };
  const ask = matches.filter((rule) => rule.tier === "ask");
  if (ask.length > 0) return {
    kind: "ask",
    reason: `Command review required (${ask.map((rule) => rule.id).join(", ")}): ${ask[0].reason ?? "this command matches an operation requiring approval"}.`
  };
  return {
    kind: "ask",
    reason: "Command review required: no rule matched this command, so the default policy is ask."
  };
}

function commandFromExecution(exec) {
  if (!exec || exec.name !== "bash") return undefined;
  const args = exec.arguments;
  if (!args || typeof args !== "object" || typeof args.command !== "string") return undefined;
  return args.command;
}

function apply(ctx, config = {}) {
  const ruleFile = config.ruleFile ?? DEFAULT_RULE_FILE;
  const rules = loadRules(ruleFile);
  ctx.on("tools/pre-execute", async (exec, next) => {
    const command = commandFromExecution(exec);
    if (command === undefined) return next();
    if (exec.signal.aborted) return { kind: "deny", reason: "Command review cancelled because the tool call was aborted." };
    const decision = decisionFor(command, rules);
    if (decision.kind !== "ask") return decision;
    return decision;
  });
}

const name = "tool-bash-policy";
const Config = {
  ruleFile: "string"
};
const inject = ["tools"];

export { Config, DEFAULT_RULE_FILE, apply, decisionFor, inject, loadRules, name };
export default apply;
