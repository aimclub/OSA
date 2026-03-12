# FAQ

## Section 1: General Questions

Welcome to the OSA (Open-Source Advisor) FAQ! This section covers the most common questions about what OSA is, who it's for, and how to get started.

### 1.1 What is OSA (Open-Source Advisor)?

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

### 1.2 Who should use OSA?

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

### 1.3 What problems does OSA solve?

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

### 1.4  Is OSA free to use?

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

### 1.5 What license does OSA use?

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

### 1.6 Who developed OSA?

OSA was developed by researchers and developers at **ITMO University** (Saint Petersburg, Russia) as part of the **AI Initiative Research Project (RPAII)**.
Core Authors:

- Nikolay Nikitin
- Andrey Getmanov
- Zakhar Popov
- EkaterinaUlyanova
- Ilya Sokolov

The project is tested and supported by the [ITMO OpenSource community](https://t.me/scientific_opensource).

### 1.7 Where can I find publications about OSA?

OSA has been published and presented at several venues:

| Language   | Publication                                                              | Link                                                                                                                             |
|------------|--------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| 🇬🇧 English | Automate Your Coding with OSA – ITMO-Made AI Assistant for Researchers   | [ITMO News](https://news.itmo.ru/en/news/14282)                                                                                  |
| 🇬🇧 English | An LLM-Powered Tool for Enhancing Scientific Open-Source Repositories    | [ICML 2025 Workshop]()                                                                                                           |
| 🇬🇧 English | An End-to-End Guide to Beautifying Your Open-Source Repo with Agentic AI | [Towards Data Science](https://towardsdatascience.com/an-end-to-end-guide-to-beautifying-your-open-source-repo-with-agentic-ai/) |
| 🇷🇺 Russian | OSA: ИИ-помощник для разработчиков научного open source кода             | [Habr](https://habr.com/ru/companies/spbifmo/articles/906018)                                                                    |

**Citation (Simple Format):**

```Nikitin N. et al. An LLM-Powered Tool for Enhancing Scientific Open-Source Repositories // Championing Open-source DEvelopment in ML Workshop@ ICML25.```

**Citation (BibTeX):**

```bibtex
@inproceedings{nikitinllm,
  title={An LLM-Powered Tool for Enhancing Scientific Open-Source Repositories},
  author={Nikitin, Nikolay and Getmanov, Andrey and Popov, Zakhar and 
      Ulyanova Ekaterina and Aksenkin, Yaroslav and 
      Sokolov, Ilya and Boukhanovsky, Alexander},
  booktitle={Championing Open-source DEvelopment in ML Workshop@ ICML25}
}
```

### 1.8 What is the OSA community and how do I join?

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

## Section 2: Installation & Setup

Welcome to Section 2 of the OSA FAQ! This section covers everything you need to know about installing and setting up OSA on your system.

### 2.1 What are the system requirements?

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

### 2.2 How do I install OSA?

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

### 2.3 What installation methods are available?

OSA supports multiple installation methods to fit different use cases:

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **📦 PyPI (pip)** | Most users, quick setup | ✅ Easy, fast, auto-dependencies | ⚠️ Less customization |
| **🔧 Source Build** | Developers, contributors | ✅ Full control, latest features | ⚠️ Manual dependency management |
| **🐳 Docker** | Production, consistent environments | ✅ Isolated, reproducible | ⚠️ Larger footprint, Docker knowledge needed |
| **🌐 Web GUI** | Non-technical users | ✅ No installation required | ⚠️ Limited to ITMO-hosted instance |

### 2.4 How do I install using pip?

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

### 2.5 How do I build from source?

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

### 2.6 How do I use OSA with Docker?

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

## Section 3: Configuration & API Keys

Welcome to Section 3 of the OSA FAQ! This section covers everything you need to know about configuring OSA, setting up API keys, and managing tokens for seamless operation.

### 3.1 What tokens/API keys do I need?

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

### 3.2 How do I set up OPENAI_API_KEY?

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

### 3.3 How do I set up GIT_TOKEN?

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

### 3.4 Which LLM providers are supported?

OSA supports multiple LLM providers through the [ProtoLLM](https://github.com/aimclub/ProtoLLM/) ecosystem.

**Supported Providers Overview:**

| Provider | API Type | Models Available | Cost | Best For |
|----------|----------|-----------------|------|----------|
| **OpenAI** | OpenAI-compatible | gpt-4, gpt-3.5-turbo, gpt-4o | 💰 Paid | High-quality, reliable results |
| **OpenRouter** | OpenAI-compatible | 100+ models (Claude, Llama, Mistral) | 💰/🆓 Mixed | Flexibility, cost optimization |
| **VseGPT** | OpenAI-compatible | OpenAI models via Russian proxy | 💰 Paid | Users in Russia/CIS region |
| **Ollama** | Local/Ollama API | Llama 3, Gemma, Mistral, custom | 🆓 Free | Privacy, offline use, customization |
| **ITMO Hosted** | OpenAI-compatible | ITMO fine-tuned models | 🆓 Free* | Research, testing, ITMO community |
| **Gigachat** | Native API | GigaChat models by Sber | 💰 Paid | Russian language, local compliance |

### 3.5 How do I configure different LLM providers?

OSA autodetects provider from base url, but you can manually configure it with the following options:

**Configuration Reference Table:**

| Provider | `--api` Value | `--base-url` | Auth Variable | Example Model |
|----------|---------------|--------------|---------------|---------------|
| OpenAI | `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o` |
| OpenRouter | `openai` | `https://openrouter.ai/api/v1` | `OPENAI_API_KEY` | `qwen/qwen3-30b` |
| VseGPT | `openai` | `https://api.vsegpt.ru/v1` | `OPENAI_API_KEY` | `openai/gpt-3.5-turbo` |
| Ollama | `ollama` | `http://localhost:11434` | None | `gemma3:27b` |
| ITMO | `openai` | `https://.../api/v1` | None (or `ITMO_API_KEY`) | `itmo-research` |
| Gigachat | `gigachat` | (auto) | `AUTHORIZATION_KEY` | `GigaChat` |

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

### 3.6 Can I use local LLM models?

**Yes!** OSA fully supports local LLM models via Ollama or self-hosted OpenAI-compatible servers.

### 3.7 How do I use the ITMO hosted model?

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

### 3.8 What configuration options are available?

OSA offers extensive CLI configuration options. For the complete reference visit the [README.md](https://github.com/aimclub/OSA/blob/main/osa_tool/scheduler/README.md).

### 3.9 How do I use custom TOML configuration?

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

## Section 4: Usage & Features

### 4.1 How do I run OSA?

### 4.2 What command-line arguments are available?

### 4.3 How does README generation work?

### 4.4 How does documentation generation work?

### 4.5 How does CI/CD workflow generation work?

### 4.6 Can OSA work with research paper-based projects?

### 4.7 How do I use the `--attachment` option for papers?

### 4.8 What are the different operation modes (basic/auto/advanced)?

OSA offers three modes to fit different needs:

| Mode | Description | Best For |
|------|-------------|----------|
| **🟢 Basic** | Predefined improvements: README, report, community files, tests/examples folders | Quick standard improvements |
| **🔵 Auto (Default)** | LLM analyzes repo and creates customized improvement plan for approval | Most users, balanced approach |
| **🟠 Advanced** | Full manual control over every step and configuration | Power users, specific requirements |

**Experimental Features:**

| Feature | Status | Description |
|---------|--------|-------------|
| **Conversational Mode** | 🚧 Under Development | Natural language requests via CLI |
| **Multi-Agent System** | 🚧 Under Development | Specialized agents for different tasks |

### 4.9 Does OSA create pull requests automatically?

### 4.10 Can I prevent OSA from creating forks/PRs?

### 4.11 Which repository platforms are supported?

### 4.12 Can I process Jupyter notebooks?

## Section 5: Troubleshooting

### 5.1 What do I do if API key authentication fails?

### 5.2 Why can't OSA access my repository?

### 5.3 What if I get permission errors with Git?

### 5.4 How do I fix Docker-related issues?

### 5.5 What if the LLM response is too long/short?

### 5.6 How do I adjust temperature and sampling parameters?

### 5.7 Where do I report bugs?

## Section 6: Contributing & Community

### 6.1 How can I contribute to OSA?

### 6.2 How do I report issues or request features?

### 6.3 Where can I get help from developers?

### 6.4 Is there a Telegram community?

### 6.5 How do I cite OSA in my research?

## Section 7: Technical Details

### 7.1 What technologies does OSA use?

### 7.2 How does OSA handle repository cloning?

### 7.3 What LLM models are recommended?

### 7.4 How do I configure model parameters (temperature, top_p, max_tokens)?

### 7.5 Can I use different models for different tasks?

### 7.6 Where is the API documentation?

---

*Last Updated: March 2026*  
*Contributors: OSA Development Team, ITMO University*
