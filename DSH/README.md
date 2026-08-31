# DSH Bash Policy Plugin

`@deepseek-ai/dsh-tool-bash-policy` is a deterministic command-review plugin for DSH. It reviews calls to the `bash` tool before they execute and classifies them as:

- `allow` — execute without prompting
- `ask` — pause for explicit user approval
- `deny` — reject automatically

Rules are literal substring patterns from a YAML file. Evaluation order is `deny`, then `allow`, then `ask`; commands that match no rule default to `ask`.

## Files

- `package.json` — plugin metadata
- `lib/index.js` — plugin implementation
- `lib/types/index.d.ts` — TypeScript declarations
- `bash-policy.example.yml` — example policy file

## Installation from Git

Clone the repository, or clone only this branch:

```bash
mkdir -p ~/.local/share/dsh/plugins
git clone --branch dsh-plugin --single-branch \
  https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git \
  ~/.local/share/dsh/plugins/dsh-tool-bash-policy
```

Replace `YOUR_USERNAME/YOUR_REPOSITORY` with the repository URL.

## Add it to a DSH profile

Edit the profile's `package.json`, normally:

```text
~/.dsh/profiles/web/package.json
```

Add the local plugin dependency. Replace `/home/USER` with the actual home directory:

```json
{
  "dependencies": {
    "@deepseek-ai/dsh-tool-bash-policy": "file:/home/USER/.local/share/dsh/plugins/dsh-tool-bash-policy"
  }
}
```

Add this row to the profile's `cordis.patch.yml`:

```yaml
- insert:
    - id: tool-bash-policy
      name: '@deepseek-ai/dsh-tool-bash-policy'
      config:
        ruleFile: '/home/USER/.config/dsh/bash-policy.yml'
```

## Create the policy file

```bash
mkdir -p ~/.config/dsh
cp ~/.local/share/dsh/plugins/dsh-tool-bash-policy/bash-policy.example.yml \
  ~/.config/dsh/bash-policy.yml
```

Edit `~/.config/dsh/bash-policy.yml` to customize the rules. A rule has this form:

```yaml
- id: allow-git-status
  tier: allow
  reason: "shows repository status"
  patterns:
    - "git status"
```

Patterns are literal, case-sensitive substrings. Do not put secrets or personal absolute paths in a shared policy file.

## Start or reload DSH

Restart the DSH web process and refresh:

```text
http://127.0.0.1:3080
```

The plugin is loaded at DSH startup, so refreshing the browser alone is not enough after changing the plugin or profile configuration.

## Test classifications

With the example policy:

```text
pwd             -> allow
npm install     -> ask
curl https://…  -> ask
rm -rf /        -> deny
unknown command -> ask
```

The `ask` decision is one-shot and uses DSH's configured approval answerer. If no approval answerer is available, DSH fails closed.

## Local development

The plugin has no build step. Test its classifier with the installed DSH runtime:

```bash
node --input-type=module <<'NODE'
import { loadRules, decisionFor } from './lib/index.js';
const rules = loadRules('./bash-policy.example.yml');
for (const command of ['pwd', 'npm install', 'rm -rf /', 'unknown command']) {
  console.log(command, decisionFor(command, rules));
}
NODE
```
