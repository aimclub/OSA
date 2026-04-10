# Section 3: Configuration & API Keys

Welcome to Section 3 of the OSA FAQ! This section covers everything you need to know about configuring OSA, setting up API keys, and managing tokens for seamless operation.

## 3.1 What tokens/API keys do I need? {: #what-tokens-needed }

OSA requires different tokens depending on your use case. Here's a complete overview:

| Token Name | Description | Mandatory | When Required |
|------------|-------------|-----------|---------------|
| **`GIT_TOKEN`** | Personal GitHub/GitLab/Gitverse token for cloning repos, accessing metadata, and creating PRs | ✅ Yes* | Always, unless using `--no-fork` with public repos |
| **`OPENAI_API_KEY`** | API key for OpenAI, VseGPT, OpenRouter providers | ❌ No | When using `--api openai` or compatible providers |
| **`ITMO_MODEL_URL`** | URL for ITMO-hosted LLM endpoint | ❌ No | When using ITMO's internal model |

\* *GIT_TOKEN can be omitted if you use `--no-fork` and work only with public repositories in read-only mode.*

**Token Alternatives:**

```bash
# Instead of GIT_TOKEN, you can use platform-specific tokens:
GITHUB_TOKEN=<your_github_token>    # For GitHub
GITLAB_TOKEN=<your_gitlab_token>    # For GitLab
GITVERSE_TOKEN=<your_gitverse_token> # For Gitverse
```

**Minimum Setup for Testing:**

```bash
# For public repos with ITMO model (no API key needed):
export GIT_TOKEN=your_token
# That's it! OSA will use default ITMO endpoint
```

## 3.2 How do I set up OPENAI_API_KEY?

Setting up your OpenAI API key is straightforward.

**Step 1: Get Your API Key**

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (it starts with `sk-`)

**Step 2: Set the Environment Variable**

| Platform | Command |
|----------|---------|
| **Linux/macOS (bash/zsh)** | `export OPENAI_API_KEY="sk-..."` |
| **Windows (PowerShell)** | `setx OPENAI_API_KEY "sk-..."` |
| **Windows (CMD)** | `set OPENAI_API_KEY=sk-...` |

**Step 3: Verify It Works**

```bash
# Check if variable is set
echo $OPENAI_API_KEY  # Linux/macOS
echo %OPENAI_API_KEY%  # Windows CMD

# Test with OSA
python -m osa_tool.run -r https://github.com/username/repo --api openai --model gpt-4
```

**Using in .env File (Recommended):**

```bash
# Create or edit .env in your project root
echo "OPENAI_API_KEY=sk-..." >> .env
```

**Security Best Practices:**

| ✅ Do | ❌ Don't |
|-------|----------|
| Store keys in `.env` (added to `.gitignore`) | Hardcode keys in scripts or commits |
| Use environment-specific keys | Share keys in public repositories |
| Rotate keys periodically | Use organization keys for personal projects |
| Limit key permissions in OpenAI dashboard | Grant unnecessary permissions |

**Troubleshooting:**

| Issue | Solution |
|-------|----------|
| "Invalid API key" error | Verify key format, check OpenAI dashboard for key status |
| "Rate limit exceeded" | Upgrade plan or reduce request frequency |

## 3.3 How do I set up GIT_TOKEN?

A Git token enables OSA to interact with your repositories (clone, create branches, open PRs).

**For GitHub:**

1. Go to [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)" or "Fine-grained token"
3. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Actions workflows)
   - ✅ `write:packages` (if publishing to GitHub Packages)
4. Generate and copy the token (starts with `ghp_`)

**For GitLab:**

