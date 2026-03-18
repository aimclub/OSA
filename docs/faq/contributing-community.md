# Section 6: Contributing & Community

Welcome to Section 6 of the OSA FAQ! This section covers everything you need to know about contributing to OSA, engaging with the community, getting help, and properly citing the project in your work.

## 6.1 How can I contribute to OSA? {: #how-to-contribute}

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

## 6.2 How do I report issues or request features?

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

## Problem Statement
[What problem does this feature solve?]

## Proposed Solution
[Describe how the feature should work]

## Use Cases
[Who would benefit? Provide examples]

## Alternatives Considered
[What other approaches did you consider?]

## Implementation Notes (Optional)
[Technical suggestions, if you have any]

## Additional Context
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

## 6.3 Where can I get help from developers?

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

## 6.4 Is there a Telegram community?

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

## 6.5 How do I cite OSA in my research? {: #how-to-cite}

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
        Ulyanova Ekaterina and Aksenkin, Yaroslav and 
        Sokolov, Ilya and Boukhanovsky, Alexander},
    booktitle={Championing Open-source DEvelopment in ML Workshop@ ICML25}
```

**Example Repository Badge:**

```markdown
[![OSA-improved](https://img.shields.io/badge/improved%20by-OSA-yellow)](https://github.com/aimclub/OSA)
```

Renders as: [![OSA-improved](https://img.shields.io/badge/improved%20by-OSA-yellow)](https://github.com/aimclub/OSA)
