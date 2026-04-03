# Section 2: Installation & Setup

Welcome to Section 2 of the OSA FAQ! This section covers everything you need to know about installing and setting up OSA on your system.

## 2.1 What are the system requirements?

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

## 2.2 How do I install OSA? {: #how-to-install }

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
| 5️⃣ | Verify installation | `osa-tool --help` |
| 6️⃣ | Run OSA | `osa-tool -r <repository_url>` |

**Quick Verification:**

```bash
# Check if OSA is installed correctly
python -c "import importlib.metadata as m; print(m.version('osa_tool'))"
```

or

```bash
pip show osa_tool
```

## 2.3 What installation methods are available?

OSA supports multiple installation methods to fit different use cases:

OSA supports multiple installation methods to fit different use cases:

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **📦 [PyPI (pip)](https://pypi.org/project/osa-tool/)** | Most users, quick setup | ✅ Easy, fast, auto-dependencies | ⚠️ Less customization |
| **🌐 [Web GUI](https://osa.nsslab.onti.actcognitive.org/)** | Non-technical users | ✅ No installation required | ⚠️ Limited to ITMO-hosted instance |
| **🔧 Source Build** | Developers, contributors | ✅ Full control, latest features | ⚠️ Manual dependency management |
| **🐳 Docker** | Production, consistent environments | ✅ Isolated, reproducible | ⚠️ Larger footprint, Docker knowledge needed |

## 2.4 How do I install using pip?

Installing via PyPI is the recommended method for most users.

**Step-by-Step Instructions:**

```bash
# Step 1: Ensure you have Python 3.11+
python --version

# Step 2: Install OSA from PyPI
pip install osa_tool

# Step 3: Verify installation
osa_tool --help
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

## 2.5 How do I build from source?

Building from source is recommended for developers who want to contribute or use the latest features.

**Complete Steps:**

```bash
# Step 1: Clone the OSA repository
git clone https://github.com/aimclub/OSA
cd OSA

# Step 2: Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# Step 3: Choose your dependency manager

# Option A: Using pip
pip install -r requirements.txt

# Option B: Using poetry (recommended for development)
poetry install

# Step 4: Run tests
pytest .

# Step 5: Verify installation
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

## 2.6 How do I use OSA with Docker?

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
