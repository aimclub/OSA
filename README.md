<p align="center">
    <img src="https://raw.githubusercontent.com/aimclub/open-source-ops/7de1e1321389ec177f236d0a5f41f876811a912a/badges/ITMO_badge.svg" align="center" width="20%">
</p>
<p align="center"><h1 align="center">OPEN-SOURCE-ADVISOR</h1></p>
<p align="center">
	<img src="https://img.shields.io/github/license/ITMO-NSS-team/Open-Source-Advisor?style=BadgeStyleOptions.DEFAULT&logo=opensourceinitiative&logoColor=white&color=blue" alt="license">
	<img src="https://img.shields.io/github/last-commit/ITMO-NSS-team/Open-Source-Advisor?style=BadgeStyleOptions.DEFAULT&logo=git&logoColor=white&color=blue" alt="last-commit">
	<img src="https://img.shields.io/github/languages/top/ITMO-NSS-team/Open-Source-Advisor?style=BadgeStyleOptions.DEFAULT&color=blue" alt="repo-top-language">
	<img src="https://img.shields.io/github/languages/count/ITMO-NSS-team/Open-Source-Advisor?style=BadgeStyleOptions.DEFAULT&color=blue" alt="repo-language-count">
</p>
<p align="center">Built with the tools and technologies:</p>
<p align="center">
	<img src="https://img.shields.io/badge/tqdm-FFC107.svg?style=BadgeStyleOptions.DEFAULT&logo=tqdm&logoColor=black"alt="tqdm">
	<img src="https://img.shields.io/badge/Pytest-0A9EDC.svg?style=BadgeStyleOptions.DEFAULT&logo=Pytest&logoColor=white"alt="Pytest">
	<img src="https://img.shields.io/badge/Docker-2496ED.svg?style=BadgeStyleOptions.DEFAULT&logo=Docker&logoColor=white"alt="Docker">
	<img src="https://img.shields.io/badge/Python-3776AB.svg?style=BadgeStyleOptions.DEFAULT&logo=Python&logoColor=white"alt="Python">
	<img src="https://img.shields.io/badge/GitHub%20Actions-2088FF.svg?style=BadgeStyleOptions.DEFAULT&logo=GitHub-Actions&logoColor=white"alt="GitHub%20Actions">
	<img src="https://img.shields.io/badge/AIOHTTP-2C5BB4.svg?style=BadgeStyleOptions.DEFAULT&logo=AIOHTTP&logoColor=white"alt="AIOHTTP">
	<img src="https://img.shields.io/badge/OpenAI-412991.svg?style=BadgeStyleOptions.DEFAULT&logo=OpenAI&logoColor=white"alt="OpenAI">
	<img src="https://img.shields.io/badge/Pydantic-E92063.svg?style=BadgeStyleOptions.DEFAULT&logo=Pydantic&logoColor=white"alt="Pydantic">
</p>
<br>

---
## Overview

<overview>
Open-Source-Advisor is a productivity tool designed to simplify the management of GitHub repositories by automating tasks related to documentation and configuration. It enhances user experience through customizable outputs, ensuring that project documentation is always current. This tool is ideal for developers seeking to streamline their workflows and maintain high-quality documentation effortlessly.
</overview>

---

## Table of contents

- [Core features](#core-features)
- [Installation](#installation)
- [Getting started](#getting-started)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Citation](#citation)

---

## Core features

<corefeatures>

1. **Main Application Logic**: Centralized in `main.py`, orchestrating overall system behavior.

2. **Configuration Management**: Utilizes multiple TOML files for flexible parameter adjustments and prompts.

3. **Containerization Support**: Dockerfile ensures consistent environments across platforms for deployment.

4. **GitHub Integration**: Automates tasks via `githubagent.py`, enhancing collaboration and version control.

5. **Documentation Generation**: Parses and generates up-to-date project documentation using dedicated scripts.

</corefeatures>

---

## Installation

Install Open-Source-Advisor using one of the following methods:

**Build from source:**

1. Clone the Open-Source-Advisor repository:
```sh
❯ git clone https://github.com/ITMO-NSS-team/Open-Source-Advisor
```

2. Navigate to the project directory:
```sh
❯ cd Open-Source-Advisor
```

3. Install the project dependencies:

**Using `pip`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Pip-3776AB.svg?style={badge_style}&logo=pypi&logoColor=white" />](https://pypi.org/project/pip/)

```sh
❯ pip install -r requirements.txt
```

**Using `docker`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Docker-2CA5E0.svg?style={badge_style}&logo=docker&logoColor=white" />](https://www.docker.com/)

```sh
❯ docker build -f docker/Dockerfile -t {image-name} .
```

---

## Getting started

### Prerequisites

OSA requires Python 3.10 or higher.

File `.env` is required to specify GitHub token and LLM API key (OPENAI_API_KEY or VSE_GPT_KEY)

### Usage

Run Open-Source-Advisor using the following command:

**Using `pip`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Pip-3776AB.svg?style={badge_style}&logo=pypi&logoColor=white" />](https://pypi.org/project/pip/)

```sh
❯ python main.py {repo_url} {api} {model_name}
```

**Using `docker`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Docker-2CA5E0.svg?style={badge_style}&logo=docker&logoColor=white" />](https://www.docker.com/)

```sh
❯ docker run --env-file .env {image-name} {repo_url} {api} {model_name}
```

---

## Examples

Examples of generated README files are available in [examples](https://github.com/ITMO-NSS-team/Open-Source-Advisor/tree/main/examples).

URL of the GitHub repository, LLM API service provider (*optional*) and Specific LLM model to use (*optional*) are required to use the generator.

Local Llama ITMO:
```sh
python main.py https://github.com/ITMO-NSS-team/Open-Source-Advisor
```  
OpenAI:
```sh
python main.py https://github.com/ITMO-NSS-team/Open-Source-Advisor openai gpt-3.5-turbo
```
VseGPT:
```sh
python main.py https://github.com/ITMO-NSS-team/Open-Source-Advisor vsegpt openai/gpt-3.5-turbo
```

---

## Contributing

- **[Report Issues](https://github.com/ITMO-NSS-team/Open-Source-Advisor/issues )**: Submit bugs found or log feature requests for the Open-Source-Advisor project.

---

## License

This project is protected under the BSD 3-Clause "New" or "Revised" License. For more details, refer to the [LICENSE](https://github.com/ITMO-NSS-team/Open-Source-Advisor/blob/main/LICENSE) file.

---

## Acknowledgments

- [**Open-source-ops**](https://github.com/aimclub/open-source-ops)

- [**Readme-ai**](https://github.com/eli64s/readme-ai)

---

## Citation

If you use this software, please cite it as below.

### APA format:

    ITMO-NSS-team (2024). Open-Source-Advisor repository [Computer software]. https://github.com/ITMO-NSS-team/Open-Source-Advisor

### BibTeX format:

    @misc{Open-Source-Advisor,

        author = {ITMO-NSS-team},

        title = {Open-Source-Advisor repository},

        year = {2024}

        publisher = {github.com}

        journal = {github.com repository}

        howpublished = {\url{https://github.com/ITMO-NSS-team/Open-Source-Advisor.git}}

        url = {https://github.com/ITMO-NSS-team/Open-Source-Advisor.git},

    }

---
