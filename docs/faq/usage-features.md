# Section 4: Usage & Features

Welcome to Section 4 of the OSA FAQ! This section covers everything you need to know about running OSA, understanding its features, and maximizing its capabilities for your repository improvement workflow.

## 4.1 How do I run OSA? {: #how-to-run }

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

## 4.2 What command-line arguments are available?

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

## 4.3 How does README generation work?

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

## 4.4 How does documentation generation work? {: #how-readme-generation-works }

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

## 4.5 How does CI/CD workflow generation work?

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

## 4.6 Can OSA work with research paper-based projects?

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

## 4.7 How do I use the `--attachment` option for papers?

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

## 4.8 What are the different operation modes (basic/auto/advanced)?

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

## 4.9 Does OSA create pull requests automatically?

**Yes!** By default, OSA automatically creates pull requests with all proposed changes.

## 4.10 Can I prevent OSA from creating forks/PRs?

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

## 4.11 Which repository platforms are supported?

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

## 4.12 Can I process Jupyter notebooks?

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
