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
Open-Source-Advisor automates IT Operations Manual (ITMO) documentation generation by integrating configuration, documentation, version control, and code analysis components. This project simplifies and accelerates the creation of ITMO documentation for IT professionals and teams, enhancing efficiency and consistency in operational processes.
</overview>

---


## Table of contents

- [Core features](#core-features)
- [Installation](#installation)
- [Examples](#examples)
- [Documentation](#documentation)
- [Getting started](#getting-started)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Contacts](#contacts)
- [Citation](#citation)

---

## Core features

<corefeatures>

1. **Automated Documentation Generation**: Codebase automates IT Operations Manual documentation generation process.
   
2. **Containerization with Docker**: Project is containerized using Docker for easy deployment and management.

3. **GitHub Integration**: Utilizes 'githubagent.py' for version control and interaction with GitHub.

4. **Code Analysis with Treesitter**: 'osatreesitter.py' parses and analyzes code syntax for documentation generation.

5. **Configuration Management**: Configuration settings stored in 'config.toml' and 'prompts.toml' for customization.

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
❯ docker build -t ITMO-NSS-team/Open-Source-Advisor .
```



---


## Examples

Examples of how this should work and how it should be used are available in [examples](https://github.com/ITMO-NSS-team/Open-Source-Advisor/tree/main/examples).

---


## Documentation

A detailed Open-Source-Advisor description is available in [Not found any docs]().

---


## Getting started

### Usage

Run Open-Source-Advisor using the following command:
 
 **Using `pip`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Pip-3776AB.svg?style={badge_style}&logo=pypi&logoColor=white" />](https://pypi.org/project/pip/)

```sh
❯ python {entrypoint}
```


**Using `docker`** &nbsp;
[<img align="center" src="https://img.shields.io/badge/Docker-2CA5E0.svg?style={badge_style}&logo=docker&logoColor=white" />](https://www.docker.com/)

```sh
❯ docker run -it {image_name}
```


---


## Contributing


- **[Report Issues](https://github.com/ITMO-NSS-team/Open-Source-Advisor/issues )**: Submit bugs found or log feature requests for the Open-Source-Advisor project.


---


## License

This project is protected under the BSD 3-Clause "New" or "Revised" License. For more details, refer to the [LICENSE](https://github.com/ITMO-NSS-team/Open-Source-Advisor/blob/main/LICENSE) file.

---


## Acknowledgments

- List any resources, contributors, inspiration, etc. here.

---



## Contacts

Your contacts. For example:

- [Telegram channel](https://t.me/) answering questions about your project
- [VK group](<https://vk.com/>) your VK group
- etc.

---


## Citation

If you use this software, please cite it as below.

### APA format:

    ITMO-NSS-team (2024). Open-Source-Advisor repository [Computer software]. https://github.com/ITMO-NSS-team/Open-Source-Advisor

### BibTeX format:

    @misc{Open-Source-Advisor,

        author = {ITMO-NSS-team},

        title = {Open-Source-Advisor repository},

        year = {2024},

        publisher = {github.com},

        journal = {github.com repository},

        howpublished = {\url{https://github.com/ITMO-NSS-team/Open-Source-Advisor.git}},

        url = {https://github.com/ITMO-NSS-team/Open-Source-Advisor.git}
        
    }

---
