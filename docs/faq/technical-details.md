# Section 7: Technical Details

Welcome to Section 7 of the OSA FAQ! This final section covers the technical architecture, underlying technologies, model recommendations, and advanced configuration options for developers and power users.

## 7.1 What technologies does OSA use?

OSA is built on a modern technology stack designed for flexibility, performance, and extensibility.

**Core Technology Stack:**

| Technology | Version | Purpose |
|------------|---------|---------|
| **🐍 Python** | 3.11+ | Main programming language |
| **🤖 ProtoLLM** | Latest | LLM abstraction layer for multiple providers |
| **🌐 AIOHTTP** | Latest | Async HTTP client for API calls |
| **✅ Pydantic** | Latest | Data validation and settings management |
| **🌳 TreeSitter** | Latest | Code parsing for documentation generation |
| **🐳 Docker** | Latest | Containerization for consistent deployment |
| **⚙️ GitHub Actions** | Latest | CI/CD automation for OSA itself |
| **📄 MkDocs** | Latest | Documentation generation and deployment |

**Key Dependencies:**

| Package | Purpose | Required |
|---------|---------|----------|
| `aiohttp` | Async HTTP requests | ✅ Yes |
| `pydantic` | Configuration validation | ✅ Yes |
| `python-dotenv` | Environment variable management | ✅ Yes |
| `tree-sitter` | Code parsing | ✅ Yes |
| `tree-sitter-python` | Python language grammar | ✅ Yes |
| `openai` | OpenAI API client | ⚠️ If using OpenAI |
| `requests` | HTTP library | ✅ Yes |
| `pyyaml` | YAML parsing for workflows | ✅ Yes |
| `mkdocs` | Documentation generation | ✅ Yes |

**Multi-Agent System (Experimental):**

OSA employs an experimental multi-agent system (MAS) for automatic and conversational modes:

Multi-agent script can be run with the following command:

```bash
python -m osa_tool.run_chat
```

| Agent | Responsibility | Status |
|-------|----------------|--------|
| **Repository Analyzer** | Scans repo structure, identifies key files | ✅ Stable |
| **README Generator** | Creates README files (standard/article) | ✅ Stable |
| **Docstring Agent** | Generates code documentation | ✅ Stable |
| **CI/CD Agent** | Creates workflow configurations | ✅ Stable |
| **Validation Agent** | Checks code quality and consistency | 🚧 Developing |
| **Conversational Agent** | Natural language interaction | 🚧 Developing |

**Agent Communication:**

- Agents communicate via a **shared state**
- Coordinated through a **directed state graph**
- Enables **conditional transitions** and **iterative workflows**

## 7.2 How does OSA handle repository cloning?

OSA uses Git to clone repositories locally for analysis, then manages changes through branches and pull requests.

**Cloning Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--no-fork` | Clone original repo directly (read-only) | `False` |
| `--delete-dir` | Remove cloned repo after processing | `disabled` |
| `--output` | Custom output directory | Current directory |
| `--branch` | Specific branch to checkout | Default branch |

**Platform-Specific Cloning:**

| Platform | Clone URL Format | API Endpoint |
|----------|-----------------|--------------|
| **GitHub** | `https://github.com/user/repo.git` | `api.github.com` |
| **GitLab** | `https://gitlab.com/user/repo.git` | `gitlab.com/api/v4` |
| **Gitverse** | `https://gitverse.io/user/repo.git` | Platform-specific |

**Error Handling:**

| Error | Cause | Solution |
|-------|-------|----------|
| `Repository not found` | Invalid URL or private repo without token | Verify URL, add GIT_TOKEN |
| `Permission denied` | Token lacks required scopes | Add `repo` scope to token |
| `Rate limit exceeded` | Too many API requests | Wait or use authenticated requests |
| `Clone failed` | Network issues or Git not installed | Check connectivity, install Git |

## 7.3 What LLM models are recommended? {: #recommended-models}

Model selection depends on your use case, budget, and quality requirements. Here are evidence-based recommendations.

**Model Recommendations by Task:**

Totally hear you—those model picks are dated now, and we can update them to current front‑runners. Below is a **newer, stronger recommendations table** using today’s top models across major providers, plus a note on preview vs. stable. I can drop this straight into your docs once you approve.

