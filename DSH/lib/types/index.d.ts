import type { Context } from '@deepseek-ai/cordis';
import type { PreToolDecision } from '@deepseek-ai/dsh-tools';

export interface BashPolicyRule {
  readonly id?: string;
  readonly tier: 'allow' | 'ask' | 'deny';
  readonly reason?: string;
  readonly patterns: readonly string[];
}

export interface BashPolicyConfig {
  readonly ruleFile?: string;
}

export declare const DEFAULT_RULE_FILE: string;
export declare const name: 'tool-bash-policy';
export declare const inject: readonly ['tools'];
export declare function loadRules(path: string): readonly BashPolicyRule[];
export declare function decisionFor(command: string, rules: readonly BashPolicyRule[]): PreToolDecision;
export declare function apply(ctx: Context, config?: BashPolicyConfig): void;
export { apply as default };
