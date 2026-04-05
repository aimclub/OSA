# Section 1: General Questions

Welcome to the OSA (Open-Source Advisor) FAQ! This section covers the most common questions about what OSA is, who it's for, and how to get started.

## 1.1 What is OSA (Open-Source Advisor)? {: #what-is-osa }

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

## 1.2 Who should use OSA?

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

## 1.3 What problems does OSA solve?

OSA addresses critical challenges in open-source project maintenance:

### **Scientific Open-Source Challenges:**

| Problem | Impact | OSA Solution |
|---------|--------|--------------|
| ❌ Code shared without README | Others can't understand or use it | ✅ Auto-generates structured README |
| ❌ No documentation/docstrings | Code is unreadable | ✅ Generates comprehensive docstrings |
| ❌ Missing CI/CD pipelines | No automated testing or quality checks | ✅ Creates customizable workflows |
| ❌ No license file | Legal uncertainty for users | ✅ Adds appropriate license |
| ❌ Poor repository structure | Confusing navigation | ✅ Reorganizes tests/examples folders |
| ❌ Low security scorecard rating | Reduced trust and adoption | ✅ Improves score from ~2.2 to ~3.7+ |

### **General Developer Challenges:**

| Problem | OSA Solution |
|---------|--------------|
| ❌ Procrastinating on documentation | ✅ Automates it in minutes |
| ❌ Maintaining dozens of repos | ✅ Standardizes across all projects |
| ❌ Missing contribution guidelines | ✅ Generates community files |
| ❌ No time for best practices | ✅ Implements them automatically |

**Key Advantage:** Unlike tools that focus on individual components (e.g., Readme-AI only generates README, RepoAgent only generates code docs), **OSA considers the repository holistically** to make it easier to understand and ready to run.

## 1.4  Is OSA free to use?

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

## 1.5 What license does OSA use?

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

## 1.6 Who developed OSA?

OSA was developed by researchers and developers at **ITMO University** (Saint Petersburg, Russia) as part of the **AI Initiative Research Project (RPAII)**.
Core Authors:

- Nikolay Nikitin
- Andrey Getmanov
- Zakhar Popov
- Ekaterina Ulyanova
- Ilya Sokolov

The project is tested and supported by the [ITMO OpenSource community](https://t.me/scientific_opensource).

## 1.7 Where can I find publications about OSA?

OSA has been published and presented at several venues:

| Language   | Publication                                                              | Link                                                                                                                             |
|------------|--------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| 🇬🇧 English | Automate Your Coding with OSA – ITMO-Made AI Assistant for Researchers   | [ITMO News](https://news.itmo.ru/en/news/14282)                                                                                  |
| 🇬🇧 English | An LLM-Powered Tool for Enhancing Scientific Open-Source Repositories    | [ICML 2025 Workshop](https://openreview.net/pdf?id=lrWseP67ab)                                                                                                           |
| 🇬🇧 English | An End-to-End Guide to Beautifying Your Open-Source Repo with Agentic AI | [Towards Data Science](https://towardsdatascience.com/an-end-to-end-guide-to-beautifying-your-open-source-repo-with-agentic-ai/) |
| 🇷🇺 Russian | OSA: ИИ-помощник для разработчиков научного open source кода             | [Habr](https://habr.com/ru/companies/spbifmo/articles/906018)                                                                    |

For citation formats, see [How do I cite OSA in my research?](contributing-community.md#how-to-cite)

## 1.8 What is the OSA community and how do I join?

The OSA community consists of developers, researchers, and users who contribute to and support the project.

**Ways to Connect:**

| Platform | Purpose | Link |
|----------|---------|------|
| 🐙 **GitHub Repository** | Report issues, contribute code, view PRs | [github.com/aimclub/OSA](https://github.com/aimclub/OSA) |
| 📚 **Documentation** | Learn about API, features, and usage | [aimclub.github.io/OSA](https://aimclub.github.io/OSA/) |
| 🎬 **Video Demo** | Watch OSA in action | [YouTube](https://www.youtube.com/watch?v=LDSb7JJgKoY) |
| 🌐 **Open-source-ops** | Related tools, content, and best practices | [github.com/aimclub/open-source-ops](https://github.com/aimclub/open-source-ops) |
| 💬 **Telegram Chat** | Ask questions, get help, share news | [@OSA_helpdesk](https://t.me/OSA_helpdesk) |

**Community Benefits:**

- 🆘 Get help from developers directly
- 📢 Stay updated on new features
- 🤝 Connect with other OSA users
- 💡 Share your use cases and improvements

## 1.9 What languages and platforms does OSA support?

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