1. Go to [GitLab Settings → Access Tokens](https://gitlab.com/-/user_settings/personal_access_tokens)
2. Name your token, set expiration
3. Select scopes:
   - ✅ `api` (Full API access)
   - ✅ `write_repository` (Clone/push code)
4. Create and copy the token

**Set the Environment Variable:**

```bash
# Linux/macOS
export GIT_TOKEN="ghp_..."

# Windows PowerShell
setx GIT_TOKEN "ghp_..."

# Or add to .env file
echo "GIT_TOKEN=ghp_..." >> .env
```

**Token Permissions Reference:**

| Action | Required Scope |
|--------|---------------|
| Clone public repo | None (token optional) |
| Clone private repo | `repo` (GitHub) / `read_repository` (GitLab) |
| Create branch/commit | `repo` / `write_repository` |
| Create Pull Request | `repo` / `write_repository` |
| Update CI/CD workflows | `workflow` (GitHub) / `api` (GitLab) |

**Using Platform-Specific Tokens:**

```bash
# GitHub
export GITHUB_TOKEN="ghp_..."

# GitLab  
export GITLAB_TOKEN="glpat-..."

# Gitverse
export GITVERSE_TOKEN="gv_..."
```

**Troubleshooting Git Token Issues:**

| Issue | Solution |
|-------|----------|
| "403 Forbidden" | Check token scopes, ensure repo access |
| "Authentication failed" | Verify token is current, not expired |
| "Rate limit exceeded" | Use fine-grained tokens, implement retry logic |
| Token not working with fork | Ensure token has `repo` scope for fork creation |

## 3.4 Which LLM providers are supported?

OSA supports multiple LLM providers through the [ProtoLLM](https://github.com/aimclub/ProtoLLM/) ecosystem.

**Supported Providers and Configuration:**

| Provider | API Type | Models Available | Cost | Best For | --api Value | --base-url | Auth Variable | Example Model |
|----------|----------|-----------------|------|----------|---------------|--------------|---------------|---------------|
| **OpenAI** | OpenAI-compatible | gpt-4, gpt-3.5-turbo, gpt-4o | 💰 Paid | High-quality, reliable results | openai | <https://api.openai.com/v1> | OPENAI_API_KEY | gpt-4o |
| **OpenRouter** | OpenAI-compatible | 100+ models (Claude, Llama, Mistral) | 💰/🆓 Mixed | Flexibility, cost optimization | openai | <https://openrouter.ai/api/v1> | OPENAI_API_KEY | qwen/qwen3-30b |
| **VseGPT** | OpenAI-compatible | OpenAI models via Russian proxy | 💰 Paid | Users in Russia/CIS region | openai | <https://api.vsegpt.ru/v1> | OPENAI_API_KEY | openai/gpt-3.5-turbo |
| **Ollama** | Local/Ollama API | Llama 3, Gemma, Mistral, custom | 🆓 Free | Privacy, offline use, customization | ollama | <http://localhost:11434> | None | gemma3:27b |
| **ITMO Hosted** | OpenAI-compatible | ITMO fine-tuned models | 🆓 Free* | Research, testing, ITMO community | openai | <https://osa.nsslab.onti.actcognitive.org/api/v1> | None (or ITMO_API_KEY) | itmo-research |
| **Gigachat** | Native API | GigaChat models by Sber | 💰 Paid | Russian language, local compliance | gigachat | (auto) | AUTHORIZATION_KEY | GigaChat |

## 3.5 How do I configure different LLM providers?

OSA autodetects provider from base url, but you can manually configure it with the following options:

Manual configuration varies slightly by provider. Here are complete examples for each:

**OpenAI (Default):**

```bash
# Set environment variables
export OPENAI_API_KEY="sk-..."

# Run OSA
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --api openai \
  --model gpt-4o \
  --base-url https://api.openai.com/v1
```

**OpenRouter:**

```bash
# OpenRouter uses OpenAI-compatible API
export OPENAI_API_KEY="sk-or-..."  # Your OpenRouter key

python -m osa_tool.run \
  -r https://github.com/username/repo \
  --api openai \
  --base-url https://openrouter.ai/api/v1 \
  --model qwen/qwen3-30b-a3b-instruct-2507
```

**VseGPT:**

```bash
export OPENAI_API_KEY="your-vsegpt-key"

python -m osa_tool.run \
  -r https://github.com/username/repo \
  --api openai \
  --base-url https://api.vsegpt.ru/v1 \
  --model openai/gpt-3.5-turbo
```

**Ollama (Local):**

```bash
# First, pull your model locally
ollama pull gemma3:27b

# Run OSA pointing to local Ollama instance
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --api ollama \
  --base-url http://localhost:11434 \
  --model gemma3:27b
```

## 3.6 Can I use local LLM models?

**Yes!** OSA fully supports local LLM models via Ollama or self-hosted OpenAI-compatible servers.

## 3.7 How do I use the ITMO hosted model?

ITMO University provides a hosted OSA endpoint for research and testing purposes.

**Access Options:**

| Option | Description | How to Use |
|--------|-------------|------------|
| **Public Web GUI** | No installation, browser-based | Visit [osa.nsslab.onti.actcognitive.org](https://osa.nsslab.onti.actcognitive.org/) |
| **Community Access** | For ITMO students/researchers | Contact ITMO OpenSource team for credentials |

## 3.8 What configuration options are available?

OSA offers extensive CLI configuration options. For the complete reference visit the [README.md](https://github.com/aimclub/OSA/blob/main/osa_tool/scheduler/README.md).

## 3.9 How do I use custom TOML configuration?

OSA supports custom configuration via TOML files for complex setups and reproducibility.

**Creating a TOML Configuration File:**

You can find the actual config file [config.toml](https://github.com/aimclub/OSA/blob/main/osa_tool/config/settings/config.toml).

**Using the Configuration File:**

```bash
# Run OSA with custom config
python -m osa_tool.run --config-file config.toml

# Override specific values via CLI (CLI takes precedence)
python -m osa_tool.run \
  --config-file config.toml \
  --model gpt-4o-mini \  # Overrides [llm].model
  --temperature 0.2      # Overrides [llm].temperature
```
