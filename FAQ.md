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

### 3.1 What tokens/API keys do I need?

### 3.2 How do I set up OPENAI_API_KEY?

### 3.3 How do I set up GIT_TOKEN?

### 3.4 What is the .env file and how do I create it?

### 3.5 Which LLM providers are supported?

### 3.6 How do I configure different LLM providers?

### 3.7 Can I use local LLM models?

### 3.8 How do I use the ITMO hosted model?

### 3.9 What configuration options are available?

### 3.10 How do I use custom TOML configuration?

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
