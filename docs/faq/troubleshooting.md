# Section 5: Troubleshooting {#troubleshooting}

Welcome to Section 5 of the OSA FAQ! This section covers common issues, errors, and solutions to help you resolve problems quickly and get back to improving your repositories.

## 5.1 What do I do if API key authentication fails? {: #what-if-api-key-fails}

API key authentication failures are common but usually easy to fix.

**Common Error Messages:**

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| `401 Unauthorized` | Invalid or expired API key | Regenerate key, check for typos |
| `403 Forbidden` | Key lacks required permissions | Check API dashboard for scopes |
| `Rate limit exceeded` | Too many requests | Wait or upgrade plan |
| `Invalid API key format` | Key malformed | Verify key starts with correct prefix |
| `Connection timeout` | Network/firewall issues | Check connectivity, proxy settings |

**Provider-Specific Solutions:**

| Provider | Verification Step | Common Issue |
|----------|-------------------|--------------|
| **OpenAI** | Check [API Keys Dashboard](https://platform.openai.com/api-keys) | Key expired, billing issues |
| **OpenRouter** | Verify at [openrouter.ai/keys](https://openrouter.ai/keys) | Credits depleted |
| **Ollama** | Test: `curl http://localhost:11434/api/tags` | Ollama not running |
| **ITMO** | Contact ITMO OpenSource team | Access credentials needed |
| **Gigachat** | Check Sber developer portal | Authorization key expired |

## 5.2 Why can't OSA access my repository?

Repository access issues typically stem from token permissions, URL format, or network problems.

**Common Access Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| `404 Not Found` | Wrong URL or private repo without token | Verify URL, add GIT_TOKEN |
| `403 Forbidden` | Token lacks permissions | Add `repo` scope to token |
| `Authentication failed` | Invalid/expired token | Regenerate Git token |
| `Repository not found` | Typo in URL or repo deleted | Double-check repository URL |
| `Connection refused` | Network/firewall blocking | Check proxy, firewall settings |

## 5.3 What if I get permission errors with Git?

Git permission errors prevent OSA from cloning, committing, or creating pull requests.

**Common Git Permission Errors:**

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Permission denied (publickey)` | SSH key not configured | Use HTTPS with token instead |
| `fatal: could not read Username` | No credentials configured | Set GIT_TOKEN environment variable |
| `remote: Repository not found` | Token lacks access | Add `repo` scope to token |
| `error: failed to push` | Branch protection rules | Request admin approval or disable protection |
| `403 Forbidden` on PR creation | Token lacks write access | Add `workflow` and `repo` scopes |

**Token Scope Reference:**

| Action | GitHub Scope | GitLab Scope |
|--------|--------------|--------------|
| Clone public repo | None | None |
| Clone private repo | `repo` | `read_repository` |
| Create branch | `repo` | `write_repository` |
| Commit changes | `repo` | `write_repository` |
| Create PR/MR | `repo` | `write_repository` |
| Update workflows | `workflow` | `api` |
| Fork repository | `repo` | `api` |

## 5.4 How do I fix Docker-related issues?

Docker issues can prevent OSA from running in containerized environments.

**Common Docker Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| `Cannot connect to Docker daemon` | Docker not running | Start Docker Desktop/service |
| `Permission denied` on socket | User not in docker group | `sudo usermod -aG docker $USER` |
| `Container exits immediately` | Missing environment variables | Check .env file format |
| `File not found` in container | Volume not mounted correctly | Use absolute paths, check mount syntax |
| `Build failed` | Dockerfile path wrong | Verify `-f docker/Dockerfile` path |
| `Out of memory` | Container memory limit | Increase Docker memory allocation |

```bash
# Run with verbose output
docker-compose up --build --verbose

# Check container logs
docker-compose logs osa

# Run interactive shell for debugging
docker-compose run osa /bin/bash
```

## 5.5 What if the LLM response is too long/short?

LLM response length issues can cause truncation or incomplete outputs.

**Response Length Problems:**

| Symptom | Cause | Solution |
|---------|-------|----------|
| Response cut off mid-sentence | `max_tokens` too low | Increase `--max_tokens` |
| Very brief responses | `max_tokens` too low or temperature too low | Increase both parameters |
| Repetitive content | Temperature too low | Increase `--temperature` |
| Incoherent responses | Temperature too high | Decrease `--temperature` |
| Context window exceeded | Repository too large | Use `--context_window` or split analysis |

**Adjusting Token Limits:**

```bash
# Default settings (may be insufficient for large repos)
python -m osa_tool.run -r <repo>
# --max_tokens 4096 (default)
# --context_window 16385 (default)

# For large repositories
python -m osa_tool.run \
  -r https://github.com/username/large-repo \
  --max_tokens 8192 \
  --context_window 32768

# For small, focused repos (faster, cheaper)
python -m osa_tool.run \
  -r https://github.com/username/small-repo \
  --max_tokens 2048 \
  --context_window 8192
```

**Token Limit Reference by Model:**

| Model | Max Output Tokens | Max Context Window | Recommended `--max_tokens` |
|-------|------------------|-------------------|---------------------------|
| GPT-3.5-turbo | 4096 | 16385 | 2048-4096 |
| GPT-4 | 4096 | 8192 | 2048-4096 |
| GPT-4o | 4096 | 128000 | 4096-8192 |
| Claude 3 | 4096 | 200000 | 4096-8192 |
| Llama 3 (70B) | 4096 | 8192 | 2048-4096 |
| Ollama (local) | Varies | Varies | 2048-4096 |

**Optimizing for Different Tasks:**

| Task | Recommended Settings |
|------|---------------------|
| **README Generation** | `--max_tokens 4096`, `--temperature 0.1` |
| **Docstring Generation** | `--max_tokens 2048`, `--temperature 0.05` |
| **Code Analysis** | `--max_tokens 4096`, `--temperature 0.1` |
| **Creative Suggestions** | `--max_tokens 2048`, `--temperature 0.3` |
| **Large Repository** | `--max_tokens 8192`, `--context_window 32768` |

```bash
# If repository exceeds context window:
# Option 1: Increase context window (if model supports it)
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --context_window 32768

# Option 2: Use model with larger context
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --model gpt-4o-128k \
  --context_window 128000
```

## 5.6 How do I adjust temperature and sampling parameters?

Temperature and sampling parameters control the creativity and determinism of LLM outputs.

**Parameter Overview:**

See [Model Parameters](technical-details.md#model-parameters) for details.

**Temperature Guide:**

| Temperature | Behavior | Best For |
|-------------|----------|----------|
| **0.0 - 0.1** | Highly deterministic, consistent | Docstrings, code generation, technical docs |
| **0.1 - 0.3** | Balanced, mostly deterministic | README generation, standard documentation |
| **0.3 - 0.5** | Some creativity | Suggestions, recommendations |
| **0.5 - 0.7** | Creative, varied outputs | Brainstorming, feature ideas |
| **0.7+** | Very creative, less reliable | Experimental, not recommended for OSA |

**Top_P (Nucleus Sampling):**

| Top_P Value | Effect | Use Case |
|-------------|--------|----------|
| **0.9 - 0.95** | Standard, good diversity | Default, most scenarios |
| **0.8 - 0.9** | More focused, less random | Technical documentation |
| **0.7 - 0.8** | Very focused, deterministic | Code generation, docstrings |
| **0.95 - 1.0** | Maximum diversity | Creative tasks (not recommended) |

**Combined Parameter Recommendations:**

| Use Case | Temperature | Top_P | Max_Tokens |
|----------|-------------|-------|------------|
| **Docstrings** | 0.05 | 0.9 | 2048 |
| **README** | 0.1 | 0.95 | 4096 |
| **CI/CD Scripts** | 0.05 | 0.9 | 4096 |
| **Analysis Report** | 0.1 | 0.95 | 4096 |
| **Suggestions** | 0.2 | 0.9 | 2048 |
| **Research Paper README** | 0.1 | 0.95 | 4096 |

## 5.7 Where do I report bugs? {: #how-to-report-bugs}

There are multiple channels for reporting bugs, requesting features, and getting help.

**Bug Reporting Channels:**

| Channel | Purpose | Response Time | Link |
|---------|---------|---------------|------|
| **GitHub Issues** | Bug reports, feature requests | 1-7 days | [github.com/aimclub/OSA/issues](https://github.com/aimclub/OSA/issues) |
| **Telegram Chat** | Quick questions, community help | Hours | [@OSA_helpdesk](https://t.me/OSA_helpdesk) |
| **Email** | Security issues, sensitive matters | 1-3 days | Contact via ITMO OpenSource |
| **Discussions** | General questions, ideas | 1-7 days | [GitHub Discussions](https://github.com/aimclub/OSA/discussions) |

**How to Report a Bug Effectively:**

**Bug Report Template:**

```markdown
## Bug Description
[Clear description of what's wrong]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [And so on...]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- OSA Version: [e.g., 1.0.0]
- Python Version: [e.g., 3.11.5]
- OS: [e.g., Ubuntu 22.04, macOS 14.0, Windows 11]
- Installation Method: [pip/Docker/source]
- LLM Provider: [OpenAI/Ollama/ITMO/etc.]

## Logs/Error Messages
```

[Paste relevant error messages or logs here]

```txt

## Additional Context
[Any other information that might help]
```

**Feature Requests:**

When requesting features, include:

```markdown
## Feature Request

## Problem Statement
[What problem does this solve?]

## Proposed Solution
[How should it work?]

## Use Cases
[Who would benefit from this?]

## Alternatives Considered
[What other solutions did you consider?]

## Additional Context
[Any other relevant information]
```
