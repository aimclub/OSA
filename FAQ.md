# FAQ {#faq}

> **Last Updated:** March 2026  
> **Version:** OSA 1.x  
> **Repository:** [github.com/aimclub/OSA](https://github.com/aimclub/OSA)

---

## Quick Navigation {#quick-navigation}

| Section | Topic | Jump To |
|---------|-------|---------|
| [1️⃣](#general-questions) | General Questions | [What is OSA?](#what-is-osa) |
| [2️⃣](#installation-setup) | Installation & Setup | [System Requirements](#system-requirements) |
| [3️⃣](#configuration-api-keys) | Configuration & API Keys | [Required Tokens](#required-tokens) |
| [4️⃣](#usage-features) | Usage & Features | [How to Run OSA](#how-to-run-osa) |
| [5️⃣](#troubleshooting) | Troubleshooting | [API Auth Fails](#api-auth-fails) |
| [6️⃣](#contributing-community) | Contributing & Community | [How to Contribute](#how-to-contribute) |
| [7️⃣](#technical-details) | Technical Details | [Technology Stack](#technology-stack) |

---

## ⚡ Quick Start: Top 10 Questions {#quick-start}

1. [What is OSA?](#what-is-osa)
2. [How do I install OSA?](#how-do-i-install-osa)
3. [What tokens do I need?](#required-tokens)
4. [How do I run OSA?](#how-to-run-osa)
5. [How does README generation work?](#readme-generation)
6. [What if API auth fails?](#api-auth-fails)
7. [How do I report a bug?](#report-bug)
8. [How can I contribute?](#how-to-contribute)
9. [How do I cite OSA?](#how-do-i-cite-osa-in-my-research)
10. [What LLM model should I use?](#llm-models)

---

## Section 1: General Questions {#general-questions}

Welcome to the OSA (Open-Source Advisor) FAQ! This section covers the most common questions about what OSA is, who it's for, and how to get started.

### 1.1 What is OSA (Open-Source Advisor)? {#what-is-osa}

OSA (Open-Source Advisor) is an **LLM-based multi-agent tool** designed to automatically improve open-source repositories and make them easier to understand, run, and reuse.

**What OSA does:**

| Feature | Description |
|---------|-------------|
| 📄 **README Generation** | Creates clear, structured README files (standard or article-style for research papers) |
| 📚 **Documentation** | Generates docstrings for Python code and builds web documentation with MkDocs |
| 🔧 **CI/CD Setup** | Automates workflow creation for testing, code quality, and deployment |
| 📊 **Repository Analysis** | Provides actionable reports on project strengths and weaknesses |
| 🤖 **Automated PRs** | Creates pull requests with all proposed improvements |
| 📋 **Community Files** | Adds contribution guidelines, Code of Conduct, issue/PR templates |

OSA was originally developed for **researchers** (biologists, chemists, etc.) who lack software engineering experience but need to share reproducible code with their publications. However, it works on **any repository**, not just scientific ones.

### 1.2 Who should use OSA? {#who-should-use-osa}

OSA is designed for multiple audiences:

| Target Audience | Primary Use Case |
|-----------------|------------------|
| **Researchers & Scientists** | Make research code reproducible and publication-ready with minimal effort |
| **Academic Labs** | Standardize documentation across multiple research repositories |
| **Open-Source Developers** | Save time on documentation and CI/CD setup for personal or team projects |
| **Students** | Learn best practices for open-source project maintenance |
| **Organizations** | Improve quality and security scores across dozens of repositories |

**Ideal scenarios:**

- ✅ You have a repository linked to a research paper but no README
- ✅ Your code lacks docstrings and documentation
- ✅ You need CI/CD pipelines but don't know where to start
- ✅ You maintain multiple repositories and need consistent quality
- ✅ You want to improve your repository's security scorecard rating

### 1.3 What problems does OSA solve? {#problems-osa-solves}

OSA addresses critical challenges in open-source project maintenance:

#### **Scientific Open-Source Challenges:**

| Problem | Impact | OSA Solution |
|---------|--------|--------------|
| ❌ Code shared without README | Others can't understand or use it | ✅ Auto-generates structured README |
| ❌ No documentation/docstrings | Code is unreadable | ✅ Generates comprehensive docstrings |
| ❌ Missing CI/CD pipelines | No automated testing or quality checks | ✅ Creates customizable workflows |
| ❌ No license file | Legal uncertainty for users | ✅ Adds appropriate license |
| ❌ Poor repository structure | Confusing navigation | ✅ Reorganizes tests/examples folders |
| ❌ Low security scorecard rating | Reduced trust and adoption | ✅ Improves score from ~2.2 to ~3.7+ |

#### **General Developer Challenges:**

| Problem | OSA Solution |
|---------|--------------|
| ❌ Procrastinating on documentation | ✅ Automates it in minutes |
| ❌ Maintaining dozens of repos | ✅ Standardizes across all projects |
| ❌ Missing contribution guidelines | ✅ Generates community files |
| ❌ No time for best practices | ✅ Implements them automatically |

**Key Advantage:** Unlike tools that focus on individual components (e.g., Readme-AI only generates README, RepoAgent only generates code docs), **OSA considers the repository holistically** to make it easier to understand and ready to run.

### 1.4  Is OSA free to use? {#osa-free}

**Yes!** OSA is completely **free and open-source** software.

| Aspect | Details |
|--------|---------|
| **License** | BSD 3-Clause "New" or "Revised" License |
| **Cost** | Free for personal and commercial use |
| **Modification** | You can modify and redistribute |
| **LLM Costs** | ⚠️ Some providers (OpenAI, etc.) charge for API usage |
| **Free Options** | ✅ ITMO-hosted models, Ollama (local), OpenRouter (free tier) |

**What's included at no cost:**

- ✅ Full OSA tool functionality
- ✅ All features (README, docs, CI/CD, reports)
- ✅ Community support via Telegram
- ✅ Regular updates and improvements

### 1.5 What license does OSA use? {#osa-license}

OSA is protected under the **BSD 3-Clause "New" or "Revised" License**.

**Permissions:**

| ✅ Allowed |
|-----------|
| Commercial use |
| Modification |
| Distribution |
| Private use |
| Sublicensing |

**Conditions:**

| ⚠️ Required |
|------------|
| Include original copyright notice |
| Include license text |
| No endorsement using contributor names |

**No restrictions on:**

- Using OSA for commercial projects
- Modifying the source code
- Distributing your modifications

For full details, see the [LICENSE file](https://github.com/aimclub/OSA/blob/main/LICENSE).

### 1.6 Who developed OSA? {#who-developed-osa}

OSA was developed by researchers and developers at **ITMO University** (Saint Petersburg, Russia) as part of the **AI Initiative Research Project (RPAII)**.
Core Authors:

- Nikolay Nikitin
- Andrey Getmanov
- Zakhar Popov
- EkaterinaUlyanova
- Ilya Sokolov

The project is tested and supported by the [ITMO OpenSource community](https://t.me/scientific_opensource).

### 1.7 Where can I find publications about OSA? {#publications-about-osa}

OSA has been published and presented at several venues:

| Language   | Publication                                                              | Link                                                                                                                             |
|------------|--------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| 🇬🇧 English | Automate Your Coding with OSA – ITMO-Made AI Assistant for Researchers   | [ITMO News](https://news.itmo.ru/en/news/14282)                                                                                  |
| 🇬🇧 English | An LLM-Powered Tool for Enhancing Scientific Open-Source Repositories    | [ICML 2025 Workshop]()                                                                                                           |
| 🇬🇧 English | An End-to-End Guide to Beautifying Your Open-Source Repo with Agentic AI | [Towards Data Science](https://towardsdatascience.com/an-end-to-end-guide-to-beautifying-your-open-source-repo-with-agentic-ai/) |
| 🇷🇺 Russian | OSA: ИИ-помощник для разработчиков научного open source кода             | [Habr](https://habr.com/ru/companies/spbifmo/articles/906018)                                                                    |

For citation formats, see [How do I cite OSA in my research?](#how-do-i-cite-osa-in-my-research)

### 1.8 What is the OSA community and how do I join? {#osa-community}

The OSA community consists of developers, researchers, and users who contribute to and support the project.

**Ways to Connect:**

| Platform | Purpose | Link |
|----------|---------|------|
| 💬 **Telegram Chat** | Ask questions, get help, share news | [@OSA_helpdesk](https://t.me/OSA_helpdesk) |
| 🐙 **GitHub Repository** | Report issues, contribute code, view PRs | [github.com/aimclub/OSA](https://github.com/aimclub/OSA) |
| 📚 **Documentation** | Learn about API, features, and usage | [aimclub.github.io/OSA](https://aimclub.github.io/OSA/) |
| 🌐 **Open-source-ops** | Related tools, content, and best practices | [github.com/aimclub/open-source-ops](https://github.com/aimclub/open-source-ops) |
| 🎬 **Video Demo** | Watch OSA in action | [YouTube](https://www.youtube.com/watch?v=LDSb7JJgKoY) |

**Community Benefits:**

- 🆘 Get help from developers directly
- 📢 Stay updated on new features
- 🤝 Connect with other OSA users
- 💡 Share your use cases and improvements

### 1.9 What languages and platforms does OSA support?

OSA's current support matrix:

| Feature | Support Level | Details |
|---------|---------------|---------|
| **Code Documentation** | 🐍 Python | Docstrings for functions, methods, classes, modules |
| **README Generation** | 🌍 Any | Text-based, works with any project type |
| **CI/CD Workflows** | 🐍 Python | Tests, formatting, PEP8, PyPI publication |
| **Repository Platforms** | ✅ GitHub, GitLab, Gitverse | Cloud and self-hosted instances |
| **Interface Languages** | 🇬🇧 English, 🇷🇺 Russian | Documentation and CLI |
| **LLM Providers** | ✅ Multiple | OpenAI, Ollama, OpenRouter, VseGPT, Gigachat, ITMO |

**Future Plans:**

| Coming Soon | Description |
|-------------|-------------|
| 🔄 **RAG System** | Compare repos with best-practice references |
| 🌐 **Multi-Language** | Support for JavaScript, Java, etc. |
| 🤖 **Conversational Mode** | Natural language improvement requests |
| 📈 **Smart Detection** | Skip already-high-quality components |

---
*[↑ Back to Section 1](#general-questions)*  

*[↑ Top](#quick-navigation)*

## Section 2: Installation & Setup {#installation-setup}

Welcome to Section 2 of the OSA FAQ! This section covers everything you need to know about installing and setting up OSA on your system.

### 2.1 What are the system requirements? {#system-requirements}

OSA has minimal system requirements and runs on most modern systems.

| Requirement | Specification | Notes |
|-------------|---------------|-------|
| **Python Version** | 🐍 Python 3.11 or higher | Required for all installation methods |
| **Operating System** | 🖥️ Linux, macOS, Windows | All major platforms supported |
| **Memory (RAM)** | 💾 4 GB minimum, 8 GB recommended | More RAM needed for local LLM models |
| **Storage** | 💿 1 GB free space | For installation + temporary repository cloning |
| **Internet Connection** | 🌐 Required | For API-based LLM providers and repository access |
| **Git** | 🔧 Git installed | Required for repository cloning and PR creation |

**Optional Requirements:**

| Component | Purpose | When Needed |
|-----------|---------|-------------|
| **Docker** | Containerized deployment | If using Docker installation method |
| **GPU** | Local LLM inference | Only if running local models (Ollama, etc.) |

**Platform-Specific Notes:**

| Platform | Considerations |
|----------|----------------|
| **Linux** | ✅ Best supported, recommended for production |
| **macOS** | ✅ Fully supported, works with Apple Silicon |
| **Windows** | ✅ Supported, use PowerShell or WSL for best experience |
| **WSL2** | ✅ Recommended for Windows users |

### 2.2 How do I install OSA? {#how-do-i-install-osa}

OSA can be installed in several ways depending on your needs. Here's the quick start:

**Recommended for Most Users:**

```bash
pip install osa_tool
```

**Complete Installation Steps:**

| Step | Action | Command |
|------|--------|---------|
| 1️⃣ | Check Python version | `python --version` (must be 3.11+) |
| 2️⃣ | Install OSA | `pip install osa_tool` |
| 3️⃣ | Create .env file | Store API keys and tokens |
| 4️⃣ | Set environment variables | `export OPENAI_API_KEY=your_key` |
| 5️⃣ | Verify installation | `python -m osa_tool.run --help` |
| 6️⃣ | Run OSA | `python -m osa_tool.run -r <repository_url>` |

**Quick Verification:**

```bash
# Check if OSA is installed correctly
python -c "import osa_tool; print(osa_tool.__version__)"
```

### 2.3 What installation methods are available? {#installation-methods}

OSA supports multiple installation methods to fit different use cases:

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **📦 PyPI (pip)** | Most users, quick setup | ✅ Easy, fast, auto-dependencies | ⚠️ Less customization |
| **🔧 Source Build** | Developers, contributors | ✅ Full control, latest features | ⚠️ Manual dependency management |
| **🐳 Docker** | Production, consistent environments | ✅ Isolated, reproducible | ⚠️ Larger footprint, Docker knowledge needed |
| **🌐 Web GUI** | Non-technical users | ✅ No installation required | ⚠️ Limited to ITMO-hosted instance |

### 2.4 How do I install using pip? {#install-using-pip}

Installing via PyPI is the recommended method for most users.

**Step-by-Step Instructions:**

```bash
# Step 1: Ensure you have Python 3.11+
python --version

# Step 2: (Optional) Create a virtual environment
python -m venv osa_env
source osa_env/bin/activate  # Linux/macOS
# OR
osa_env\Scripts\activate     # Windows

# Step 3: Install OSA from PyPI
pip install osa_tool

# Step 4: Verify installation
python -m osa_tool.run --help
```

**Upgrade to Latest Version:**

```bash
pip install --upgrade osa_tool
```

**Check Installed Version:**

```bash
pip show osa_tool
```

**Uninstall OSA:**

```bash
pip uninstall osa_tool
```

### 2.5 How do I build from source? {#build-from-source}

Building from source is recommended for developers who want to contribute or use the latest features.

**Complete Steps:**

```bash
# Step 1: Clone the OSA repository
git clone https://github.com/aimclub/OSA
cd OSA

# Step 2: Choose your dependency manager

# Option A: Using pip
pip install -r requirements.txt

# Option B: Using poetry (recommended for development)
poetry install

# Step 3: Verify installation
python -m osa_tool.run --help
```

**Development Setup:**

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests to verify setup
pytest tests/

# Check code quality
black osa_tool/ --check
```

**Contributing Workflow:**

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ...

# Run tests before committing
pytest tests/

# Commit and push
git add .
git commit -m "Add your feature"
git push origin feature/your-feature-name
```

### 2.6 How do I use OSA with Docker? {#use-osa-docker}

Docker provides a consistent, isolated environment for running OSA.

**Prerequisites:**

- Docker installed and running
- Git token and API keys ready

**Step-by-Step Docker Setup:**

```bash
# Step 1: Clone the repository (if not already done)
git clone https://github.com/aimclub/OSA
cd OSA

# Step 2: Build the Docker image
docker build \
  --build-arg GIT_USER_NAME="your-user-name" \
  --build-arg GIT_USER_EMAIL="your-user-email" \
  -f docker/Dockerfile \
  -t osa_tool:latest \
  .

# Step 3: Create .env file with your credentials
# See Section 3 for .env file format

# Step 4: Run OSA with Docker
docker run \
  --env-file .env \
  osa_tool:latest \
  -r https://github.com/username/repository
```

**Docker Run Options:**

| Option | Description | Example |
|--------|-------------|---------|
| `--env-file` | Load environment variables | `--env-file .env` |
| `-v` | Mount volumes for file access | `-v ./papers:/app/papers` |
| `--rm` | Remove container after exit | `--rm` |
| `-it` | Interactive mode | `-it` |

**Complete Docker Command with All Options:**

```bash
docker run --rm -it \
  --env-file .env \
  -v $(pwd)/papers:/app/OSA/papers \
  osa_tool:latest \
  -r https://github.com/username/repo \
  --api openai \
  --model gpt-4 \
  --attachment /app/OSA/papers/paper.pdf
```

**Docker Compose (Optional):**

```yaml
# docker-compose.yml
version: '3.8'
services:
  osa:
    build:
      context: .
      dockerfile: docker/Dockerfile
      args:
        GIT_USER_NAME: "your-user-name"
        GIT_USER_EMAIL: "your-user-email"
    env_file:
      - .env
    volumes:
      - ./papers:/app/OSA/papers
    command: ["-r", "https://github.com/username/repo"]
```

```bash
# Run with Docker Compose
docker-compose up --rm osa
```

---
*[↑ Back to Section 2](#installation-setup)*  

*[↑ Top](#quick-navigation)*

## Section 3: Configuration & API Keys {#configuration-api-keys}

Welcome to Section 3 of the OSA FAQ! This section covers everything you need to know about configuring OSA, setting up API keys, and managing tokens for seamless operation.

### 3.1 What tokens/API keys do I need? {#required-tokens}

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

### 3.2 How do I set up OPENAI_API_KEY? {#setup-openai-api-key}

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

### 3.3 How do I set up GIT_TOKEN? {#setup-git-token}

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

### 3.4 Which LLM providers are supported? {#llm-providers}

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

### 3.5 How do I configure different LLM providers? {#configure-llm-providers}

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

**ITMO Hosted Model:**

```bash
# Option 1: Via .env file
echo "ITMO_MODEL_URL=https://osa.nsslab.onti.actcognitive.org/api/v1" >> .env

# Option 2: Via command line
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --base-url https://osa.nsslab.onti.actcognitive.org/api/v1
# No API key needed for public ITMO endpoint
```

### 3.6 Can I use local LLM models? {#local-llm-models}

**Yes!** OSA fully supports local LLM models via Ollama or self-hosted OpenAI-compatible servers.

### 3.7 How do I use the ITMO hosted model? {#itmo-hosted-model}

ITMO University provides a hosted OSA endpoint for research and testing purposes.

**Access Options:**

| Option | Description | How to Use |
|--------|-------------|------------|
| **Public Web GUI** | No installation, browser-based | Visit [osa.nsslab.onti.actcognitive.org](https://osa.nsslab.onti.actcognitive.org/) |
| **API Access** | CLI usage with ITMO endpoint | Set `--base-url` to ITMO API endpoint |
| **Community Access** | For ITMO students/researchers | Contact ITMO OpenSource team for credentials |

**Using ITMO Model via CLI:**

```bash
# Method 1: Direct base-url parameter
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --base-url https://osa.nsslab.onti.actcognitive.org/api/v1

# Method 2: Via .env file
echo "ITMO_MODEL_URL=https://osa.nsslab.onti.actcognitive.org/api/v1" >> .env
python -m osa_tool.run -r https://github.com/username/repo
```

### 3.8 What configuration options are available? {#configuration-options}

OSA offers extensive CLI configuration options. For the complete reference visit the [README.md](https://github.com/aimclub/OSA/blob/main/osa_tool/scheduler/README.md).

### 3.9 How do I use custom TOML configuration? {#custom-toml-config}

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

---
*[↑ Back to Section 3](#configuration-api-keys)*  

*[↑ Top](#quick-navigation)*

## Section 4: Usage & Features {#usage-features}

Welcome to Section 4 of the OSA FAQ! This section covers everything you need to know about running OSA, understanding its features, and maximizing its capabilities for your repository improvement workflow.

### 4.1 How do I run OSA? {#how-to-run-osa}

Running OSA is straightforward once you have it installed and configured. Here's the complete workflow:

**Basic Run (Minimum Required):**

```bash
# Set your environment variables first
export GIT_TOKEN="ghp_..."
export OPENAI_API_KEY="sk-..."  # If using OpenAI

# Run OSA with repository URL
python -m osa_tool.run -r https://github.com/username/repository
```

**Running with Docker:**

```bash
docker run --env-file .env osa_tool:latest \
  -r https://github.com/username/repository
```

### 4.2 What command-line arguments are available?

OSA provides extensive CLI arguments for customization. Here's the complete reference:

**Required Arguments:**

| Flag | Description | Example | Mandatory |
|------|-------------|---------|-----------|
| `-r, --repository` | URL of GitHub/GitLab/Gitverse repository | `-r https://github.com/aimclub/OSA` | ✅ Yes |

**Core Configuration:**

| Flag | Description | Default | Example |
|------|-------------|---------|---------|
| `-b, --branch` | Target branch name | Default branch | `-b develop` |
| `-o, --output` | Output directory path | Current directory | `-o ./results` |
| `-m, --mode` | Operation mode | `auto` | `--mode basic` |
| `--config-file` | Path to TOML configuration | None | `--config-file config.toml` |

**LLM Configuration:**

| Flag | Description | Default | Example |
|------|-------------|---------|---------|
| `--api` | LLM provider | `openai` | `--api ollama` |
| `--base-url` | API endpoint URL | `https://openrouter.ai/api/v1` | `--base-url http://localhost:11434` |
| `--model` | LLM model name | `gpt-3.5-turbo` | `--model llama3.2:3b` |
| `--temperature` | Sampling temperature (0-1) | `0.05` | `--temperature 0.3` |
| `--top_p` | Nucleus sampling probability | `0.95` | `--top_p 0.9` |
| `--max_tokens` | Max output tokens | `4096` | `--max_tokens 2048` |
| `--context_window` | Total context window | `16385` | `--context_window 8192` |

**Task-Specific Models** (when `--use-single-model=false`):

| Flag | Purpose | Example |
|------|---------|---------|
| `--model-docstring` | Model for docstring generation | `--model-docstring codellama:13b` |
| `--model-readme` | Model for README generation | `--model-readme gpt-4o` |
| `--model-validation` | Model for code validation | `--model-validation llama3.1:8b` |
| `--model-general` | Model for general tasks | `--model-general gemma3:27b` |

**Repository Interaction:**

| Flag | Description | Default | Example |
|------|-------------|---------|---------|
| `--no-fork` | Skip creating fork | `False` | `--no-fork` |
| `--no-pull-request` | Skip creating PR | `False` | `--no-pull-request` |
| `--delete-dir` | Delete cloned repo after processing | `disabled` | `--delete-dir` |

**Special Features:**

| Flag | Description | Example |
|------|-------------|---------|
| `--attachment` | Path/URL to PDF/.docx paper | `--attachment ./paper.pdf` |
| `--convert-notebooks` | Convert Jupyter notebooks | `--convert-notebooks ./notebooks/` |
| `--generate-workflows` | Generate CI/CD pipelines | `--generate-workflows` |

**Help:**

```bash
# View all available arguments
python -m osa_tool.run --help
```

### 4.3 How does README generation work? {#readme-generation}

OSA's README generation is one of its core features, creating comprehensive documentation automatically.

**README Sections Generated:**

| Section | Content | Auto-Generated |
|---------|---------|----------------|
| **Project Title** | Repository name + description | ✅ |
| **Badges** | Build status, license, version, etc. | ✅ |
| **Overview** | Project purpose and goals | ✅ |
| **Core Features** | Key functionality list | ✅ |
| **Installation** | Step-by-step setup instructions | ✅ |
| **Quick Start** | Basic usage examples | ✅ |
| **Documentation** | Links to docs, API reference | ✅ |
| **Examples** | Code snippets and demos | ✅ |
| **Contributing** | How to contribute guidelines | ✅ |
| **License** | License information | ✅ |
| **Acknowledgments** | Credits and citations | ✅ |

**Standard vs Article-Style README:**

| Feature | Standard README | Article-Style README |
|---------|-----------------|---------------------|
| **Trigger** | Default | `--attachment <paper>` |
| **Overview** | Project-focused | Research paper-focused |
| **Content Section** | Features list | Paper methodology |
| **Algorithms** | Optional | Detailed explanation |
| **Citations** | Optional | Required |
| **Best For** | General projects | Research publications |

### 4.4 How does documentation generation work?

OSA generates comprehensive code documentation through a sophisticated multi-stage pipeline.

**What Gets Documented:**

| Component | Documentation Generated |
|-----------|------------------------|
| **Modules** | File-level descriptions, purpose, exports |
| **Classes** | Class purpose, attributes, methods overview |
| **Methods** | Parameters, return values, behavior, exceptions |
| **Functions** | Purpose, arguments, returns, examples |
| **Imports** | Dependency relationships mapped |

**Documentation Output Locations:**

```
project/
├── docs/
│   ├── index.md           # Main documentation page
│   ├── api/               # API reference
│   │   ├── module1.md
│   │   └── module2.md
│   └── examples.md        # Usage examples
├── mkdocs.yml             # MkDocs configuration
└── .github/workflows/
    └── docs-deploy.yml    # Auto-deployment workflow
```

### 4.5 How does CI/CD workflow generation work?

OSA automatically creates CI/CD pipelines tailored to your repository platform and needs.

**Generated Workflow Components:**

| Component | Purpose | Tools Used |
|-----------|---------|------------|
| **Unit Tests** | Run automated tests | pytest, unittest |
| **Code Formatting** | Ensure consistent style | Black, autopep8 |
| **Linting** | Check code quality | flake8, PEP8 |
| **Type Checking** | Validate type hints | mypy, pyright |
| **Documentation** | Build and deploy docs | MkDocs, Sphinx |
| **Package Publish** | Upload to PyPI | twine, poetry |
| **Code Coverage** | Track test coverage | coverage.py, Codecov |

**Workflow Customization Options:**

| Flag | Description | Example |
|------|-------------|---------|
| `--use-poetry` | Enable Poetry dependency management | `--use-poetry` |
| `--branches` | Specify trigger branches | `--branches main,develop` |
| `--codecov-token` | Codecov integration token | `--codecov-token <token>` |
| `--include-codecov` | Enable coverage reporting | `--include-codecov` |

**Repository Structure After CI/CD Setup:**

```
repository/
├── .github/
│   └── workflows/
│       ├── ci.yml           # Main CI pipeline
│       ├── docs-deploy.yml  # Documentation deployment
│       └── publish.yml      # PyPI publication
├── tests/                   # Standardized test directory
│   ├── __init__.py
│   └── test_main.py
├── examples/                # Standardized examples directory
│   ├── basic_usage.py
│   └── advanced_demo.py
└── .gitlab-ci.yml           # GitLab alternative
```

### 4.6 Can OSA work with research paper-based projects?

**Yes!** This is one of OSA's unique strengths. It was originally designed specifically for research repositories.

**Research Project Support:**

| Feature | Description | Benefit |
|---------|-------------|---------|
| **Article-Style README** | README generated from paper content | Connects code to research |
| **PDF Attachment** | Upload paper PDF for context | Accurate methodology documentation |
| **Algorithm Section** | Explains implemented methods | Reproduces research claims |
| **Citation Integration** | Auto-generates citation section | Proper academic attribution |
| **Reproducibility Focus** | Emphasizes setup and usage | Enables result verification |

**Why Research Projects Need OSA:**

| Common Problem | OSA Solution |
|----------------|--------------|
| ❌ Code shared without README | ✅ Auto-generated article-style README |
| ❌ No connection to paper | ✅ Paper content integrated into docs |
| ❌ Missing implementation details | ✅ Algorithm section from paper |
| ❌ No reproducibility instructions | ✅ Clear setup and usage guide |
| ❌ Missing license | ✅ Appropriate license added |
| ❌ No CI/CD for validation | ✅ Automated testing workflows |

**Research Repository Example:**

Before OSA:

```
research-code/
├── main.py          # No docstrings
├── utils.py         # No documentation
└── results/         # No README
```

After OSA:

```
research-code/
├── README.md        # Article-style with paper summary
├── main.py          # Full docstrings
├── utils.py         # Full docstrings
├── docs/            # MkDocs documentation
├── tests/           # Automated tests
├── examples/        # Usage examples
├── LICENSE          # License file
├── CITATION.cff     # Citation file
└── .github/workflows/
    └── ci.yml       # CI/CD pipeline
```

**Paper Integration Workflow:**

```
1. Upload paper PDF → 2. OSA extracts key information → 
3. Generates article-style README → 4. Links code to methodology →
5. Creates reproducibility guide → 6. Adds citation information
```

### 4.7 How do I use the `--attachment` option for papers?

The `--attachment` option enables article-style README generation based on research papers.

**Supported Formats:**

| Format | Local Path | URL | Notes |
|--------|-----------|-----|-------|
| **PDF** | `./paper.pdf` | `https://.../paper.pdf` | ✅ Fully supported |
| **DOCX** | `./paper.docx` | — | ⚠️ Limited support |
| **LaTeX** | `./paper.tex` | — | ⚠️ Limited support |

**Using Local Files:**

```bash
# Standard local file
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --attachment ./papers/research_paper.pdf

# With absolute path
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --attachment /home/user/papers/paper.pdf
```

**Using URLs:**

```bash
# Direct PDF URL
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --attachment https://arxiv.org/pdf/2401.12345.pdf

# Research gate, ACM, IEEE links (if publicly accessible)
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --attachment https://dl.acm.org/doi/pdf/10.1145/xxxxxxx
```

**Using with Docker:**

```bash
# Method 1: Copy file into image before building
cp paper.pdf ./docker/papers/
docker build -t osa_tool .
docker run --env-file .env osa_tool:latest \
  -r https://github.com/username/repo \
  --attachment /app/OSA/papers/paper.pdf

# Method 2: Volume mounting (recommended)
docker run --env-file .env \
  -v $(pwd)/papers:/app/OSA/papers \
  osa_tool:latest \
  -r https://github.com/username/repo \
  --attachment /app/OSA/papers/paper.pdf
```

### 4.8 What are the different operation modes (basic/auto/advanced)?

OSA offers three modes to fit different needs:

| Mode | Description | Best For |
|------|-------------|----------|
| **🟢 Basic** | Predefined improvements: README, report, community files, tests/examples folders | Quick standard improvements |
| **🔵 Auto (Default)** | LLM analyzes repo and creates customized improvement plan for approval | Most users, balanced approach |
| **🟠 Advanced** | Full manual control over every step and configuration | Power users, specific requirements |

```bash
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --mode advanced
```

**Experimental Features:**

| Feature | Status | Description |
|---------|--------|-------------|
| **Conversational Mode** | 🚧 Under Development | Natural language requests via CLI |
| **Multi-Agent System** | 🚧 Under Development | Specialized agents for different tasks |

### 4.9 Does OSA create pull requests automatically?

**Yes!** By default, OSA automatically creates pull requests with all proposed changes.

### 4.10 Can I prevent OSA from creating forks/PRs?

**Yes!** You can run OSA in read-only mode without creating forks or pull requests.

**Options to Disable Automatic Changes:**

| Flag | Effect | Use Case |
|------|--------|----------|
| `--no-fork` | Skip fork creation | Read-only analysis of public repos |
| `--no-pull-request` | Skip PR creation | Review changes locally first |
| Both flags | Local changes only | Full control over what gets pushed |

**Read-Only Mode:**

```bash
# Analyze without any remote repository modifications
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --no-fork \
  --no-pull-request
```

### 4.11 Which repository platforms are supported?

OSA supports multiple repository hosting platforms.

**Supported Platforms:**

| Platform | Support Level | Features | Token Type |
|----------|---------------|----------|------------|
| **GitHub** | ✅ Full | All features | `GITHUB_TOKEN` / `GIT_TOKEN` |
| **GitLab.com** | ✅ Full | All features | `GITLAB_TOKEN` / `GIT_TOKEN` |
| **GitLab Self-Hosted** | ✅ Full | All features | `GITLAB_TOKEN` / `GIT_TOKEN` |
| **Gitverse** | ✅ Full | All features | `GITVERSE_TOKEN` / `GIT_TOKEN` |

**CI/CD Platform Differences:**

| Feature | GitHub | GitLab | Gitverse |
|---------|--------|--------|----------|
| **Workflow Location** | `.github/workflows/` | `.gitlab-ci.yml` | Platform-specific |
| **Workflow Format** | YAML (Actions) | YAML (CI/CD) | YAML |
| **PR Terminology** | Pull Request | Merge Request | Pull Request |
| **Branch Protection** | Supported | Supported | Supported |
| **Pages Deployment** | GitHub Pages | GitLab Pages | Platform Pages |

**Platform Detection:**

OSA automatically detects the platform from the repository URL:

| URL Pattern | Detected Platform |
|-------------|-------------------|
| `github.com/*` | GitHub |
| `gitlab.com/*` | GitLab |
| `gitlab.*/*` | GitLab (self-hosted) |
| `gitverse.io/*` | Gitverse |

**Token Permissions by Platform:**

| Platform | Required Scopes |
|----------|-----------------|
| **GitHub** | `repo`, `workflow` |
| **GitLab** | `api`, `write_repository` |
| **Gitverse** | `repo`, `write` |

### 4.12 Can I process Jupyter notebooks?

**Yes!** OSA can convert Jupyter notebooks to Python scripts for processing.

**Using Notebook Conversion:**

```bash
# Convert specific notebooks
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --convert-notebooks ./notebooks/tutorial.ipynb

# Convert all notebooks in directory
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --convert-notebooks ./notebooks/

# Multiple notebook paths
python -m osa_tool.run \
  -r https://github.com/username/repo \
  --convert-notebooks ./notebooks/*.ipynb
```

---
*[↑ Back to Section 4](#usage-features)*  

*[↑ Top](#quick-navigation)*

## Section 5: Troubleshooting {#troubleshooting}

Welcome to Section 5 of the OSA FAQ! This section covers common issues, errors, and solutions to help you resolve problems quickly and get back to improving your repositories.

### 5.1 What do I do if API key authentication fails? {#api-auth-fails}

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

### 5.2 Why can't OSA access my repository?

Repository access issues typically stem from token permissions, URL format, or network problems.

**Common Access Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| `404 Not Found` | Wrong URL or private repo without token | Verify URL, add GIT_TOKEN |
| `403 Forbidden` | Token lacks permissions | Add `repo` scope to token |
| `Authentication failed` | Invalid/expired token | Regenerate Git token |
| `Repository not found` | Typo in URL or repo deleted | Double-check repository URL |
| `Connection refused` | Network/firewall blocking | Check proxy, firewall settings |

### 5.3 What if I get permission errors with Git?

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

### 5.4 How do I fix Docker-related issues?

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

### 5.5 What if the LLM response is too long/short?

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

### 5.6 How do I adjust temperature and sampling parameters?

Temperature and sampling parameters control the creativity and determinism of LLM outputs.

**Parameter Overview:**

See [Model Parameters](#model-parameters) for details.

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

### 5.7 Where do I report bugs? {#report-bug}

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

### Problem Statement
[What problem does this solve?]

### Proposed Solution
[How should it work?]

### Use Cases
[Who would benefit from this?]

### Alternatives Considered
[What other solutions did you consider?]

### Additional Context
[Any other relevant information]
```

---
*[↑ Back to Section 5](#troubleshooting)*  

*[↑ Top](#quick-navigation)*

## Section 6: Contributing & Community {#contributing-community}

Welcome to Section 6 of the OSA FAQ! This section covers everything you need to know about contributing to OSA, engaging with the community, getting help, and properly citing the project in your work.

### 6.1 How can I contribute to OSA? {#how-to-contribute}

OSA welcomes contributions from developers, researchers, documentation writers, and users of all skill levels. Here's how you can get involved:

**Ways to Contribute:**

| Contribution Type | Description | Skill Level | Time Commitment |
|-------------------|-------------|-------------|-----------------|
| **🐛 Bug Reports** | Report issues you encounter | Beginner | 10-30 min |
| **💡 Feature Ideas** | Suggest improvements or new features | Beginner | 15-45 min |
| **📝 Documentation** | Improve README, FAQ, API docs | Beginner-Intermediate | 1-4 hours |
| **🧪 Testing** | Test new releases, verify fixes | Beginner | 30 min - 2 hours |
| **🔧 Code Contributions** | Fix bugs, implement features | Intermediate-Advanced | 2-20+ hours |
| **🌍 Translation** | Localize documentation and UI | Intermediate | 2-10 hours |
| **📚 Examples** | Create tutorial repos, use cases | Intermediate | 1-5 hours |
| **🎨 Design** | Improve UI, logos, visuals | Intermediate | 2-8 hours |

**Getting Started with Code Contributions:**

```bash
# Step 1: Fork the repository
# Visit https://github.com/aimclub/OSA and click "Fork"

# Step 2: Clone your fork
git clone https://github.com/YOUR_USERNAME/OSA
cd OSA

# Step 3: Set up development environment
python -m venv osa-dev
source osa-dev/bin/activate  # Linux/macOS
# OR
osa-dev\Scripts\activate     # Windows

# Step 4: Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Step 5: Create a feature branch
git checkout -b feature/your-feature-name

# Step 6: Make your changes
# ... edit code, add tests, update docs ...

# Step 7: Run tests and checks
pytest tests/
black osa_tool/ --check

# Step 8: Commit and push
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name

# Step 9: Open a Pull Request
# Visit your fork on GitHub and click "New Pull Request"
```

**Contribution Guidelines:**

| Guideline | Details |
|-----------|---------|
| **Code Style** | Follow PEP 8, use Black for formatting |
| **Type Hints** | Add type annotations to new functions |
| **Docstrings** | Use Google-style docstrings for all public APIs |
| **Tests** | Add tests for new features, ensure existing tests pass |
| **Commits** | Use conventional commits: `feat:`, `fix:`, `docs:`, `chore:` |
| **PR Description** | Explain what changed, why, and how to test |
| **Review Process** | Be responsive to feedback, iterate on changes |

**Code of Conduct:**

OSA follows a community-focused Code of Conduct:

✅ **We encourage:**

- Respectful, inclusive communication
- Constructive feedback and collaboration
- Patience with newcomers and diverse perspectives
- Focus on technical merit, not personal attributes

❌ **We don't tolerate:**

- Harassment, discrimination, or offensive language
- Spam, trolling, or disruptive behavior
- Plagiarism or misrepresentation of contributions

Report concerns to: [OSA_helpdesk Telegram](https://t.me/OSA_helpdesk) or project maintainers.

### 6.2 How do I report issues or request features?

Use GitHub Issues for structured bug reports and feature requests.

**Reporting a Bug:**

1. **Search first**: Check if the issue already exists at [github.com/aimclub/OSA/issues](https://github.com/aimclub/OSA/issues)

2. **Create a new issue**: Click "New Issue" → "Bug Report"

3. **Use the template**:

```markdown
## Bug Description
[Clear, concise description of the problem]

## Steps to Reproduce
1. [First step: e.g., "Install OSA via pip"]
2. [Second step: e.g., "Run command: osa_tool -r <repo>"]
3. [Third step: e.g., "Observe error message"]

## Expected Behavior
[What should have happened]

## Actual Behavior
[What actually happened, including error messages]

## Environment
- OSA Version: [e.g., 1.2.0]
- Python Version: [e.g., 3.11.5]
- OS: [e.g., Ubuntu 22.04, macOS 14.0, Windows 11]
- Installation: [pip/Docker/source]
- LLM Provider: [OpenAI/Ollama/ITMO/etc.]

## Logs/Error Output
```

[Paste relevant logs or error messages here]

```

## Additional Context
[Screenshots, repository links, or other helpful info]
```

1. **Add labels** (if you have permissions): `bug`, `priority:high`, etc.

2. **Submit** and monitor for maintainer responses.

**Requesting a Feature:**

1. **Search first**: Ensure the feature hasn't been requested

2. **Create a new issue**: Click "New Issue" → "Feature Request"

3. **Use the template**:

```markdown
## Feature Request

### Problem Statement
[What problem does this feature solve?]

### Proposed Solution
[Describe how the feature should work]

### Use Cases
[Who would benefit? Provide examples]

### Alternatives Considered
[What other approaches did you consider?]

### Implementation Notes (Optional)
[Technical suggestions, if you have any]

### Additional Context
[Links, mockups, or related discussions]
```

**Tips for Effective Issues:**

| Do | Don't |
|----|-------|
| ✅ Provide minimal reproducible example | ❌ Post large code dumps without context |
| ✅ Include environment details | ❌ Assume everyone uses your setup |
| ✅ Search before posting | ❌ Create duplicate issues |
| ✅ Be specific about expected behavior | ❌ Write vague titles like "It doesn't work" |
| ✅ Respond to maintainer questions | ❌ Abandon issues after posting |

### 6.3 Where can I get help from developers?

Multiple channels are available for getting help, from quick questions to in-depth technical discussions.

**Support Channels Overview:**

| Channel | Best For | Response Time | Link |
|---------|----------|---------------|------|
| **💬 Telegram Chat** | Quick questions, community help, announcements | Minutes to hours | [@OSA_helpdesk](https://t.me/OSA_helpdesk) |
| **🐙 GitHub Issues** | Bug reports, feature requests, technical discussions | 1-7 days | [github.com/aimclub/OSA/issues](https://github.com/aimclub/OSA/issues) |
| **💬 GitHub Discussions** | General questions, ideas, showcase projects | 1-7 days | [github.com/aimclub/OSA/discussions](https://github.com/aimclub/OSA/discussions) |
| **📚 Documentation** | Self-help, API reference, usage guides | Instant | [aimclub.github.io/OSA](https://aimclub.github.io/OSA/) |
| **🎬 Video Tutorials** | Visual learners, step-by-step guides | On-demand | [YouTube Demo](https://www.youtube.com/watch?v=LDSb7JJgKoY) |

**Telegram Community Details:**

**[@OSA_helpdesk](https://t.me/OSA_helpdesk)** is the primary real-time support channel:

| Feature | Description |
|---------|-------------|
| **Active Community** | Developers, researchers, and users from around the world |
| **Maintainer Presence** | Core team members regularly answer questions |
| **Announcements** | Release notes, events, and project updates |
| **Networking** | Connect with other OSA users and collaborators |
| **Language** | Primarily English and Russian |

**When to Use Each Channel:**

| Need | Recommended Channel |
|------|---------------------|
| "How do I install OSA?" | Documentation |
| "I found a bug" | GitHub Issues |
| "Can OSA do X?" | Telegram or GitHub Discussions |
| "I have a feature idea" | GitHub Discussions → GitHub Issues |
| "Can you review my PR?" | GitHub PR comments + Telegram mention |
| "Security concern" | Direct message to maintainers (private) |
| "Just saying thanks!" | GitHub Star |

⚠️ **Please respect maintainers' time**: Use public channels when possible, and provide complete information upfront.

### 6.4 Is there a Telegram community?

**Yes!** OSA has an active Telegram community for real-time support and collaboration.

**Join the Community:**

🔗 [**@OSA_helpdesk**](https://t.me/OSA_helpdesk)

**Community Guidelines:**

✅ **Do:**

- Search chat history before asking
- Share your OSA success stories
- Help others when you can
- Keep discussions respectful and on-topic

❌ **Don't:**

- Spam or advertise unrelated projects
- Share API keys or sensitive credentials
- Use aggressive or disrespectful language
- Expect immediate responses (maintainers have other commitments)

### 6.5 How do I cite OSA in my research? {#how-do-i-cite-osa-in-my-research}

If you use OSA in your research or mention it in publications, please cite the project appropriately.

**Citation Formats:**

**Simple Format (for text):**

```txt
Nikitin N. et al. An LLM-Powered Tool for Enhancing Scientific Open-Source Repositories // 
Championing Open-source DEvelopment in ML Workshop@ ICML25.
```

**BibTeX Format (for LaTeX):**

```bibtex
@inproceedings{nikitinllm,
  title={An LLM-Powered Tool for Enhancing Scientific Open-Source Repositories},
  author={Nikitin, Nikolay and Getmanov, Andrey and Popov, Zakhar and 
      Ulyanova, Ekaterina and Aksenkin, Yaroslav and 
      Sokolov, Ilya and Boukhanovsky, Alexander},
  booktitle={Championing Open-source DEvelopment in ML Workshop@ ICML25},
  year={2025},
  url={https://aimclub.github.io/OSA/}
}
```

**Example Repository Badge:**

```markdown
[![OSA-improved](https://img.shields.io/badge/improved%20by-OSA-yellow)](https://github.com/aimclub/OSA)
```

Renders as: [![OSA-improved](https://img.shields.io/badge/improved%20by-OSA-yellow)](https://github.com/aimclub/OSA)

---
*[↑ Back to Section 6](#contributing-community)*  

*[↑ Top](#quick-navigation)*

## Section 7: Technical Details {#technical-details}

Welcome to Section 7 of the OSA FAQ! This final section covers the technical architecture, underlying technologies, model recommendations, and advanced configuration options for developers and power users.

### 7.1 What technologies does OSA use? {#technology-stack}

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

### 7.2 How does OSA handle repository cloning?

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

### 7.3 What LLM models are recommended? {#llm-models}

Model selection depends on your use case, budget, and quality requirements. Here are evidence-based recommendations.

**Model Recommendations by Task:**

| Task | Recommended Model | Alternative | Budget Option |
|------|------------------|-------------|---------------|
| **README Generation** | GPT-4o | Claude 3.5 Sonnet | GPT-3.5-turbo |
| **Docstring Generation** | GPT-4o | Codellama 13B | GPT-3.5-turbo |
| **CI/CD Workflow** | GPT-4o | Claude 3 Haiku | GPT-3.5-turbo |
| **Code Analysis** | GPT-4o | DeepSeek Coder | Llama 3.1 8B |
| **Research Paper README** | GPT-4o | Claude 3.5 Sonnet | GPT-3.5-turbo |
| **Full Repository** | GPT-4o | Mixtral 8x7B | Llama 3.1 70B |

### 7.4 How do I configure model parameters (temperature, top_p, max_tokens)? {#model-parameters}

Model parameters control the behavior, creativity, and output length of LLM responses.

**Parameter Reference:**

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `--temperature` | Float | 0.0 - 2.0 | 0.05 | Controls randomness/creativity |
| `--top_p` | Float | 0.0 - 1.0 | 0.95 | Nucleus sampling probability |
| `--max_tokens` | Integer | 1 - model max | 4096 | Maximum output tokens |
| `--context_window` | Integer | 1 - model max | 16385 | Total input + output context |

### 7.5 Can I use different models for different tasks?

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

### 7.6 Where is the API documentation?

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

---
*[↑ Back to Section 7](#technical-details)*  

*[↑ Top](#quick-navigation)*
