# OSA: OPEN-SOURCE ADVISOR

<p align="center">

[![Acknowledgement ITMO](https://raw.githubusercontent.com/aimclub/open-source-ops/43bb283758b43d75ec1df0a6bb4ae3eb20066323/badges/ITMO_badge.svg)](https://itmo.ru/)
[![Open-source-ops website](https://raw.githubusercontent.com/aimclub/open-source-ops/7de1e1321389ec177f236d0a5f41f876811a912a/badges/open--source--ops-black.svg)](https://aimclub.github.io/open-source-ops/)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![OSA-improved](https://img.shields.io/badge/improved%20by-OSA-yellow)](https://github.com/ITMO-NSS-team/Open-Source-Advisor)
[![Telegram Chat](https://img.shields.io/badge/Telegram-group-blue)](https://t.me/OSA_helpdesk)
</p>

<p>Built with:</p>
<p>
	<img src="https://img.shields.io/badge/Python-3776AB.svg?style=BadgeStyleOptions.DEFAULT&logo=Python&logoColor=white" alt="Python">
	<img src="https://img.shields.io/badge/Docker-2496ED.svg?style=BadgeStyleOptions.DEFAULT&logo=Docker&logoColor=white" alt="Docker">
	<img src="https://img.shields.io/badge/GitHub%20Actions-2088FF.svg?style=BadgeStyleOptions.DEFAULT&logo=GitHub-Actions&logoColor=white" alt="GitHub%20Actions">
	<img src="https://img.shields.io/badge/AIOHTTP-2C5BB4.svg?style=BadgeStyleOptions.DEFAULT&logo=AIOHTTP&logoColor=white" alt="AIOHTTP">
	<img src="https://img.shields.io/badge/OpenAI-412991.svg?style=BadgeStyleOptions.DEFAULT&logo=OpenAI&logoColor=white" alt="OpenAI">
	<img src="https://img.shields.io/badge/Pydantic-E92063.svg?style=BadgeStyleOptions.DEFAULT&logo=Pydantic&logoColor=white" alt="Pydantic">
</p>

---
## Overview

<overview>

OSA (Open-Source-Advisor) is a LLM-based tool for improving the quality of scientific open source projects and helping create them from scratch. 
It automates the generation of README, different levels of documentation, CI/CD scripts, etc. 
It also generates advices and recommendations for the repository.

OSA is currently under development, so not all features are implemented.
</overview>

---
## How it works?

Here is a short demo:

![Animation](./docs/images/osa_demo.gif)

---

## Table of contents

- [Core features](#core-features)
- [Installation](#installation)
- [Getting started](#getting-started)
- [Examples](#examples)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Citation](#citation)

---

## Core features

<corefeatures>

1. **README file generation**: Automates the creation of a clear and structured README file for a repository, including projects based on research papers.

2. **Documentation generation**: Automatically generates docstrings for Python code.

3. **Automatic implementation of changes**: Clones the repository, creates a branch, commits and pushes changes, and creates a pull request with proposed changes.

4. **Various LLMs**: Use OSA with an LLM accessible via API (e.g., OpenAI, VseGPT), a local server, or try an [osa_bot](https://github.com/osa-bot) hosted on ITMO servers.

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

**Using `poetry`** &nbsp;
[<img align="center" src="https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json" />](https://python-poetry.org/)

```sh
❯ poetry install 
```

**Using `docker`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Docker-2CA5E0.svg?style={badge_style}&logo=docker&logoColor=white" />](https://www.docker.com/)

```sh
❯ docker build --build-arg GIT_USER_NAME="your-user-name" --build-arg GIT_USER_EMAIL="your-user-email" -f docker/Dockerfile -t {image-name} .
```

---

## Getting started

### Prerequisites

OSA requires Python 3.10 or higher.

File `.env` is required to specify GitHub token (GIT_TOKEN) and LLM API key (OPENAI_API_KEY or VSE_GPT_KEY)

### Usage

Run Open-Source-Advisor using the following command:

**Using `pip`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Pip-3776AB.svg?style={badge_style}&logo=pypi&logoColor=white" />](https://pypi.org/project/pip/)

```sh
❯ python main.py -r {repository} [--api {api}] [--model {model_name}] [--article {article}]
```

**Using `docker`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Docker-2CA5E0.svg?style={badge_style}&logo=docker&logoColor=white" />](https://www.docker.com/)

```sh
❯ docker run --env-file .env {image-name} -r {repository} [--api {api}] [--model {model_name}] [--article {article}]
```

The --article option enables you to choose a README template for a repository based on an article. You can provide either a link to a PDF file of the article or a path to a local PDF file after the --article option. If you are using Docker, ensure that you upload the PDF file to the OSA folder before building the image, then, specify the path as /app/OSA/... or just use volume mounting to access the file.

### Configuration

| Flag           | Description                                  | Default |
|----------------|----------------------------------------------|---------|
| `--repository` | URL of the GitHub repository (**Mandatory**) |         |
| `--api`        | LLM API service provider                     | `llama` |
| `--model`      | Specific LLM model to use                    | `llama` |
| `--article`    | Link to the pdf file of the article          | `None`  |

---

## Examples

Examples of generated README files are available in [examples](https://github.com/ITMO-NSS-team/Open-Source-Advisor/tree/main/examples).

URL of the GitHub repository, LLM API service provider (*optional*) and Specific LLM model to use (*optional*) are required to use the generator.

To see available models go there:
1. [VseGpt](https://vsegpt.ru/Docs/Models)
2. [OpenAI](https://platform.openai.com/docs/models)

Local Llama ITMO:
```sh
python main.py -r https://github.com/ITMO-NSS-team/Open-Source-Advisor
```  
OpenAI:
```sh
python main.py -r https://github.com/ITMO-NSS-team/Open-Source-Advisor --api openai --model gpt-3.5-turbo
```
VseGPT:
```sh
python main.py https://github.com/ITMO-NSS-team/Open-Source-Advisor --api vsegpt --model openai/gpt-3.5-turbo
```

---

## Documentation

Detailed description of OSA API is available [here](https://itmo-nss-team.github.io/Open-Source-Advisor/).

---

## Contributing

- **[Report Issues](https://github.com/ITMO-NSS-team/Open-Source-Advisor/issues )**: Submit bugs found or log feature requests for the Open-Source-Advisor project.

---

## License

This project is protected under the BSD 3-Clause "New" or "Revised" License. For more details, refer to the [LICENSE](https://github.com/ITMO-NSS-team/Open-Source-Advisor/blob/main/LICENSE) file.

---

## Acknowledgments

The project is supported as ITMO University Research Project in AI Initiative (RPAII).

OSA is tested by the members of [ITMO OpenSource](https://t.me/scientific_opensource) community. Useful content from community 
is available in [**Open-source-ops**](https://github.com/aimclub/open-source-ops)

Also, we thank [**Readme-ai**](https://github.com/eli64s/readme-ai) 
for their code that we used as a foundation for our own version of README generator.

---

## Citation

If you use this software, please cite it as below.

### APA format:

    ITMO, NSS Lab (2025). Open-Source-Advisor repository [Computer software]. https://github.com/ITMO-NSS-team/Open-Source-Advisor

### BibTeX format:

    @misc{Open-Source-Advisor,

        author = {ITMO, NSS Lab},

        title = {Open-Source-Advisor repository},

        year = {2025},

        publisher = {github.com},

        journal = {github.com repository},

        howpublished = {\url{https://github.com/ITMO-NSS-team/Open-Source-Advisor.git}},

        url = {https://github.com/ITMO-NSS-team/Open-Source-Advisor.git}

    }

---