| Task | Recommended Model | Alternative | Budget Option |
|------|------------------|-------------|---------------|
| **README Generation** | GPT‑5.4 | Claude Sonnet 4 | GPT‑5‑mini |
| **Docstring Generation** | GPT‑5‑mini | Mistral Devstral 2 | Mistral Small 3.2 |
| **CI/CD Workflow** | GPT‑5‑mini | Gemini 2.5 Flash | Mistral Small 3.2 |
| **Code Analysis** | GPT‑5.4 | Claude Opus 4.1 | Gemini 2.5 Flash |
| **Research Paper README** | GPT‑5.4 | Claude Opus 4.1 | Gemini 2.5 Flash |
| **Full Repository** | GPT‑5.4 | Gemini 2.5 Pro | Claude Sonnet 4 |

**Notes**

- **GPT‑5.4** is the current OpenAI flagship for complex reasoning and coding; **GPT‑5‑mini** is the cost‑optimized option. ([developers.openai.com](https://developers.openai.com/api/docs/models))  
- **Claude Opus 4.1** and **Claude Sonnet 4** are Anthropic’s latest top‑tier models. ([docs.anthropic.com](https://docs.anthropic.com/en/docs/about-claude/models/all-models))  
- **Gemini 2.5 Pro / Flash** are Google’s current stable production models; **Gemini 3 Pro** exists but is still **preview**. ([ai.google.dev](https://ai.google.dev/models/gemini))  
- **Mistral Large 3 / Devstral 2 / Small 3.2** are the latest in Mistral’s lineup (Devstral is code‑focused). ([docs.mistral.ai](https://docs.mistral.ai/getting-started/models))  

## 7.4 How do I configure model parameters (temperature, top_p, max_tokens)? {: #model-parameters}

Model parameters control the behavior, creativity, and output length of LLM responses.

**Parameter Reference:**

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `--temperature` | Float | 0.0 - 2.0 | 0.05 | Controls randomness/creativity |
| `--top_p` | Float | 0.0 - 1.0 | 0.95 | Nucleus sampling probability |
| `--max_tokens` | Integer | 1 - model max | 4096 | Maximum output tokens |
| `--context_window` | Integer | 1 - model max | 16385 | Total input + output context |

## 7.5 Can I use different models for different tasks?

**Yes!** OSA supports task-specific model configuration for optimized performance and cost.

**Multi-Model Configuration:**

By default, OSA uses a single model for all tasks (`--use-single-model`). To use different models:

```bash
# Disable single model mode
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --model-docstring codellama:13b \
  --model-readme gpt-4o \
  --model-validation llama3.1:8b \
  --model-general gpt-4o
```

**TOML Configuration for Multi-Model:**

```toml
# config.toml
[general]
repository = "https://github.com/username/repo"
mode = "auto"

[llm]
use_single_model = false

[models]
docstring = "codellama:13b"
readme = "gpt-4o"
validation = "gpt-3.5-turbo"
general = "gpt-4o"
```

**Task-Specific Model Flags:**

| Flag | Purpose | Recommended Model |
|------|---------|-------------------|
| `--model-docstring` | Docstring generation | Codellama 13B, GPT-4o |
| `--model-readme` | README generation | GPT-4o, Claude 3.5 |
| `--model-validation` | Code validation | Llama 3.1 8B, GPT-3.5 |
| `--model-general` | General tasks | GPT-4o, ITMO Research |

**Why Use Different Models?**

| Benefit | Description | Example |
|---------|-------------|---------|
| **Cost Optimization** | Use cheaper models for simple tasks | GPT-3.5 for validation, GPT-4o for README |
| **Performance** | Faster models for quick tasks | Llama 3.1 8B for validation |
| **Quality** | Best model for critical tasks | GPT-4o for README and docs |
| **Specialization** | Code models for code tasks | Codellama for docstrings |

## 7.6 Where is the API documentation?

Comprehensive API documentation is available through multiple channels.

**Documentation Resources:**

| Resource | Type | Link |
|----------|------|------|
| **Main Documentation** | Full API reference | [aimclub.github.io/OSA](https://aimclub.github.io/OSA/) |
| **GitHub README** | Quick start, examples | [github.com/aimclub/OSA](https://github.com/aimclub/OSA) |
| **CLI Help** | Command-line reference | `python -m osa_tool.run --help` |
| **Workflow Generator** | CI/CD configuration | [osa_tool/workflow/README.md](https://github.com/aimclub/OSA/tree/main/osa_tool/workflow) |
| **Scheduler/CLI** | Interactive mode guide | [osa_tool/scheduler/README.md](https://github.com/aimclub/OSA/tree/main/osa_tool/scheduler) |
| **Examples** | Generated outputs | [github.com/aimclub/OSA/examples](https://github.com/aimclub/OSA/tree/main/examples) |
