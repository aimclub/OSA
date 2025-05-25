<p align="center">

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

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

OSA (Open-Source-Advisor) is a LLM-based tool for improving the quality of scientific open source projects and helping create them from scratch. 
It automates the generation of README, different levels of documentation, CI/CD scripts, etc. 
It also generates advices and recommendations for the repository.

OSA is currently under development, so not all features are implemented.

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

1. **README file generation**: Automates the creation of a clear and structured README file for a repository, including projects based on research papers.

2. **Documentation generation**: Automatically generates docstrings for Python code.

3. **Automatic implementation of changes**: Clones the repository, creates a branch, commits and pushes changes, and creates a pull request with proposed changes.

4. **Various LLMs**: Use OSA with an LLM accessible via API (e.g., OpenAI, VseGPT, Ollama), a local server, or try an [osa_bot](https://github.com/osa-bot) hosted on ITMO servers.

5. **GitHub Action Workflow Generator**: Automatically generates customizable CI/CD workflows for Python repositories, including unit tests, code formatting, PEP 8 compliance checks, and PyPI publication.

---

## Installation

Install Open-Source-Advisor using one of the following methods:

**Using PyPi:**

```sh
pip install osa_tool
```

**Build from source:**

1. Clone the Open-Source-Advisor repository:
```sh
git clone https://github.com/aimclub/OSA
```

2. Navigate to the project directory:
```sh
cd Open-Source-Advisor
```

3. Install the project dependencies:

**Using `pip`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Pip-3776AB.svg?style={badge_style}&logo=pypi&logoColor=white" />](https://pypi.org/project/pip/)

```sh
pip install -r requirements.txt
```

**Using `poetry`** &nbsp;
[<img align="center" src="https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json" />](https://python-poetry.org/)

```sh
poetry install 
```

**Using `docker`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Docker-2CA5E0.svg?style={badge_style}&logo=docker&logoColor=white" />](https://www.docker.com/)

```sh
docker build --build-arg GIT_USER_NAME="your-user-name" --build-arg GIT_USER_EMAIL="your-user-email" -f docker/Dockerfile -t {image-name} .
```

---

## Getting started

### Prerequisites

OSA requires Python 3.10 or higher.

File `.env` is required to specify GitHub token (GIT_TOKEN) and LLM API key (OPENAI_API_KEY or VSE_GPT_KEY)

When running `osa-tool` from CLI, you need to set the GIT_TOKEN and API key first:

```commandline
export OPENAI_API_KEY=<your_api_key>
export GIT_TOKEN=<your_git_token>
```

### Tokens

| Token name       | Description                                                                                                        | Mandatory |
|------------------|--------------------------------------------------------------------------------------------------------------------|-----------|
| `GIT_TOKEN`      | Personal GitHub token used to clone private repositories, access metadata, and interact with the GitHub API.       | Yes       |
| `OPENAI_API_KEY` | API key for accessing [OpenAI](https://platform.openai.com/docs/api-reference/introduction)'s language models.     | No        |
| `VSE_GPT_KEY`    | API key for [vsegpt](https://vsegpt.ru/Docs/API) LLM provider compatible with OpenAI's API format.                 | No        |
| `X-API-Key`      | API key for the [pepy.tech](https://pepy.tech/pepy-api) REST API, used to fetch Python package download statistics | No        |

### Usage

Run Open-Source-Advisor using the following command:

**Using `pip`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Pip-3776AB.svg?style={badge_style}&logo=pypi&logoColor=white" />](https://pypi.org/project/pip/)

```sh
python -m osa_tool.run -r {repository} [--api {api}] [--base-url {base_url}] [--model {model_name}] [--article {article}] [--convert-notebooks {notebook_paths}]
```

**Using `docker`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Docker-2CA5E0.svg?style={badge_style}&logo=docker&logoColor=white" />](https://www.docker.com/)

```sh
docker run --env-file .env {image-name} -r {repository} [--api {api}] [--base-url {base_url}] [--model {model_name}] [--article {article}] [--convert-notebooks {notebook_paths}]
```

The --article option enables you to choose a README template for a repository based on an article. You can provide either a link to a PDF file of the article or a path to a local PDF file after the --article option. If you are using Docker, ensure that you upload the PDF file to the OSA folder before building the image, then, specify the path as /app/OSA/... or just use volume mounting to access the file.

The --generate-workflows option is intended to create customizable CI/CD pipelines for Python repositories. For detailed documentation, see the [GitHub Action Workflow Generator README](./osa_tool/github_workflow/README.md).

### Configuration

| Flag                   | Description                                                                   | Default                     |
|------------------------|-------------------------------------------------------------------------------|-----------------------------|
| `-r`, `--repository`   | URL of the GitHub repository (**Mandatory**)                                  |                             |
| `-b`, `--branch`       | Branch name of the GitHub repository                                          | Default branch              |
| `--api`                | LLM API service provider                                                      | `llama`                     |
| `--base-url`           | URL of the provider compatible with API OpenAI                                | `https://api.openai.com/v1` |
| `--model`              | Specific LLM model to use                                                     | `gpt-3.5-turbo`             |
| `--article`            | Link to the pdf file of the article                                           | `None`                      |
| `--translate-dirs`     | Enable automatic translation of the directory name into English               | `disabled`                  |
| `--convert-notebooks`  | One or more notebook file or directory paths                                  | `repository directory`      |
| `--delete-dir`         | Enable deleting the downloaded repository after processing (**Linux only**)   | `disabled`                  |
| `--generate-workflows` | Enable creation of CI/CD pipelines (**only for Python repositories**)         | `disabled`                  |
| `--ensure-license`     | Enable creation of LICENSE file by choice from BSD-3 Clause, MIT or Apache-2.0| `bsd-3`                     |
| `--not-publish-results`       | Avoid create fork and pull request for target repository           | `False`                     |

---

## Examples

Examples of generated README files are available in [examples](https://github.com/aimclub/OSA/tree/main/examples).

URL of the GitHub repository, LLM API service provider (*optional*) and Specific LLM model to use (*optional*) are required to use the generator.

To see available models go there:
1. [OpenAI](https://platform.openai.com/docs/models)
2. [Ollama](https://ollama.com/library)

Local Llama ITMO:
```sh
python -m osa_tool.run -r https://github.com/aimclub/OSA
```  
OpenAI:
```sh
python -m osa_tool.run -r https://github.com/aimclub/OSA --api openai
```
VseGPT:
```sh
python -m osa_tool.run -r https://github.com/aimclub/OSA --api openai --base-url https://api.vsegpt.ru/v1 --model openai/gpt-3.5-turbo
```
Ollama:
```sh
python -m osa_tool.run -r https://github.com/aimclub/OSA --api ollama --base-url http://[YOUR_OLLAMA_IP]:11434 --model gemma3:27b
```

---

## Contributing

- **[Report Issues](https://github.com/aimclub/OSA/issues )**: Submit bugs found or log feature requests for the Open-Source-Advisor project.

---

## License

This project is protected under the BSD 3-Clause "New" or "Revised" License. For more details, refer to the [LICENSE](https://github.com/aimclub/OSA/blob/main/LICENSE) file.

---
