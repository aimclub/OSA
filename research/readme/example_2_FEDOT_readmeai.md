<p align="center">
  <img src="FEDOT.png" width="60%" alt="FEDOT-logo">
</p>
<p align="center">
    <h1 align="center">FEDOT</h1>
</p>
<p align="center">
    <em>Where Data Orchestrates Brilliance!</em>
</p>
<p align="center">
	<img src="https://img.shields.io/github/license/aimclub/FEDOT?style=flat&logo=opensourceinitiative&logoColor=white&color=0080ff" alt="license">
	<img src="https://img.shields.io/github/last-commit/aimclub/FEDOT?style=flat&logo=git&logoColor=white&color=0080ff" alt="last-commit">
	<img src="https://img.shields.io/github/languages/top/aimclub/FEDOT?style=flat&color=0080ff" alt="repo-top-language">
	<img src="https://img.shields.io/github/languages/count/aimclub/FEDOT?style=flat&color=0080ff" alt="repo-language-count">
</p>
<p align="center">
		<em>Built with the tools and technologies:</em>
</p>
<p align="center">
	<img src="https://img.shields.io/badge/GNU%20Bash-4EAA25.svg?style=flat&logo=GNU-Bash&logoColor=white" alt="GNU%20Bash">
	<img src="https://img.shields.io/badge/YAML-CB171E.svg?style=flat&logo=YAML&logoColor=white" alt="YAML">
	<img src="https://img.shields.io/badge/SciPy-8CAAE6.svg?style=flat&logo=SciPy&logoColor=white" alt="SciPy">
	<img src="https://img.shields.io/badge/Python-3776AB.svg?style=flat&logo=Python&logoColor=white" alt="Python">
	<img src="https://img.shields.io/badge/Docker-2496ED.svg?style=flat&logo=Docker&logoColor=white" alt="Docker">
	<br>
	<img src="https://img.shields.io/badge/GitHub%20Actions-2088FF.svg?style=flat&logo=GitHub-Actions&logoColor=white" alt="GitHub%20Actions">
	<img src="https://img.shields.io/badge/pandas-150458.svg?style=flat&logo=pandas&logoColor=white" alt="pandas">
	<img src="https://img.shields.io/badge/Pytest-0A9EDC.svg?style=flat&logo=Pytest&logoColor=white" alt="Pytest">
	<img src="https://img.shields.io/badge/NumPy-013243.svg?style=flat&logo=NumPy&logoColor=white" alt="NumPy">
	<img src="https://img.shields.io/badge/JSON-000000.svg?style=flat&logo=JSON&logoColor=white" alt="JSON">
</p>

<br>

#####  Table of Contents

- [ Overview](#-overview)
- [ Features](#-features)
- [ Repository Structure](#-repository-structure)
- [ Modules](#-modules)
- [ Getting Started](#-getting-started)
    - [ Prerequisites](#-prerequisites)
    - [ Installation](#-installation)
    - [ Usage](#-usage)
    - [ Tests](#-tests)
- [ Project Roadmap](#-project-roadmap)
- [ Contributing](#-contributing)
- [ License](#-license)
- [ Acknowledgments](#-acknowledgments)

---

##  Overview

FEDOT is an open-source project designed to streamline the development and optimization of machine learning models through a flexible and scalable framework. The projects core functionality revolves around orchestrating the end-to-end model development lifecycle, from data preprocessing to result interpretation. With a focus on efficiency and scalability, FEDOT enables seamless integration of advanced algorithms and data processing techniques, empowering users to create efficient and scalable machine learning models. By managing the interaction between different components within the system, FEDOT enhances communication and workflow orchestration, ensuring the successful execution of machine learning workflows. The projects value proposition lies in its ability to automate model building and optimization processes, making it a valuable tool for researchers and developers in the machine learning community.

---

##  Features

|    |   Feature         | Description |
|----|-------------------|---------------------------------------------------------------|
| ⚙️  | **Architecture**  | FEDOT's architecture facilitates seamless integration of various modules for orchestrating machine learning workflows. The system's logic enhances flexibility and scalability, ensuring efficient communication between components. README files define workflows and processes for creating scalable ML models. |
| 🔩 | **Code Quality**  | The codebase maintains good quality and style, ensuring readability and maintainability. It follows best practices with clear documentation and well-structured code.|
| 📄 | **Documentation** | Extensive documentation including README files, setup.py, and requirements.txt provides essential information for users. Dependencies are well-documented, ensuring compatibility with base frameworks and libraries.|
| 🔌 | **Integrations**  | Key integrations include XGBoost, LightGBM, Scikit-learn, and other libraries for data processing, modeling, and optimizations. Docker and GitHub Actions are also utilized for CI/CD. |
| 🧩 | **Modularity**    | The codebase exhibits high modularity, enabling code reuse and easy experimentation with different models. Various components are encapsulated for efficient data preprocessing, model structuring, and result interpretation.|
| 🧪 | **Testing**       | Testing frameworks such as pytest are used for ensuring code quality and reliability. Testfixtures and joblib facilitate integration testing of machine learning workflows. |
| ⚡️  | **Performance**   | Efficient resource usage is ensured with libraries like Pandas, Numpy, and Statsmodels. XGBoost and LightGBM enhance model performance. The system can handle complex machine learning workflows effectively. |
| 🛡️ | **Security**      | Measures for data protection involve secured access control to sensitive resources. Dependencies are managed securely, and continuous monitoring is in place to detect and address vulnerabilities.|
| 📦 | **Dependencies**  | Key dependencies include XGBoost, Scikit-learn, LightGBM, Pandas, and other libraries for machine learning and data processing. Docker is used for containerization. |
| 🚀 | **Scalability**   | FEDOT exhibits scalability with the ability to handle increased traffic and load efficiently. The architecture supports seamless integration of advanced algorithms for creating scalable ML models. |

---

##  Repository Structure

```sh
└── FEDOT/
    ├── .github
    │   ├── CODE_OF_CONDUCT.md
    │   ├── CONTRIBUTING.md
    │   ├── ISSUE_TEMPLATE
    │   ├── PULL_REQUEST_TEMPLATE.md
    │   ├── README.rst
    │   └── workflows
    ├── LICENSE.md
    ├── MANIFEST.in
    ├── README.rst
    ├── README_en.rst
    ├── docker
    │   ├── Dockerfile
    │   ├── Dockerfile_light
    │   ├── README.rst
    │   ├── README_en.rst
    │   ├── gpu
    │   └── jupiter
    ├── docs
    │   ├── Makefile
    │   ├── fedot-workflow.png
    │   ├── fedot_logo.png
    │   ├── files
    │   ├── make.bat
    │   └── source
    ├── examples
    │   ├── README.rst
    │   ├── __init__.py
    │   ├── advanced
    │   ├── data
    │   ├── project_import_export.py
    │   ├── real_cases
    │   └── simple
    ├── fedot
    │   ├── __init__.py
    │   ├── api
    │   ├── core
    │   ├── explainability
    │   ├── preprocessing
    │   ├── remote
    │   ├── structural_analysis
    │   ├── utilities
    │   └── version.py
    ├── other_requirements
    │   ├── docs.txt
    │   ├── examples.txt
    │   ├── extra.txt
    │   └── profilers.txt
    ├── requirements.txt
    ├── setup.py
    └── test
        ├── __init__.py
        ├── conftest.py
        ├── data
        ├── integration
        ├── sensitivity
        ├── test_gpu_strategy.py
        └── unit
```

---

##  Modules

<details closed><summary>.</summary>

| File | Summary |
| --- | --- |
| [MANIFEST.in](https://github.com/aimclub/FEDOT/blob/main/MANIFEST.in) | Data for core repositorys functionalities. |
| [README_en.rst](https://github.com/aimclub/FEDOT/blob/main/README_en.rst) | This code file in the FEDOT repository plays a crucial role in managing the interaction between different components within the system. It facilitates the seamless integration of various modules and ensures efficient communication to enable the successful execution of machine learning workflows. This code encapsulates the logic for orchestrating the flow of data and operations, enhancing the overall flexibility and scalability of the system architecture. |
| [README.rst](https://github.com/aimclub/FEDOT/blob/main/README.rst) | This code file in the FEDOT repository serves the critical purpose of defining the workflows and processes for creating efficient and scalable machine learning models using the FEDOT framework. It encapsulates key features for orchestrating the end-to-end model development lifecycle, facilitating seamless integration of advanced algorithms and data processing techniques. |
| [requirements.txt](https://github.com/aimclub/FEDOT/blob/main/requirements.txt) | Specifies dependency versions for the FEDOT repository. Ensures compatibility with base framework TheGolem 0.4.0, and integrates essential libraries for data processing, modeling, optimizations, and plotting. Also includes miscellaneous utilities and test framework requirements. |
| [setup.py](https://github.com/aimclub/FEDOT/blob/main/setup.py) | This code file in the FEDOT repository facilitates the interaction with various machine learning models for automated model building and optimization. It plays a crucial role in coordinating data preprocessing, model structuring, and result interpretation. By encapsulating these functionalities, it empowers users to easily experiment with different models and efficiently analyze the results within the repositorys architecture. |

</details>

<details closed><summary>.github</summary>

| File | Summary |
| --- | --- |
| [README.rst](https://github.com/aimclub/FEDOT/blob/main/.github/README.rst) | This code file in the `FEDOT` repository plays a crucial role in providing advanced functionality for creating and managing machine learning workflows using the FEDOT framework. It enables users to define complex data processing pipelines and optimize model configurations through a user-friendly interface. This code contributes significantly to the repositorys architecture by facilitating the design and execution of sophisticated machine learning experiments while abstracting away complex implementation details. |

</details>

<details closed><summary>.github.ISSUE_TEMPLATE</summary>

| File | Summary |
| --- | --- |
| [config.yml](https://github.com/aimclub/FEDOT/blob/main/.github/ISSUE_TEMPLATE/config.yml) | Enables users to report issues easily by linking to the Fedot Help Desk for questions and answers. Supports a proactive community discussion to enhance project transparency and user engagement. |

</details>

<details closed><summary>.github.workflows</summary>

| File | Summary |
| --- | --- |
| [fix-pep8-command.yml](https://github.com/aimclub/FEDOT/blob/main/.github/workflows/fix-pep8-command.yml) | Enforces PEP8 code style guidelines with automated checks. Improves code readability and consistency by analyzing and formatting code based on predefined rules, enhancing overall code quality in the parent repository. |
| [autopep8.yml](https://github.com/aimclub/FEDOT/blob/main/.github/workflows/autopep8.yml) | Automates code formatting with Autopep8 to maintain consistent style in the repository. Streamlines the development workflow by enforcing PEP 8 standards on every code change before merging. |
| [unit-build.yml](https://github.com/aimclub/FEDOT/blob/main/.github/workflows/unit-build.yml) | Orchestrates unit testing to ensure code quality. Triggers automated testing on each commit, safeguarding against regressions. Facilitates early bug detection for robust software development. |
| [publish_pypi.yml](https://github.com/aimclub/FEDOT/blob/main/.github/workflows/publish_pypi.yml) | Automates PyPI package publishing upon a new tag in the FEDOT repo. Triggers package release process, checks out the code to publish, and builds the distribution package before uploading to PyPI. |
| [integration-build.yml](https://github.com/aimclub/FEDOT/blob/main/.github/workflows/integration-build.yml) | Integrates automatic testing, building, and deployment workflows. Enhances code quality by executing tests and ensuring seamless integration within the repository architecture. |
| [slash-command-dispatch.yml](https://github.com/aimclub/FEDOT/blob/main/.github/workflows/slash-command-dispatch.yml) | Enables automated triggering of GitHub Actions workflows based on slash commands. Key features include dynamic workflow selection and parameter passing for efficient workflow execution within the FEDOT repository architecture. |
| [mirror_repo_to_gitlab.yml](https://github.com/aimclub/FEDOT/blob/main/.github/workflows/mirror_repo_to_gitlab.yml) | Automates mirror sync between GitHub and GitLab for seamless repository management, ensuring consistent code availability across platforms. Streamlines collaboration and enhances project visibility for team members and contributors. |
| [notify.yml](https://github.com/aimclub/FEDOT/blob/main/.github/workflows/notify.yml) | Notifies contributors of workflow statuses via GitHub Actions, enhancing collaboration and project transparency. Key features include automated notifications on pull requests and issues. |

</details>

<details closed><summary>docker</summary>

| File | Summary |
| --- | --- |
| [README_en.rst](https://github.com/aimclub/FEDOT/blob/main/docker/README_en.rst) | This code file in the FEDOT repository plays a crucial role in enabling users to create and manage custom pipelines for automated machine learning workflows. It provides the necessary functionality for defining the pipeline structure and configuring various machine learning components within the framework. This code file essentially empowers users to orchestrate and optimize the end-to-end process of building machine learning models tailored to their specific use cases within the FEDOT ecosystem. |
| [README.rst](https://github.com/aimclub/FEDOT/blob/main/docker/README.rst) | This code file in the FEDOT repository contributes to the projects architecture by providing essential functionality for building and executing advanced machine learning workflows. It enables users to create complex data pipelines, optimize model hyperparameters, and perform automated feature engineering. |
| [Dockerfile_light](https://github.com/aimclub/FEDOT/blob/main/docker/Dockerfile_light) | Enables lightweight containerized execution of FEDOT. Installs Python dependencies, sets the working directory, and configures the Python path within the container. |
| [Dockerfile](https://github.com/aimclub/FEDOT/blob/main/docker/Dockerfile) | Sets up the base image for running FEDOT in a container by installing Python dependencies and setting up the working directory. Ensures proper environment configuration for seamless execution within the container. |

</details>

<details closed><summary>docker.gpu</summary>

| File | Summary |
| --- | --- |
| [conda_gpu_requirements.sh](https://github.com/aimclub/FEDOT/blob/main/docker/gpu/conda_gpu_requirements.sh) | Establishes GPU environment with RAPIDS libraries, Python 3.8, and CUDA toolkit 11.0 for accelerated data processing within the FEDOT repositorys Docker GPU setup. |
| [Dockerfile](https://github.com/aimclub/FEDOT/blob/main/docker/gpu/Dockerfile) | Enables running FEDOT on GPU by setting up the necessary environment, installing dependencies, and configuring the Python path. Streamlines the GPU execution process within the repositorys Docker workflow. |

</details>

<details closed><summary>docker.jupiter</summary>

| File | Summary |
| --- | --- |
| [docker-compose.yml](https://github.com/aimclub/FEDOT/blob/main/docker/jupiter/docker-compose.yml) | Enables running Jupyter notebook for interactive development in the FEDOT repository structure. Builds the Jupyter container with port mapping and volume mounting for seamless integration with the project workspace. |
| [Dockerfile_Jupiter](https://github.com/aimclub/FEDOT/blob/main/docker/jupiter/Dockerfile_Jupiter) | Installs dependencies like pkg-config and HDF5, setting up a Jupyter notebook environment with Fedot and necessary packages. |

</details>

<details closed><summary>fedot</summary>

| File | Summary |
| --- | --- |
| [version.py](https://github.com/aimclub/FEDOT/blob/main/fedot/version.py) | Defines the current version of the repository as 0.7.4. |

</details>

<details closed><summary>fedot.preprocessing</summary>

| File | Summary |
| --- | --- |
| [dummy_preprocessing.py](https://github.com/aimclub/FEDOT/blob/main/fedot/preprocessing/dummy_preprocessing.py) | This code file within the FEDOT repository is responsible for providing essential API functionalities for the FEDOT framework. It serves as a bridge for developers to interact with the core features of FEDOT, enabling seamless integration of automated machine learning workflows. The code encapsulates critical components for data preprocessing, model structuring, explainability, and remote execution, empowering users to leverage FEDOTs capabilities effectively within their projects. Its presence enriches the repositorys architecture by offering a user-friendly interface for leveraging the power of automated machine learning in various applications. |
| [structure.py](https://github.com/aimclub/FEDOT/blob/main/fedot/preprocessing/structure.py) | This code file in the `FEDOT` repository plays a crucial role in managing the core functionalities of the project. It orchestrates the interaction between different modules such as API, core functionality, preprocessing, and structural analysis within the `fedot` package. By providing a cohesive structure and facilitating communication between these components, this code file ensures the smooth execution of machine learning workflows and enhances the overall efficiency and maintainability of the system. |
| [data_type_check.py](https://github.com/aimclub/FEDOT/blob/main/fedot/preprocessing/data_type_check.py) | Enables decorators to check data types (time series, multi time series, image) before running preprocessing functions, ensuring compatibility within the data processing pipeline. |
| [data_types.py](https://github.com/aimclub/FEDOT/blob/main/fedot/preprocessing/data_types.py) | The code file in this repository, located within the `FEDOT/fedot/` directory, plays a crucial role in facilitating the core functionality of the FEDOT framework. It enables seamless interaction with various machine learning components, data preprocessing tools, and model explainability features. By leveraging this code, developers can effortlessly build, analyze, and deploy machine learning workflows, making it a foundational piece within the diverse ecosystem of the FEDOT framework. |
| [categorical.py](https://github.com/aimclub/FEDOT/blob/main/fedot/preprocessing/categorical.py) | The code file in the parent repository FEDOT contributes to the open-source project's core functionality. It plays a critical role in enabling users to interact with the project's API, perform data preprocessing, and conduct structural analysis. Additionally, it enhances the project's explainability features and provides utilities for improved workflow management. The code file aligns with the repository's architecture, supporting the project's overarching goal of facilitating advanced machine learning workflows through a user-friendly interface. |
| [base_preprocessing.py](https://github.com/aimclub/FEDOT/blob/main/fedot/preprocessing/base_preprocessing.py) | This code file in the FEDOT repository plays a critical role in enabling the API functionality for the open-source project. It serves as a bridge between user interactions and the core components of the system, allowing for seamless integration and utilization of the projects features. By abstracting complex functionalities into accessible interfaces, this code file empowers users to leverage the full potential of the FEDOT framework without needing to delve into intricate technical details. Its presence ensures a user-friendly experience and promotes widespread adoption of the project by simplifying interactions with its underlying capabilities. |
| [preprocessing.py](https://github.com/aimclub/FEDOT/blob/main/fedot/preprocessing/preprocessing.py) | This code file in the `FEDOT` repository plays a crucial role in the core functionality of the project. It focuses on implementing key features related to creating and managing machine learning workflows. By defining the fundamental structure and interactions within these workflows, this code enhances the projects capabilities in automating and optimizing data processing and analysis tasks. |

</details>

<details closed><summary>fedot.explainability</summary>

| File | Summary |
| --- | --- |
| [surrogate_explainer.py](https://github.com/aimclub/FEDOT/blob/main/fedot/explainability/surrogate_explainer.py) | This code file, located within the `FEDOT/examples/advanced` directory of the repository, showcases the application of advanced machine learning algorithms and workflows using the FEDOT framework. It demonstrates complex data processing, model orchestration, and result analysis techniques to solve intricate real-world problems efficiently. By leveraging the features provided in this code, developers can gain insights into building sophisticated machine learning pipelines for tasks that demand high levels of customization and optimization within the FEDOT ecosystem. |
| [explainers.py](https://github.com/aimclub/FEDOT/blob/main/fedot/explainability/explainers.py) | Generates pipeline explanations based on a selected method. Determines and creates a suitable explainer instance for a given task type. Visualizes explanations with optional plotting capabilities. |
| [explainer_template.py](https://github.com/aimclub/FEDOT/blob/main/fedot/explainability/explainer_template.py) | Explain and visualize. The class serves as a blueprint for implementing various explanation techniques in the architecture of the FEDOT repository. |

</details>

<details closed><summary>fedot.core</summary>

| File | Summary |
| --- | --- |
| [utils.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/utils.py) | This code file in the `FEDOT` repository plays a crucial role in enabling the integration of advanced machine learning workflows. It facilitates the customization and composition of complex data processing pipelines, empowering users to construct and evaluate sophisticated models for various real-world applications. By providing a flexible and extensible framework, this code file significantly enhances the repositorys capabilities in delivering powerful and scalable machine learning solutions. |
| [constants.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/constants.py) | Defines constants for data split ratios, tuning iterations, API timeout, presets, and minimum pipeline numbers for an open-source projects core functionality. |

</details>

<details closed><summary>fedot.core.caching</summary>

| File | Summary |
| --- | --- |
| [preprocessing_cache_db.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/caching/preprocessing_cache_db.py) | This code file in the `FEDOT` repository is a crucial component that implements advanced algorithms for automated machine learning workflows. It enhances the parent repositorys architecture by providing sophisticated capabilities for data preprocessing, model explainability, and structural analysis. By leveraging this code, users can streamline the process of building, evaluating, and optimizing machine learning pipelines within the FEDOT framework. |
| [pipelines_cache_db.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/caching/pipelines_cache_db.py) | The code file in this repositorys `FEDOT/examples/` directory showcases advanced and simple usage scenarios of the FEDOT framework for automated machine learning. It demonstrates the application of the framework to real cases, along with providing guidance on data preprocessing and project import/export functionalities. This code plays a pivotal role in illustrating the versatility and practicality of FEDOT within different machine learning contexts. |
| [preprocessing_cache.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/caching/preprocessing_cache.py) | Code File SummaryThis code file in the `FEDOT` repository plays a critical role in the projects architecture by providing functionality for advanced data processing and model building tasks. It achieves this by leveraging the core components of the FEDOT library, enabling users to create sophisticated machine learning pipelines for complex predictive modeling scenarios. The file encapsulates key features that empower developers to streamline the development of AI-based solutions while maintaining flexibility and scalability within the project ecosystem. |
| [pipelines_cache.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/caching/pipelines_cache.py) | This code file in the `FEDOT` repository is crucial for implementing core functionality related to structural analysis within the overall architecture. It enables the system to analyze and interpret data structures efficiently, aiding in the process of generating insights and making informed decisions based on the data at hand. This critical feature contributes significantly to the repositorys goal of providing a comprehensive framework for automated machine learning workflows. |
| [base_cache_db.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/caching/base_cache_db.py) | This code file in the `FEDOT` repository contributes to the core functionality of the project by implementing advanced machine learning algorithms for automated model building. It enhances the frameworks capabilities in generating sophisticated predictive models and streamlining the model selection process. By leveraging innovative approaches and algorithms, this code file empowers users to efficiently construct and evaluate complex machine learning pipelines within the FEDOT ecosystem. |
| [base_cache.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/caching/base_cache.py) | Implements a caching mechanism to enhance performance by storing and loading data efficiently using specific DBs for operations and preprocessing. Calculates the percentage of loaded elements versus computed ones and allows resetting scores as needed. |

</details>

<details closed><summary>fedot.core.visualisation</summary>

| File | Summary |
| --- | --- |
| [pipeline_specific_visuals.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/visualisation/pipeline_specific_visuals.py) | This code file within the FEDOT repository serves as a crucial component for enabling streamlined data preprocessing capabilities. It contributes to the overall architecture by providing essential functionalities to enhance data quality and prepare it for subsequent analysis and modeling tasks. Its role is pivotal in ensuring the efficiency and effectiveness of machine learning workflows within the repository. |

</details>

<details closed><summary>fedot.core.operations</summary>

| File | Summary |
| --- | --- |
| [model.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/model.py) | This code file in the `FEDOT` repositorys `fedot` directory supports various features crucial to the parent repositorys architecture. It contributes to the core functionality, API interactions, preprocessing tasks, explainability tools, structural analysis, and utility functionalities within the `FEDOT` framework. This code plays a vital role in enabling end-users to build, analyze, and interpret machine learning models efficiently. |
| [factory.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/factory.py) | This code file in the FEDOT repository is responsible for implementing crucial functionalities related to data preprocessing and feature engineering within the machine learning workflow. It plays a pivotal role in ensuring that the input data is appropriately processed and transformed to enhance model performance. By managing these critical steps, the code significantly contributes to the overall effectiveness and accuracy of the machine learning models developed using the FEDOT framework. |
| [operation.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/operation.py) | This code file in the FEDOT repository plays a crucial role in enabling the orchestration of machine learning workflows. By providing a streamlined approach to defining and executing complex data processing pipelines, it empowers users to efficiently leverage various algorithms for predictive modeling and data analysis tasks. It acts as a central component within the repositorys architecture, facilitating the seamless integration of diverse modules and functionalities to support end-to-end machine learning operations. |
| [automl.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/automl.py) | Implements AutoML strategy defining model fit/predict methods based on OperationTypesRepository for the parent repositorys architecture. |
| [atomized_template.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/atomized_template.py) | This code file within the FEDOT repository plays a crucial role in enabling users to leverage advanced automated machine learning capabilities. It provides essential functions for creating, evaluating, and optimizing machine learning pipelines. This functionality is integral to the core operations of the repository, empowering users to efficiently develop and deploy sophisticated machine learning solutions. |
| [hyperparameters_preprocessing.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/hyperparameters_preprocessing.py) | The code file in the `fedot` directory of the repository plays a crucial role in providing core functionality for the FEDOT framework. It encompasses essential modules like API integration, core algorithms, explainability tools, preprocessing utilities, structural analysis, as well as various support functions. This code file essentially forms the backbone of the FEDOT framework, enabling seamless interaction with data, model creation, and analysis within the project. |
| [atomized_model.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/atomized_model.py) | FEDOT/fedot/api/model.py`The `model.py` file in the `FEDOT` repositorys `api` module acts as a central component for creating and managing machine learning models within the framework. This code file enables users to define, train, and evaluate complex machine learning pipelines effortlessly. It encapsulates functionality for orchestrating the entire model lifecycle, including hyperparameter tuning and performance optimization. By leveraging this file, developers can seamlessly interact with the framework to build and deploy customized machine learning solutions efficiently. |
| [operation_parameters.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/operation_parameters.py) | The code file in this repository plays a crucial role in facilitating the integration of advanced machine learning models for building predictive analytics pipelines. It enhances the repositorys architecture by providing essential functionalities for data preprocessing, model explainability, and structural analysis. The code enables users to efficiently leverage these features to develop robust machine learning solutions, ultimately enhancing the overall capabilities and usability of the parent repository. |
| [data_operation.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/data_operation.py) | Defines the evaluation strategy for data tasks, assigning column types when necessary. Accesses metadata for the specified data operation from the repository. |
| [operation_template.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/operation_template.py) | This code file in the FEDOT repository plays a crucial role in providing an interface for users to interact with machine learning workflows. It facilitates the construction of complex data processing pipelines and model ensembles in a flexible and intuitive manner, enhancing the productivity and efficiency of developers working with the FEDOT framework. |

</details>

<details closed><summary>fedot.core.operations.evaluation</summary>

| File | Summary |
| --- | --- |
| [automl.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/automl.py) | This code file in the FEDOT repository plays a crucial role in the core functionality of the project. It focuses on providing essential APIs for building and managing machine learning workflows. By abstracting complex processes into simple, reusable components, it empowers users to create, analyze, and optimize predictive models efficiently. This code file significantly contributes to the repositorys architecture by enabling seamless integration of machine learning capabilities into various applications. |
| [regression.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/regression.py) | This code file in the FEDOT repository contributes to the core functionality of the open-source project. It plays a critical role in enabling advanced machine learning workflows and pipeline construction. The file encapsulates key algorithms and methods essential for data preprocessing, feature engineering, model training, and prediction generation. Ultimately, it empowers users to build and customize complex machine learning pipelines efficiently within the FEDOT framework. |
| [custom.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/custom.py) | Implements a custom model strategy with fit, predict, and predict_for_fit methods that handle the training and prediction processes using domain-specific implementations in the parent repositorys architecture. |
| [classification.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/classification.py) | This code file in the parent repository `FEDOT` focuses on the core functionalities of the `fedot` package. It plays a vital role in handling API interactions, core system operations, explainability, preprocessing data, conducting structural analysis, and providing utility functions. The file greatly contributes to the overall architecture by ensuring the smooth functioning and performance of these key features within the repository. |
| [time_series.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/time_series.py) | Data_processing.py`This code file `data_processing.py` in the `FEDOT` repository plays a crucial role in managing and transforming data for machine learning workflows. It provides essential functionalities for preprocessing and structuring data, ensuring it is ready for consumption by the core machine learning components within the repository. By handling tasks such as cleaning, encoding, and feature engineering, this module contributes significantly to the overall data pipeline, enhancing the efficiency and effectiveness of the machine learning models developed using the `FEDOT` framework. |
| [boostings.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/boostings.py) | The code file in this repository under the `FEDOT/examples` directory showcases various usage scenarios and applications of the FEDOT framework. It provides practical illustrations of implementing advanced and simple machine learning workflows using FEDOTs capabilities. By presenting real-world cases and demonstrating data processing techniques, the code file serves as a valuable educational and reference tool for users looking to leverage FEDOT for developing efficient machine learning solutions. |
| [text.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/text.py) | Code SummaryThe code file in this repository, located within the `FEDOT/fedot` directory, plays a crucial role in defining the core functionality of the FEDOT framework. It encapsulates essential modules for API interactions, core algorithms, explainability features, preprocessing tasks, remote functionality, structural analysis utilities, and other essential components. This code file acts as the backbone of the FEDOT project, enabling users to leverage its capabilities for developing and deploying machine learning workflows efficiently across various use cases. |
| [common_preprocessing.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/common_preprocessing.py) | Code File SummaryThis code file in the `FEDOT` repository plays a crucial role in enabling advanced workflow management and model development capabilities. It empowers users to seamlessly orchestrate complex data processing pipelines and construct sophisticated machine learning models with ease. By abstracting away the complexities, it allows developers to focus on crafting high-quality models and analyzing results efficiently within the broader architecture of the repository. |
| [data_source.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/data_source.py) | Defines a custom evaluation strategy for machine learning model training and prediction using a specified data source. This strategy fits data during training and predicts on new data, adhering to the EvaluationStrategy interface. |
| [clustering.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/clustering.py) | Implements Sklearn clustering for model fitting and prediction, with a strategy for ignoring warnings. Enhances model training and prediction by leveraging the Sklearn library with customizable parameters for clustering tasks. |
| [evaluation_interfaces.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/evaluation_interfaces.py) | This code file in the FEDOT repository plays a crucial role in enabling the orchestration of high-level machine learning workflows using the FEDOT framework. It provides essential functionalities for constructing, training, and evaluating complex machine learning pipelines efficiently. By structuring and managing these workflows effectively, this code file helps users leverage the full potential of the FEDOT framework in building and deploying advanced machine learning models for diverse applications. |

</details>

<details closed><summary>fedot.core.operations.evaluation.gpu</summary>

| File | Summary |
| --- | --- |
| [regression.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/gpu/regression.py) | Enables GPU-accelerated regression predictions using CuML, handling data conversion and model inference in the FEDOT repository. |
| [classification.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/gpu/classification.py) | Implements a GPU-based strategy for applying classification algorithms from CuML in the Sklearn library. Performs predictions on input data by converting features to cudf DataFrame and utilizing Sklearn-compatible prediction methods. |
| [common.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/gpu/common.py) | This code file in the FEDOT repository plays a crucial role in providing an interface for running machine learning workflows efficiently. It integrates various core functionalities such as API access, preprocessing, and structural analysis, allowing users to build and optimize complex models. Overall, it empowers developers to leverage the full potential of the FEDOT framework in developing and deploying machine learning solutions seamlessly. |
| [clustering.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/gpu/clustering.py) | Implements GPU-based clustering evaluation strategy using CuML for k-means clustering. Fits and predicts on GPU-accelerated data, handling cudf and cuml dependencies, while allowing parameter configuration for training. |

</details>

<details closed><summary>fedot.core.operations.evaluation.operation_implementations</summary>

| File | Summary |
| --- | --- |
| [implementation_interfaces.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/implementation_interfaces.py) | This code file in the `FEDOT` repository plays a crucial role in managing the core functionalities of the open-source project. It enables the orchestration of data preprocessing, feature engineering, model building, and explainability processes within the framework. By leveraging this code, users can create complex machine learning pipelines and conduct structural analysis to optimize performance and interpretability. The file serves as a key component in providing a scalable and flexible environment for developing and deploying machine learning solutions efficiently. |

</details>

<details closed><summary>fedot.core.operations.evaluation.operation_implementations.data_operations</summary>

| File | Summary |
| --- | --- |
| [sklearn_filters.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/data_operations/sklearn_filters.py) | This code file in the FEDOT repository plays a crucial role in managing the core functionality of the FEDOT framework. It ensures effective communication between different modules within the software, facilitating the creation and execution of machine learning workflows. By abstracting complex operations into a simple interface, this code promotes modularity and scalability within the overall architecture of the repository. |
| [ts_transformations.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/data_operations/ts_transformations.py) | This code file in the repository `FEDOT` serves as a critical component in enabling the integration and execution of GPU-based strategies within the framework. By leveraging this code, developers can harness the power of GPUs for accelerated computational tasks, enhancing the overall performance and efficiency of the system without delving into intricate technical details. |
| [categorical_encoders.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/data_operations/categorical_encoders.py) | This code file in the **FEDOT** repository plays a crucial role in defining the core structure and functionalities of the open-source project. It contributes to the **FEDOT** frameworks capabilities in handling data preprocessing, model explainability, remote execution, and structural analysis. By utilizing this code, developers can efficiently build and analyze machine learning workflows, making it a fundamental component of the repositorys architecture. |
| [sklearn_imbalanced_class.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/data_operations/sklearn_imbalanced_class.py) | This code file within the FEDOT repository plays a critical role in orchestrating machine learning workflows using the FEDOT framework. It provides essential functions for defining, optimizing, and interpreting complex machine learning pipelines efficiently. By leveraging this code, developers can streamline the creation and interpretation of automated machine learning models within the FEDOT ecosystem. |
| [text_preprocessing.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/data_operations/text_preprocessing.py) | This code file in the FEDOT repository plays a crucial role in providing core functionality for the platform. It contributes to building and executing machine learning workflows, handling data preprocessing, model explainability, and remote operations. It aligns with the repositorys focus on automating the creation of machine learning pipelines and offers utilities for structural analysis. The file encapsulates key features that enable the seamless orchestration of complex processes within the machine learning ecosystem supported by the repository. |
| [sklearn_selectors.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/data_operations/sklearn_selectors.py) | This code file in the `FEDOT` repository plays a crucial role in the architecture by providing advanced and simple examples showcasing the capabilities of the parent project. It serves as a practical guide for users, demonstrating how to import/export projects and work with real cases. By offering hands-on illustrations, it enhances the understanding of the projects functionalities without delving into technical intricacies. |
| [decompose.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/data_operations/decompose.py) | This code file in the `FEDOT` repository plays a crucial role in enabling advanced machine learning workflows within the parent architecture. It empowers users to effortlessly create, analyze, and optimize complex data pipelines for model development. By leveraging this code, developers can seamlessly design and deploy machine learning solutions across various domains, enhancing the overall flexibility and efficiency of the repositorys machine learning capabilities. |
| [text_pretrained.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/data_operations/text_pretrained.py) | This code file in the `FEDOT` repository contributes to the core functionality of the project by providing essential API endpoints for interacting with machine learning workflows. It enables users to easily build, customize, and evaluate complex pipelines for solving various data science tasks. Through these APIs, developers can streamline the creation and deployment of machine learning models, enhancing productivity and effectiveness in data analysis and prediction tasks. |
| [sklearn_transformations.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/data_operations/sklearn_transformations.py) | This code file in the FEDOT repository plays a crucial role in managing the core functionality of the open-source project. It focuses on providing high-level APIs and utilities that enable users to create and analyze machine learning workflows efficiently. By encapsulating key functionalities such as data preprocessing, model interpretation, and structural analysis, this code contributes significantly to the project's goal of delivering a flexible and user-friendly framework for automated machine learning tasks. |

</details>

<details closed><summary>fedot.core.operations.evaluation.operation_implementations.data_operations.topological</summary>

| File | Summary |
| --- | --- |
| [fast_topological_extractor.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/data_operations/topological/fast_topological_extractor.py) | This code file in the FEDOT repository plays a crucial role in managing the versioning of the project. It ensures that the software follows a structured approach to version control, allowing for clear identification and tracking of changes over time. By enforcing version consistency across the repository, this code file contributes to maintaining the overall integrity and stability of the project. |

</details>

<details closed><summary>fedot.core.operations.evaluation.operation_implementations.models</summary>

| File | Summary |
| --- | --- |
| [knn.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/knn.py) | This code file in the FEDOT repository plays a crucial role in providing essential core functionalities for the framework. It facilitates key operations such as API interactions, core algorithms, explainability features, data preprocessing, and structural analysis. By encapsulating these critical components, the code file significantly contributes to the overall functionality and usability of the FEDOT framework, empowering users to efficiently build, analyze, and interpret machine learning workflows. |
| [discriminant_analysis.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/discriminant_analysis.py) | This code file within the FEDOT repository serves a critical role in enabling the orchestration of machine learning workflows using the FEDOT framework. It encapsulates key functionalities for constructing, optimizing, and evaluating complex machine learning pipelines, empowering users to efficiently experiment with diverse data sources and modeling techniques. |
| [svc.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/svc.py) | Implements multi-class classification with Support Vector Machines. Fits the model to training data and predicts class labels or probabilities. Supports updating models internal parameters. |
| [keras.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/keras.py) | This code file in the `FEDOT` repository plays a crucial role in facilitating the integration and execution of machine learning pipelines using the FEDOT framework. It focuses on orchestrating the workflow for creating, optimizing, and interpreting complex models through a user-friendly interface. Key features include automated model generation, hyperparameter tuning, and model explainability, empowering users to efficiently develop and analyze machine learning solutions. |
| [boostings_implementations.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/boostings_implementations.py) | This code file in the `FEDOT` repository focuses on providing a set of utility functions and tools essential for enhancing the robustness and efficiency of the framework. It plays a critical role in supporting various core functionalities such as data preprocessing, model explainability, and structural analysis within the larger repository architecture. The code contributes to streamlining processes and facilitating seamless interactions between different components of the framework, ensuring smooth execution and optimal performance. |
| [custom_model.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/custom_model.py) | The code file in this repositorys `FEDOT/fedot/core` directory plays a crucial role in the parent repositorys architecture. It serves as the foundational backbone for implementing core functionality in the FEDOT framework. This code file encapsulates essential features that enable the orchestration of machine learning workflows, model training, and prediction generation within the FEDOT ecosystem. Its purpose is central to facilitating the seamless integration of diverse machine learning algorithms and data processing tools, empowering users to develop robust predictive models efficiently. |

</details>

<details closed><summary>fedot.core.operations.evaluation.operation_implementations.models.ts_implementations</summary>

| File | Summary |
| --- | --- |
| [naive.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/ts_implementations/naive.py) | This code file in the FEDOT repository plays a crucial role in implementing advanced machine learning workflows. It focuses on creating custom pipelines for automated model building and analysis. By leveraging the functionalities provided in this file, users can efficiently design, optimize, and interpret complex data pipelines for various ML tasks. It is an essential component within the repositorys architecture, empowering developers to streamline the process of developing and deploying machine learning solutions effectively. |
| [arima.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/ts_implementations/arima.py) | This code file in the parent repository FEDOT plays a critical role in enabling the customization and enhancement of machine learning models through its core functionality. It provides a set of APIs and utilities that empower users to build flexible workflows, conduct structural analysis, and enhance model explainability. By leveraging this code, developers can streamline the preprocessing of data and access remote services efficiently. This crucial component aligns with the repository's architectural vision of providing a comprehensive toolkit for machine learning experimentation and deployment. |
| [poly.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/ts_implementations/poly.py) | SummaryThis code file within the FEDOT repository serves as a key component for managing data preprocessing tasks in machine learning workflows. It provides essential functionalities to clean, transform, and prepare data for modeling, enhancing the efficiency and accuracy of predictive algorithms. By encapsulating robust preprocessing capabilities, this code enables seamless integration of high-quality data processing steps within the broader architecture of the repository, facilitating the development and deployment of advanced machine learning models. |
| [cgru.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/ts_implementations/cgru.py) | This code file in the `FEDOT` repository serves the purpose of handling core functionalities and utilities within the FEDOT framework. It contributes critical features to support various aspects such as API interactions, preprocessing data, explainability of models, structural analysis, and remote operations. This code plays a significant role in enhancing the overall capabilities and flexibility of the FEDOT framework for building and analyzing machine learning pipelines. |
| [statsmodels.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/operations/evaluation/operation_implementations/models/ts_implementations/statsmodels.py) | This code file in the `FEDOT` repository serves a critical role in managing and executing integration tests for the various components of the library. By providing a suite of test cases that simulate real-world scenarios, this code ensures that the core functionalities of `FEDOT` work seamlessly together. Through rigorous testing, it validates the robustness and reliability of the software, contributing to the overall quality and stability of the open-source project. |

</details>

<details closed><summary>fedot.core.composer</summary>

| File | Summary |
| --- | --- |
| [random_composer.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/composer/random_composer.py) | Creates pipelines with optimal performance by composing them using a random search approach. Data source splitting, training, and testing are conducted to optimize pipeline fitness. |
| [composer.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/composer/composer.py) | Defines a base class for composite operations during an optimization process to generate optimal pipeline structures. It enables composing pipelines for single or multi-objective optimization, returning the best pipeline(s) based on specified data. |
| [meta_rules.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/composer/meta_rules.py) | The code file in this repository contributes to building and managing machine learning workflows using the FEDOT framework. It enables users to define, optimize, and execute complex data processing and modeling pipelines efficiently. This code promotes seamless orchestration of diverse machine learning tasks, enhancing productivity and model performance within the parent repositorys architecture. |
| [metrics.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/composer/metrics.py) | This code file in the FEDOT repository plays a crucial role in enabling high-level interaction with machine learning models through a user-friendly API. By offering a simplified interface, it empowers developers to effortlessly leverage complex algorithms for data analysis and model training within the FEDOT ecosystem. This abstraction layer enhances usability and accelerates the integration of advanced machine learning capabilities into diverse projects. |
| [composer_builder.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/composer/composer_builder.py) | SummaryThe code file located in the `FEDOT/fedot/structural_analysis` directory plays a critical role in the parent repositorys architecture by providing functionalities related to structural analysis within the FEDOT framework. It enables the identification and evaluation of complex structural patterns within data, supporting the overall modeling and optimization processes. This code file contributes to the core functionality of FEDOT by enhancing the understanding of the data structures and relationships, ultimately improving the quality of machine learning models built using the framework. |

</details>

<details closed><summary>fedot.core.composer.gp_composer</summary>

| File | Summary |
| --- | --- |
| [specific_operators.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/composer/gp_composer/specific_operators.py) | This code file in the FEDOT repository contributes to the repositorys architecture by providing essential functionalities for building and managing machine learning workflows. Its main purpose is to enable users to create, customize, and analyze complex ML pipelines efficiently. By leveraging the features in this code file, developers can streamline the process of designing and optimizing machine learning models within the FEDOT ecosystem. |
| [gp_composer.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/composer/gp_composer/gp_composer.py) | Code SummaryThe `test_gpu_strategy.py` file in the `test` directory of the `FEDOT` repository evaluates the performance and functionality of GPU strategies implemented in the core algorithms. This crucial test file ensures that the GPU utilization and strategies align with the repositorys emphasis on optimizing computational efficiency using hardware acceleration. By validating GPU strategy implementations, it helps maintain the high-performance standards of the core algorithms within the repository. |

</details>

<details closed><summary>fedot.core.optimisers.objective</summary>

| File | Summary |
| --- | --- |
| [metrics_objective.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/optimisers/objective/metrics_objective.py) | Defines a metric objective class that handles quality and complexity metrics, supporting multi-objective optimization. Parses and assigns metrics from repository, applying appropriate functions based on type. |
| [objective_serialization.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/optimisers/objective/objective_serialization.py) | Enables backward compatibility by parsing JSON objects into appropriate Objective instances, ensuring seamless integration with previous versions of the parent repositorys architecture. |
| [data_source_splitter.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/optimisers/objective/data_source_splitter.py) | This code file in the `FEDOT` repository contributes to the core functionality of the project by implementing key API endpoints for interacting with the machine learning workflow system. It facilitates the creation, customization, and execution of data processing pipelines for predictive modeling tasks. The file encapsulates the logic for managing workflow components, evaluating model performance, and optimizing pipeline configurations, enabling users to efficiently build and deploy machine learning solutions. |
| [data_objective_eval.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/optimisers/objective/data_objective_eval.py) | This code file in the parent repository FEDOT plays a crucial role in providing a high-level overview of the FEDOT library's functionality and capabilities. It serves as a comprehensive guide for users, showcasing various real-world applications and demonstrating how to leverage the library's advanced features. By exploring this code, developers can gain insights into the powerful machine learning capabilities offered by FEDOT and learn how to effectively utilize them in their projects. |

</details>

<details closed><summary>fedot.core.pipelines</summary>

| File | Summary |
| --- | --- |
| [pipeline_builder.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/pipeline_builder.py) | Creates a PipelineBuilder by inheriting OptGraphBuilder. Merges pipeline builders using merge_opt_graph_builders. |
| [template.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/template.py) | This code file in the FEDOT repository plays a critical role in the core functionality of the project. It implements advanced algorithms for automated machine learning workflows, enabling users to build complex data processing pipelines effortlessly. This key component significantly enhances the projects capabilities by providing efficient and customizable solutions for data analysis and model building. |
| [adapters.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/adapters.py) | This code file in the FEDOT repository plays a critical role in enabling advanced machine learning workflows for time series analysis. It facilitates the creation of complex pipeline structures for modeling and forecasting tasks, with a strong emphasis on explainability and preprocessing functionalities. The code enhances the parent repositorys architecture by providing a flexible and extensible framework for building and evaluating machine learning models on time series data, catering to both simple and real-world use cases. |
| [verification.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/verification.py) | This code file in the FEDOT repository plays a critical role in facilitating the interoperability and smooth functioning of different modules within the system. It acts as a bridge, enabling seamless communication and data exchange between various components of the repositorys architecture. By abstracting away complex implementation details, it ensures that the workflow remains robust and efficient, ultimately enhancing the overall performance and user experience of the system. |
| [pipeline_node_factory.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/pipeline_node_factory.py) | This code file in the `FEDOT` repository plays a crucial role in orchestrating machine learning workflows using the FEDOT framework. It enables the seamless integration of diverse data sources, model building, and result interpretation for advanced analytics and predictive modeling. The code file ensures streamlined execution of complex data processing pipelines and empowers users to leverage sophisticated machine learning techniques effectively within the broader architecture of the repository. |
| [random_pipeline_factory.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/random_pipeline_factory.py) | This code file in the `FEDOT` repository plays a critical role in the core functionality of the project. It focuses on facilitating the creation and management of machine learning workflows using a modular and extensible approach. The code enables the construction of complex pipelines for data analysis and modeling, promoting reusability and flexibility in developing diverse ML solutions. |
| [pipeline.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/pipeline.py) | Project_import_export.py`The `project_import_export.py` file within the `examples` directory of the `FEDOT` repository facilitates the seamless import and export of machine learning projects. It empowers users to efficiently share and collaborate on projects, enabling easy migration between environments and fostering reproducibility. This code file plays a crucial role in promoting the interoperability and scalability of machine learning workflows within the overarching architecture of the repository. |
| [automl_wrappers.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/automl_wrappers.py) | Defines serialization wrappers for TPOT and H2O algorithms for classification, regression, and time series forecasting. Facilitates loading and saving H2O algorithm models, enhancing ML pipeline interoperability in the repository. |
| [node.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/node.py) | This code file in the repository `FEDOT` plays a crucial role in managing the core functionality of the FEDOT framework. It enables users to define complex machine learning workflows with ease, incorporating advanced algorithms for data preprocessing, structural analysis, and model explainability. By leveraging this code, developers can create, modify, and evaluate machine learning pipelines efficiently, contributing to the overall flexibility and scalability of the framework. |
| [pipeline_advisor.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/pipeline_advisor.py) | This code file in the FEDOT repository contributes to the core functionality of the project. It plays a crucial role in enabling users to create, analyze, and optimize machine learning pipelines through a user-friendly API. By leveraging this code, developers can efficiently preprocess data, design complex workflows, and gain insights into model explainability. It is a fundamental component that empowers users to harness the full potential of the FEDOT framework for building robust machine learning solutions. |
| [verification_rules.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/verification_rules.py) | This code file within the FEDOT repository provides essential functionalities for creating and manipulating machine learning workflows using the FEDOT framework. It specifically focuses on enabling users to define custom preprocessing steps for their data, enhancing the overall flexibility and control in building predictive models. This feature plays a crucial role in the architecture by empowering users to tailor their data processing pipelines to suit the specific requirements of their machine learning tasks. |
| [pipeline_graph_generation_params.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/pipeline_graph_generation_params.py) | Generates graph generation parameters for pipelines, considering constraints and task requirements, using a factory approach within the pipeline architecture. |
| [ts_wrappers.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/ts_wrappers.py) | This code file within the FEDOT repository serves the critical function of providing essential APIs for data preprocessing, core functionalities, and structural analysis. It enables seamless integration and interaction with the main FEDOT system, contributing to the overall efficiency and robustness of the open-source project. |
| [pipeline_composer_requirements.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/pipeline_composer_requirements.py) | Defines requirements and validation options for Pipelines and data in the parent repository. Sets content types for primary and secondary graph operations, with cross-validation fold settings. Ensures the number of folds for KFold cross-validation is valid. |

</details>

<details closed><summary>fedot.core.pipelines.prediction_intervals</summary>

| File | Summary |
| --- | --- |
| [visualization.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/visualization.py) | This code file in the FEDOT repository serves the critical purpose of managing version control for the project. It helps ensure proper tracking and updating of the software, contributing to the overall stability and reliability of the system. |
| [tuners.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/tuners.py) | Optimize_model.py`The `optimize_model.py` file in the `FEDOT` repository serves the crucial function of fine-tuning machine learning models to achieve optimal performance. This code facilitates the enhancement of model efficiency and accuracy through advanced optimization techniques. By leveraging this file, developers can improve the overall quality and predictive power of their machine learning models within the broader architecture of the parent repository. |
| [utils.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/utils.py) | Fedot/core/data/operations.py`This code file in the `FEDOT` repositorys `core` module defines a set of essential operations crucial for data processing within the framework. It encapsulates the core functionality required for data operations in the machine learning workflows facilitated by the parent repository. The file plays a vital role in enabling efficient data manipulation and transformation, pivotal for the successful execution of various algorithms and models provided by the `FEDOT` framework. |
| [main.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/main.py) | The `main.py` file under `FEDOT` repositorys `fedot/core/pipelines/prediction_intervals` directory is a critical component contributing to the repository's architecture. This code file facilitates the generation of prediction intervals for model predictions, enhancing the overall predictive capabilities of the system. It plays a pivotal role in enabling accurate forecasting and uncertainty estimation within the larger system, supporting robust decision-making processes. |
| [metrics.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/metrics.py) | Calculates quantile loss, prediction interval coverage probability (PICP), and interval score metrics for evaluating prediction intervals in the pipelines module of FEDOT repositorys core architecture. |
| [params.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/params.py) | Fedot/core/individual/operations.py`This code file in the `FEDOT` repositorys architecture focuses on defining the critical operations that individual components can perform within the system. It plays a vital role in enabling the core functionality of the system by encapsulating essential operations for processing and manipulating data. Through this file, the system's components can leverage a set of predefined operations to perform various tasks efficiently, contributing to the overall functionality and versatility of the system. |
| [pipeline_constraints.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/pipeline_constraints.py) | First element consistency between prediction and forecast, assessing oscillation in predictions compared to training series. It ensures pipelines deliver stable and accurate forecasts within defined boundaries. |
| [graph_distance.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/graph_distance.py) | This code file in the parent repository FEDOT focuses on implementing advanced machine learning workflows and data processing capabilities. It plays a crucial role in facilitating the creation and execution of complex predictive models using the FEDOT framework, contributing to the repository's overarching goal of enabling efficient and scalable data analysis solutions. |
| [ts_mutation.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/ts_mutation.py) | This code file in the FEDOT repository plays a crucial role in enabling advanced automated machine learning capabilities. It primarily focuses on orchestrating complex workflows for data processing, feature engineering, and model building. By leveraging a modular architecture, it empowers users to construct and execute customized machine learning pipelines efficiently within the FEDOT framework. |

</details>

<details closed><summary>fedot.core.pipelines.prediction_intervals.solvers</summary>

| File | Summary |
| --- | --- |
| [mutation_of_best_pipeline.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/solvers/mutation_of_best_pipeline.py) | Example_pipeline.py`This code file defines a complex machine learning pipeline within the `FEDOT` repository. The pipeline showcases advanced modeling techniques and data preprocessing steps, serving as a reference for developers to understand how to construct sophisticated workflows using the `FEDOT` framework. By demonstrating the integration of various modules and components provided by the repository, this code file illustrates best practices for building end-to-end machine learning solutions tailored to diverse use cases and datasets. |
| [best_pipelines_quantiles.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/solvers/best_pipelines_quantiles.py) | The code file in this repositorys `FEDOT/fedot/core` directory plays a crucial role in implementing the fundamental functionalities of the FEDOT framework. It focuses on the core components and algorithms necessary for building and executing machine learning workflows efficiently. This code defines the backbone of the framework, enabling the creation and customization of complex machine learning pipelines while ensuring modularity and extensibility are maintained throughout the system. |
| [last_generation_quantile_loss.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/prediction_intervals/solvers/last_generation_quantile_loss.py) | Model_selection.py`The `model_selection.py` file in the `FEDOT` repository plays a crucial role in automating the selection of the best machine learning models for given data. It facilitates the process of identifying and evaluating various models to determine the most suitable one for a specific task. This file is instrumental in optimizing model performance by systematically comparing and choosing the most effective model based on predefined criteria, enhancing the efficiency and accuracy of machine learning workflows within the repository architecture. |

</details>

<details closed><summary>fedot.core.pipelines.tuning</summary>

| File | Summary |
| --- | --- |
| [hyperparams.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/tuning/hyperparams.py) | This code file within the FEDOT repository serves the critical purpose of providing API endpoints for interacting with the core functionality of the FEDOT library. It enables users to access methods for data preprocessing, structural analysis, and model explainability. By abstracting these key features into a well-defined interface, this code supports seamless integration of the FEDOT framework into various applications without the need to delve into the technical complexities of its implementation. |
| [search_space.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/tuning/search_space.py) | This code file in the FEDOT repository plays a crucial role in providing advanced functionalities for constructing and analyzing machine learning workflows. It contributes to the core functionality of FEDOT by enhancing its capabilities in workflow creation, explainability, preprocessing, and structural analysis. The files implementation aligns with the repositorys focus on enabling users to build, evaluate, and interpret complex ML pipelines efficiently. |
| [timer.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/tuning/timer.py) | Enforces time limit in pipelining tuning. Inherits Timer to track process duration, logs termination due to time limit, and returns termination status upon exit. |
| [tuner_builder.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/pipelines/tuning/tuner_builder.py) | This code file in the `FEDOT` repository plays a crucial role in implementing core functionalities for automated machine learning (AutoML) workflows. It enables users to leverage sophisticated data processing, model building, and interpretability features provided by the repository. By abstracting complex machine learning operations into a user-friendly interface, it empowers developers to effortlessly construct and analyze machine learning pipelines for various tasks. |

</details>

<details closed><summary>fedot.core.repository</summary>

| File | Summary |
| --- | --- |
| [operation_types_repository.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/repository/operation_types_repository.py) | This code file in the `FEDOT` repository plays a crucial role in enabling advanced machine learning workflows by providing essential functionalities for data preprocessing, model explanation, and remote execution. It helps streamline the process of analyzing and transforming data to enhance model performance, allowing for improved interpretability and scalability in machine learning projects within the parent repositorys architecture. |
| [json_evaluation.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/repository/json_evaluation.py) | Implements functions to read field values from a dictionary, import enums from string representations, and import evaluation strategy modules based on specified namespace and type. Enhances repositorys flexibility for dynamic handling of data types and evaluation strategies. |
| [tasks.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/repository/tasks.py) | Defines task types and parameters for time series forecasting, classification, regression, and clustering. Enables validation, compatibility, and extraction of task parameters within the broader FEDOT repository architecture. |
| [default_params_repository.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/repository/default_params_repository.py) | Retrieves default parameters for a given operation from a JSON repository file. Maps model names to corresponding parameters, enhancing modularity and configurability within the repository architecture. |
| [pipeline_operation_repository.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/repository/pipeline_operation_repository.py) | This code file in the `FEDOT` repository plays a crucial role in enabling advanced data processing and analysis workflows. It provides essential functionalities related to structural analysis within the repositorys architecture, contributing to the core capabilities of the open-source project. |
| [metrics_repository.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/repository/metrics_repository.py) | Time_series_forecasting.py`The `time_series_forecasting.py` file in the `FEDOT` repository provides a crucial feature for performing time series forecasting using advanced algorithms. This code file enables users to analyze historical data patterns and predict future trends with high accuracy. By leveraging sophisticated models and techniques, this functionality empowers users to make informed decisions based on predictive insights derived from time series data. |
| [dataset_types.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/repository/dataset_types.py) | Table, time series, multi time series, text, image. Each type has a default representation. |
| [graph_operation_repository.py](https://github.com/aimclub/FEDOT/blob/main/fedot/core/repository/graph_operation_repository.py) | Defines an abstract class for extracting models based on graph structures. Methods enable retrieving models by specific keys or all available models. |

</details>

<details closed><summary>fedot.structural_analysis</summary>

| File | Summary |
| --- | --- |
| [sa_requirements.py](https://github.com/aimclub/FEDOT/blob/main/fedot/structural_analysis/sa_requirements.py) | The code file in this repositorys architecture focuses on implementing essential functionality for the FEDOT project. It plays a crucial role in performing advanced data analysis and building machine learning pipelines. It contributes to the core functionalities of the project by enabling users to create, execute, and evaluate complex machine learning workflows efficiently. |

</details>

<details closed><summary>fedot.structural_analysis.operations_hp_sensitivity</summary>

| File | Summary |
| --- | --- |
| [one_operation_sensitivity.py](https://github.com/aimclub/FEDOT/blob/main/fedot/structural_analysis/operations_hp_sensitivity/one_operation_sensitivity.py) | This code file in the `FEDOT` repository plays a crucial role in enhancing the interpretability and explainability of machine learning models built using the `FEDOT` framework. It introduces key functionalities that enable users to gain insights into the decision-making process of the models, supporting transparency and trust in the results produced by the system. By providing tools for explaining model predictions, this code contributes significantly to the overall transparency and usability of the machine learning workflows facilitated by the `FEDOT` platform. |
| [problem.py](https://github.com/aimclub/FEDOT/blob/main/fedot/structural_analysis/operations_hp_sensitivity/problem.py) | The code file in question enables the utilization of advanced machine learning workflows within the FEDOT repository. By leveraging this code, users can streamline the creation and assessment of complex data science pipelines, empowering them to derive meaningful insights from their data efficiently. |
| [multi_operations_sensitivity.py](https://github.com/aimclub/FEDOT/blob/main/fedot/structural_analysis/operations_hp_sensitivity/multi_operations_sensitivity.py) | This code file within the `FEDOT` repository plays a crucial role in the architecture by providing foundational structures for machine learning workflows. It facilitates the creation and manipulation of complex pipelines for data processing and modeling. Through its interfaces and utilities, it empowers users to efficiently build, analyze, and optimize machine learning pipelines for a variety of tasks and datasets. |
| [params_bounds.json](https://github.com/aimclub/FEDOT/blob/main/fedot/structural_analysis/operations_hp_sensitivity/params_bounds.json) | This code file in the FEDOT repository serves a critical role in managing the workflows for the framework. It facilitates the seamless integration and orchestration of tasks within the system, ensuring efficient execution and coordination of various processes. By handling workflow management, this code file plays a key part in maintaining the overall architecture of the repository, enabling effective collaboration and streamlined development practices. |
| [sa_and_sample_methods.py](https://github.com/aimclub/FEDOT/blob/main/fedot/structural_analysis/operations_hp_sensitivity/sa_and_sample_methods.py) | Implements sensitivity analysis using Sobol and Saltelli methods for pipelines in the parent repositorys structural analysis module.araohod_hp_sensitivity/hp_sensitivity.py in FEDOT. |

</details>

<details closed><summary>fedot.utilities</summary>

| File | Summary |
| --- | --- |
| [window_size_selector.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/window_size_selector.py) | Train.py`This code file `train.py` in the `FEDOT` repository serves as a crucial component for training machine learning models using the FEDOT framework. It implements a streamlined process for training models, enabling users to efficiently leverage the capabilities of FEDOT for creating and optimizing complex machine learning pipelines.By encapsulating the training logic, `train.py` provides a high-level interface for users to train models effortlessly, abstracting away the complexities of the underlying model training process. This code file significantly contributes to the seamless integration of the FEDOT framework into various machine learning projects, empowering developers to focus on model development and experimentation without getting bogged down by implementation intricacies. |
| [memory.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/memory.py) | Monitors and logs Python memory consumption. Features memory session start/finish, memory measures retrieval, and logging capabilities. Enhances system memory analysis in the FEDOT repository. |
| [debug.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/debug.py) | The code file in this repositorys `examples` directory showcases both advanced and simple use cases of the FEDOT framework. It demonstrates how to import and export projects, providing real-world scenarios for leveraging the capabilities of the framework. This code file serves as a practical guide for users looking to implement FEDOT in their machine learning projects, offering insights into the frameworks functionalities and potential applications. |
| [define_metric_by_task.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/define_metric_by_task.py) | Defines default quality metrics per task for various machine learning problems, accessing metric values based on task type and computing the corresponding metric with a specified rounding precision. |
| [custom_errors.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/custom_errors.py) | MethodNotImplementError` and `AbstractMethodNotImplementError`. Enhances codebase maintainability and readability by providing clear error messages. Improves developer understanding when working with abstract classes. |
| [synth_dataset_generator.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/synth_dataset_generator.py) | This code file in the `FEDOT` repository serves a critical role in implementing advanced machine learning workflows using the FEDOT framework. It enables users to create complex pipelines for data processing and modeling, facilitating seamless integration of various data transformation and predictive modeling techniques. By leveraging this code, developers can construct sophisticated machine learning pipelines with ease, aiding in the analysis and optimization of predictive models for diverse use cases across industries. |
| [golem_imports_transition.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/golem_imports_transition.py) | The code file in this repository contributes to the FEDOT project, which focuses on creating automated machine learning workflows. This specific code file plays a crucial role in defining and orchestrating various data preprocessing operations within the FEDOT framework. It enables users to streamline data preparation tasks efficiently, facilitating the creation of robust machine learning pipelines. |
| [composer_timer.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/composer_timer.py) | This code file in the FEDOT repository plays a crucial role in enabling the seamless transition between various stages of machine learning model development. It encapsulates a set of functions and utilities that facilitate efficient data preprocessing, model structuring, and explainability analysis. By abstracting away the complexity of these tasks, this code enhances the overall user experience and empowers developers to focus on building high-performing machine learning models. |
| [random.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/random.py) | Implements custom random state handling for data and model operations in the parent repositorys architecture. Manages random seed settings for operations during execution within the framework. |
| [pattern_wrappers.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/pattern_wrappers.py) | Implements a decorator to ensure a single instance of a class, promoting efficient memory usage and preventing unnecessary object duplication within the FEDOT repository architecture. |
| [project_import_export.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/project_import_export.py) | The code file in question aims to facilitate data preprocessing tasks within the broader FEDOT repository. It plays a critical role in ensuring that input data is properly formatted and cleaned before being utilized in the machine learning workflow provided by the project. By abstracting away the complexities of data preparation, this code module enables users to seamlessly integrate their datasets for model training and evaluation, enhancing the overall efficiency and effectiveness of the system. |
| [ts_gapfilling.py](https://github.com/aimclub/FEDOT/blob/main/fedot/utilities/ts_gapfilling.py) | This code file in the `FEDOT` repository plays a crucial role in providing an intuitive and powerful API for users to interact with the core functionalities of the system. By abstracting complex processes and providing simplified interfaces, it enables users to effortlessly leverage the capabilities of the framework to build, optimize, and analyze machine learning pipelines. This API module serves as the gateway for users to create, evaluate, and deploy custom machine learning workflows efficiently within the `FEDOT` ecosystem. |

</details>

<details closed><summary>fedot.api</summary>

| File | Summary |
| --- | --- |
| [main.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/main.py) | Code SummaryThe `main.py` file in the `api` module of the `FEDOT` repository acts as the entry point for interacting with the core functionality of the FEDOT framework. It provides a high-level interface for users to leverage the capabilities of FEDOT, such as initiating machine learning workflows, optimizing hyperparameters, and evaluating model performance. By encapsulating these key operations, `main.py` simplifies the usage of FEDOT and allows users to focus on building and deploying machine learning pipelines efficiently. |
| [builder.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/builder.py) | This code file in the `FEDOT` repository plays a crucial role in the core functionality of the project. It contributes to the implementation of key features related to machine learning workflows, data preprocessing, and model explainability. By leveraging this code, users can efficiently build, analyze, and interpret complex machine learning pipelines. Its integration within the projects architecture underscores a commitment to providing a comprehensive framework for developing advanced data analysis solutions. |
| [fedot_cli.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/fedot_cli.py) | This code file within the FEDOT repository plays a critical role in enabling advanced data processing and model building workflows. It provides essential functionalities for structuring and analyzing data, facilitating model interpretability, and streamlining preprocessing tasks. By leveraging this code, users can effectively manipulate data, interpret model outcomes, and optimize data processing pipelines within the parent repositorys architecture. |
| [help.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/help.py) | This code file in the FEDOT repository plays a crucial role in enabling automated machine learning workflows. It leverages FEDOTs core functionalities to streamline the process of building, training, and evaluating machine learning models. By providing a user-friendly interface and powerful tools for data preprocessing, model structuring, and explainability, this code enhances the repositorys mission of democratizing AI and empowering users to create impactful solutions effortlessly. |
| [time.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/time.py) | The code file in the parent repository `FEDOT` serves as a comprehensive library for Automated Machine Learning (AutoML). It facilitates the creation and optimization of machine learning pipelines with minimal manual intervention, promoting efficiency and accuracy in model development. The code file is pivotal in enabling users to streamline their workflow by automating the process of model selection, hyperparameter tuning, and feature engineering, ultimately enhancing the overall productivity of data scientists and machine learning engineers. |

</details>

<details closed><summary>fedot.api.api_utils</summary>

| File | Summary |
| --- | --- |
| [api_composer.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/api_composer.py) | This code file in the `FEDOT` repository plays a key role in enabling remote deployment of machine learning workflows. It provides essential functionality for orchestrating and executing complex predictive modeling tasks on remote servers or cloud instances. By leveraging this code, users can seamlessly manage and monitor machine learning operations remotely, enhancing scalability and efficiency in model development and deployment processes within the repositorys architecture. |
| [predefined_model.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/predefined_model.py) | This code file in the `FEDOT` repository plays a crucial role in enabling advanced machine learning workflows using the FEDOT framework. It provides essential APIs and core functionalities for building, analyzing, and explaining machine learning models. By leveraging this code, users can preprocess data, conduct structural analysis, and access utilities for streamlined model development. Its integration within the repository architecture supports the creation and deployment of complex machine learning pipelines for diverse use cases. |
| [input_analyser.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/input_analyser.py) | This code file in the `FEDOT` repository plays a crucial role in enabling the seamless integration and interaction of various components within the project. It facilitates the orchestration and communication between different modules and functionalities, contributing significantly to the overall architectures robustness and flexibility. |
| [api_params_repository.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/api_params_repository.py) | This code file in the `FEDOT` repository plays a crucial role in facilitating the import and export of machine learning projects. It provides functionality to seamlessly transfer complex workflows between different environments, enabling developers to leverage and share their models efficiently. This feature enhances collaboration and productivity within the repository by promoting interoperability and reusability of machine learning pipelines in diverse settings. |
| [presets.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/presets.py) | FEDOT/fedot/core/data/input_data.py`This code file in the `FEDOT` repository serves a crucial role in handling input data for the framework. It enables the seamless processing and transformation of data to suit the requirements of various machine learning workflows. The code facilitates efficient data manipulation tasks, ensuring compatibility and integration with the wider functionalities offered by the repositorys core modules. |
| [api_data.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/api_data.py) | The **code file** in this repository plays a crucial role in utilizing the **FEDOT** framework, which is aimed at enabling streamlined development of **automated machine learning workflows**. It focuses on providing a **comprehensive set of APIs** for building and executing machine learning pipelines, along with **core functionalities** for model interpretation and preprocessing. By leveraging this code, users can easily develop and deploy **complex AI models** using a **structured and intuitive approach**, enhancing productivity and model explainability within their projects.This component serves as a cornerstone for **integrating advanced ML capabilities** into applications by abstracting complex ML concepts into **simple and reusable components**. Additionally, it facilitates seamless **handling of data preprocessing tasks** and offers **tools for model explainability**, empowering developers to create **robust and interpretable AI solutions** efficiently. |
| [data_definition.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/data_definition.py) | Fedot/core/composer/random_composer.py`**The `random_composer.py` file in the `fedot/core/composer` directory plays a crucial role in the `FEDOT` repositorys architecture by facilitating the creation of random composite models. This code file is essential for the generation of diverse and unique model structures within the framework, enabling experimentation and innovation in model design. Its functionality significantly contributes to the flexibility and adaptability of the repository's ML model composition capabilities. |
| [params.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/params.py) | This code file in the FEDOT repository plays a crucial role in managing the core functionalities and workflows of the open-source project. It orchestrates the interactions between various modules such as API, core algorithms, explainability tools, preprocessing, and structural analysis components. By providing the necessary structure and utilities, this code enables the seamless integration of different components and empowers users to build and execute machine learning workflows efficiently within the FEDOT framework. |

</details>

<details closed><summary>fedot.api.api_utils.assumptions</summary>

| File | Summary |
| --- | --- |
| [assumptions_builder.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/assumptions/assumptions_builder.py) | This code file within the FEDOT repository serves to provide essential utilities and functionalities for the core functionality of the project. It plays a crucial role in enabling seamless data preprocessing and structural analysis, ultimately enhancing the overall performance and efficiency of the automated machine learning workflows implemented within the repository. |
| [task_assumptions.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/assumptions/task_assumptions.py) | This code file in the parent repository `FEDOT` is crucial for managing the core functionalities related to data preprocessing within the machine learning workflow. It enables the seamless integration of diverse data sources and ensures standardized formatting for efficient model training and evaluation. By abstracting complex data manipulation tasks, it empowers developers to focus on building robust machine learning pipelines with minimal overhead. |
| [preprocessing_builder.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/assumptions/preprocessing_builder.py) | This code file in the `FEDOT` repository plays a crucial role in defining the fundamental structures and functionalities of the project. It contributes to the core architecture by providing essential API endpoints, structural analysis tools, explainability features, and various utility functions. Its primary purpose is to enable the seamless integration of machine learning workflows and data preprocessing tasks within the FEDOT framework. |
| [operations_filter.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/assumptions/operations_filter.py) | Filters and samples operations in a pipeline based on predefined lists, ensuring selected choices meet defined criteria. |
| [assumptions_handler.py](https://github.com/aimclub/FEDOT/blob/main/fedot/api/api_utils/assumptions/assumptions_handler.py) | This code file in the FEDOT repository plays a crucial role in enabling remote execution of machine learning workflows. It allows users to leverage computational resources efficiently by scheduling and monitoring their tasks remotely. This feature enhances the scalability and flexibility of the framework, empowering users to execute complex experiments without being constrained by local computational limitations. |

</details>

<details closed><summary>fedot.remote</summary>

| File | Summary |
| --- | --- |
| [pipeline_run_config.py](https://github.com/aimclub/FEDOT/blob/main/fedot/remote/pipeline_run_config.py) | This code file in the `FEDOT` repository plays a crucial role in enabling seamless communication between different components of the system. It facilitates the transfer of data and instructions among various modules, ensuring efficient coordination and interaction within the software architecture. By managing the inter-module connections, this code enhances the overall functionality and performance of the system, enabling smooth operation and collaboration among diverse features and functionalities. |
| [remote_evaluator.py](https://github.com/aimclub/FEDOT/blob/main/fedot/remote/remote_evaluator.py) | This code file within the FEDOT repository serves the critical function of providing API functionalities for the framework. It enables seamless integration with external systems and allows easy access to the core features of FEDOT, facilitating the construction and analysis of machine learning pipelines. This pivotal component aligns with the repositorys architecture by encapsulating essential functions within the API module, contributing to the overall modularity and extensibility of the framework. |
| [remote_run_dockerfile](https://github.com/aimclub/FEDOT/blob/main/fedot/remote/remote_run_dockerfile) | Enables running FEDOT within a container by configuring the base image. Installs Python dependencies, sets up the working directory, and defines the entry point for executing the pipeline with specified configurations. |
| [run_pipeline.py](https://github.com/aimclub/FEDOT/blob/main/fedot/remote/run_pipeline.py) | This code file in the FEDOT repository plays a crucial role in enabling advanced data processing and analysis within the framework. It facilitates seamless integration of various machine learning models for efficient model training and prediction tasks. By leveraging this code, developers can easily construct automated workflows, analyze model structures, and ensure transparency in model decision-making processes. Overall, this code file enhances the capabilities of the FEDOT framework by providing essential functionalities for building robust and interpretable machine learning pipelines. |

</details>

<details closed><summary>fedot.remote.infrastructure.clients</summary>

| File | Summary |
| --- | --- |
| [client.py](https://github.com/aimclub/FEDOT/blob/main/fedot/remote/infrastructure/clients/client.py) | Defines a base class for remote evaluation client, facilitating fitting pipelines in an external system. Handles connection and task execution parameters, along with downloading fitted pipelines. Subclasses implement methods for creating tasks, waiting, and retrieving results. |
| [test_client.py](https://github.com/aimclub/FEDOT/blob/main/fedot/remote/infrastructure/clients/test_client.py) | Implements remote client for executing pipelines and retrieving results. Manages connection and execution parameters, output path, task creation, monitoring readiness, and downloading results. |
| [datamall_client.py](https://github.com/aimclub/FEDOT/blob/main/fedot/remote/infrastructure/clients/datamall_client.py) | This code file in the `FEDOT` repository serves the critical function of providing essential utility functions to support various aspects of the framework. It enhances the core functionality by offering key tools for data preprocessing, structural analysis, and model explainability. These utilities play a pivotal role in ensuring the seamless operation of the machine learning workflows facilitated by the repository, contributing significantly to the overall effectiveness and versatility of the framework. |

</details>

<details closed><summary>other_requirements</summary>

| File | Summary |
| --- | --- |
| [profilers.txt](https://github.com/aimclub/FEDOT/blob/main/other_requirements/profilers.txt) | Profiles code execution and memory usage. Includes tools like snakeviz and gprof2dot for time profiling, objgraph and memory_profiler for memory profiling. |
| [docs.txt](https://github.com/aimclub/FEDOT/blob/main/other_requirements/docs.txt) | Facilitates documentation generation with Sphinx, including custom directives and themes. Enhances readability and searchability of project documentation. |
| [examples.txt](https://github.com/aimclub/FEDOT/blob/main/other_requirements/examples.txt) | Lists additional AutoML and data-related dependencies for the FEDOT repository. |
| [extra.txt](https://github.com/aimclub/FEDOT/blob/main/other_requirements/extra.txt) | Specifies extra dependencies for DNNs, images, texts, and topological features. Enhances functionality with libraries such as TensorFlow, Torch, OpenCV, Gensim, and Giottotda. Organizes essential requirements for advanced project functionalities. |

</details>

<details closed><summary>test</summary>

| File | Summary |
| --- | --- |
| [conftest.py](https://github.com/aimclub/FEDOT/blob/main/test/conftest.py) | Sets up caching mechanism for pipeline operations and preprocessing in test runs to prevent data leakage and ensure repeatability of results by setting a fixed random seed. |
| [test_gpu_strategy.py](https://github.com/aimclub/FEDOT/blob/main/test/test_gpu_strategy.py) | Implements GPU evaluation and prediction strategies using CuML for classification. Tests fitting and predicting operations with synthetic data, asserting correct outputs. |

</details>

<details closed><summary>test.integration</summary>

| File | Summary |
| --- | --- |
| [test_profiler.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/test_profiler.py) | Profiles code execution with time and memory profilers, ensuring requirements are met. Deletes temporary files before and after tests. Supports accurate performance analysis and debugging within the FEDOT repositorys architecture. |

</details>

<details closed><summary>test.integration.quality</summary>

| File | Summary |
| --- | --- |
| [test_synthetic_tasks.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/quality/test_synthetic_tasks.py) | This code file in the `FEDOT` repository serves the purpose of providing essential utilities for the core functionality of the framework. Its critical features include API endpoints, core algorithms, explainability tools, preprocessing functions, remote execution capabilities, and structural analysis methods. These utilities play a crucial role in enabling the overall functionality and usability of the `FEDOT` framework for various machine learning tasks and workflows. |
| [test_quality_improvement.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/quality/test_quality_improvement.py) | This code file in the `FEDOT` repository plays a crucial role in enabling advanced data processing and model building workflows. By utilizing the functionalities provided in this file, users can effectively design, optimize, and analyze complex machine learning pipelines. This contributes significantly to the repositorys overarching goal of empowering developers to create robust and adaptable predictive models for various real-world applications. |

</details>

<details closed><summary>test.integration.preprocessing</summary>

| File | Summary |
| --- | --- |
| [test_pipeline_preprocessing.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/preprocessing/test_pipeline_preprocessing.py) | This code file in the `FEDOT` repository serves a critical role by providing essential functionalities for building, executing, and evaluating automated machine learning workflows. It plays a key part in the parent repositorys architecture, enabling users to create sophisticated ML pipelines with ease. The code enhances the flexibility and usability of the repository, empowering developers to leverage advanced automation capabilities efficiently. |

</details>

<details closed><summary>test.integration.api_params</summary>

| File | Summary |
| --- | --- |
| [test_main_api_params.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/api_params/test_main_api_params.py) | Repository StructureWithin the `FEDOT/examples` directory, the code file `project_import_export.py` plays a critical role in showcasing the seamless import and export functionality of machine learning projects within the parent repositorys architecture. This code file demonstrates the effortless transfer of models and data pipelines, highlighting the versatility and robustness of the project management capabilities provided by the repository's frameworks. |

</details>

<details closed><summary>test.integration.data_operations</summary>

| File | Summary |
| --- | --- |
| [test_text_preprocessing.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/data_operations/test_text_preprocessing.py) | Tests the text preprocessing pipeline functionality within the repositorys integration suite. Verifies text cleaning on a sample dataset for a classification task, ensuring the output length matches the input. |

</details>

<details closed><summary>test.integration.real_applications</summary>

| File | Summary |
| --- | --- |
| [test_examples.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/real_applications/test_examples.py) | Feature_engineering.py`This code file within the `FEDOT` repository plays a critical role in enhancing the performance of machine learning models by automating feature engineering. By leveraging this module, developers can effortlessly extract valuable insights from raw data, empowering models to make more accurate predictions. This feature seamlessly integrates into the parent repositorys architecture, emphasizing the importance of optimizing data representation to drive superior model outcomes. |
| [test_real_cases.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/real_applications/test_real_cases.py) | This code file in the FEDOT repository serves the critical function of defining the core functionalities and APIs for the FEDOT framework. It encapsulates key features for data processing, model structuring, and result interpretation within the ecosystem. This module plays a pivotal role in enabling users to build, evaluate, and deploy machine learning pipelines efficiently using FEDOTs capabilities. |
| [test_model_result_reproducing.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/real_applications/test_model_result_reproducing.py) | This code file in the FEDOT repository serves the critical function of providing a high-level API for interacting with the core functionality of the FEDOT framework. It abstracts complex processes such as model building, data preprocessing, and structural analysis, making it easier for users to create and manipulate machine learning workflows. Its key features include enabling the creation and customization of pipelines for data processing and predictive modeling, facilitating easy experimentation with different algorithms and hyperparameters, and supporting model explainability through intuitive interfaces. |
| [test_heavy_models.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/real_applications/test_heavy_models.py) | Tests time series forecasting with deep learning models using a specified pipeline and custom function. Validates model predictions against test data, ensuring non-null output and correct prediction length. |

</details>

<details closed><summary>test.integration.utilities</summary>

| File | Summary |
| --- | --- |
| [test_pipeline_import_export.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/utilities/test_pipeline_import_export.py) | This code file within the FEDOT repository serves as a crucial component for enabling remote model deployment and inference functionality. It allows users to interact with trained models on external servers, facilitating seamless integration of machine learning models into production systems. |
| [test_project_import_export.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/utilities/test_project_import_export.py) | This code file in the `FEDOT` repository is designed to provide essential functionalities for handling data preprocessing within the machine learning workflow. It plays a crucial role in ensuring that input data is properly formatted and optimized for subsequent model training and evaluation processes. By incorporating this code, users can streamline their data preparation tasks effectively, enhancing the overall efficiency and accuracy of their machine learning projects within the repositorys architecture. |

</details>

<details closed><summary>test.integration.multimodal</summary>

| File | Summary |
| --- | --- |
| [test_multimodal.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/multimodal/test_multimodal.py) | The code file in the parent repository FEDOT contributes essential functionality to the open-source project. It plays a crucial role in enabling the creation of complex machine learning workflows with a focus on automation and efficiency. This code enhances the capabilities of the project by facilitating the seamless integration of various data preprocessing techniques and structural analysis methods. Its core purpose lies in empowering users to build and customize machine learning pipelines effectively for diverse applications. |

</details>

<details closed><summary>test.integration.models</summary>

| File | Summary |
| --- | --- |
| [test_atomized_model.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/models/test_atomized_model.py) | This code file in the `FEDOT` repository contributes to the core functionality of the project by providing essential APIs, core functionalities, explainability tools, preprocessing capabilities, and utilities. It plays a crucial role in enabling users to build, analyze, and interpret machine learning workflows efficiently within the broader architecture of the repository. |
| [test_model.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/models/test_model.py) | This code file within the FEDOT repository serves to enhance the explainability of machine learning models created using the FEDOT framework. By providing intuitive visualizations and insights into the models decision-making process, it empowers users to better understand and interpret the models predictions. This feature strengthens the overall transparency and trustworthiness of machine learning applications developed with FEDOT. |
| [test_strategy.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/models/test_strategy.py) | This code file in the `FEDOT` repository plays a critical role in enabling advanced data processing and model building functionalities within the project. It provides essential APIs and core functionalities for creating and analyzing complex machine learning workflows. This code file enhances the projects capabilities in handling diverse data sources and optimizing model performance, contributing significantly to the overall flexibility and effectiveness of the repositorys architecture. |
| [test_models_params.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/models/test_models_params.py) | Automl.py`The `automl.py` code file in the `FEDOT` repository is a critical component that enables automated machine learning (AutoML) capabilities. This file implements algorithms and processes for automating the machine learning workflow, from data preprocessing to model selection and optimization. By leveraging this code, users can easily build and deploy machine learning pipelines without requiring extensive manual intervention. This functionality aligns with the overarching goal of the `FEDOT` repository, which aims to provide a user-friendly framework for developing and deploying machine learning solutions efficiently. |
| [test_custom_model_introduction.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/models/test_custom_model_introduction.py) | This code file in the `FEDOT` repository contributes to the core functionality of the project by implementing key features for building, analyzing, and optimizing automated machine learning workflows. It plays a crucial role in enabling users to develop and deploy complex machine learning pipelines efficiently. |
| [test_split_train_test.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/models/test_split_train_test.py) | The code file in question serves as a key component within the FEDOT repositorys architecture. It plays a crucial role in enabling advanced data processing and machine learning workflows. By leveraging this code, users can effectively build, analyze, and optimize complex machine learning models. This functionality is essential for empowering developers to craft robust, data-driven solutions using the FEDOT framework. |
| [test_repository.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/models/test_repository.py) | This code file within the FEDOT repository plays a crucial role in enabling advanced machine learning workflows for time series forecasting and other predictive analytics tasks. It provides high-level APIs and core functionalities to build complex models efficiently. By leveraging this code, developers can streamline the process of data preprocessing, structural analysis, and model explainability within their projects. Overall, this code serves as a fundamental component for integrating sophisticated machine learning capabilities into various applications using FEDOTs open-source framework. |

</details>

<details closed><summary>test.integration.cache</summary>

| File | Summary |
| --- | --- |
| [test_cache_parallel.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/cache/test_cache_parallel.py) | This code file in the FEDOT repository plays a critical role in enabling open-source contributors to create and manage workflows within the FEDOT framework. It facilitates the orchestration of various tasks and modules to streamline the development and deployment of machine learning models. By encapsulating workflow management logic, this code enhances the scalability and modularity of the repository's architecture, promoting collaboration and innovation among users. |

</details>

<details closed><summary>test.integration.automl</summary>

| File | Summary |
| --- | --- |
| [test_automl.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/automl/test_automl.py) | Tests H2O and Fedot automl example pipeline evaluations. Uses OperationTypesRepository for automl setup. |

</details>

<details closed><summary>test.integration.optimizer</summary>

| File | Summary |
| --- | --- |
| [test_evaluation.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/optimizer/test_evaluation.py) | This code file in the `FEDOT` repository serves as a critical component for enabling explainability within the framework. It enhances the interpretability of machine learning models generated by FEDOT, allowing users to gain insights into the decision-making process behind the model predictions. By integrating this feature, the code promotes transparency and trust in the AI models created using the FEDOT framework. |

</details>

<details closed><summary>test.integration.composer</summary>

| File | Summary |
| --- | --- |
| [test_history.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/composer/test_history.py) | Auto_ml_pipeline.py`The `auto_ml_pipeline.py` file in the `FEDOT` repository plays a crucial role in automating machine learning pipelines. It enables users to effortlessly create and optimize complex pipelines for their data analysis tasks. This code file abstracts away the complexities of manual pipeline construction, allowing users to focus on high-level pipeline design and optimization. Its functionality significantly enhances the efficiency and effectiveness of machine learning workflows within the parent repositorys architecture. |
| [test_composer.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/composer/test_composer.py) | The code file in this repositorys `FEDOT/examples` directory showcases practical demonstrations of utilizing the FEDOT framework for advanced and simple machine learning workflows. It offers insightful guidance on importing/exporting projects, handling real-world cases, and implementing basic tasks. These examples serve as valuable resources for users looking to leverage FEDOTs capabilities effectively within their projects. |

</details>

<details closed><summary>test.integration.classification</summary>

| File | Summary |
| --- | --- |
| [test_classification.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/classification/test_classification.py) | This code file in the `FEDOT` repository contributes to the core functionality of the project. It plays a vital role in executing machine learning workflows and managing pipelines for automated model building and optimization. The file integrates various modules and utilities to enable efficient data preprocessing, structural analysis, and model explainability within the framework. |

</details>

<details closed><summary>test.integration.api</summary>

| File | Summary |
| --- | --- |
| [test_api_cli_params.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/api/test_api_cli_params.py) | Imitates argparse API call and tests all CLI parameters against the API in `test_api_cli_params.py`. Parses command-line arguments, separates parameters for Fedot, preprocesses keys, and runs Fedot for time series forecasting and classification tasks. |
| [test_main_api.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/api/test_main_api.py) | The code file in this repository under `FEDOT/examples/project_import_export.py` showcases how to efficiently import and export machine learning projects using the FEDOT framework. This functionality is crucial for seamless collaboration and sharing of ML workflows among team members. It enables users to package and transport their projects easily, fostering a more streamlined and collaborative development process within the repositorys architecture. |
| [test_api_utils.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/api/test_api_utils.py) | Optimization.py`The `optimization.py` file in the `FEDOT` repository plays a crucial role in improving the performance of models developed within the framework. It leverages advanced optimization techniques to fine-tune model parameters and enhance predictive accuracy. By integrating cutting-edge optimization algorithms, this code file elevates the overall efficiency and effectiveness of machine learning workflows in `FEDOT`. |
| [test_api_info.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/api/test_api_info.py) | Generates and displays essential modeling and data operations information for regression, classification, clustering, and time series forecasting tasks within the FEDOT API. Verifies correct API help functionality by confirming the presence of specific models for regression and classification tasks. |

</details>

<details closed><summary>test.integration.pipelines.tuning</summary>

| File | Summary |
| --- | --- |
| [test_pipeline_tuning.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/pipelines/tuning/test_pipeline_tuning.py) | This code file in the `FEDOT` repository plays a critical role in orchestrating data preprocessing and feature engineering for machine learning workflows. By providing a streamlined interface for data manipulation, it empowers users to efficiently prepare their datasets for model training and evaluation within the broader framework of the repositorys machine learning pipeline architecture. |
| [test_tuner_builder.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/pipelines/tuning/test_tuner_builder.py) | This code file in the `FEDOT` repository plays a crucial role in enabling advanced data processing and modeling capabilities. It empowers users to create complex machine learning workflows through intuitive APIs and tools provided by the parent repository. This code file showcases the core functionalities related to data preprocessing, model explainability, and structural analysis, reflecting the projects commitment to delivering a comprehensive solution for developing and deploying machine learning models. |

</details>

<details closed><summary>test.integration.validation</summary>

| File | Summary |
| --- | --- |
| [test_table_cv.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/validation/test_table_cv.py) | Demonstrates composing pipelines with cross-validation optimization, focusing on classification metrics like ROCAUC, accuracy, and log-loss. Validates pipeline performance using sklearn metrics within the Fedot repositorys architecture. |

</details>

<details closed><summary>test.integration.remote</summary>

| File | Summary |
| --- | --- |
| [test_remote_composer.py](https://github.com/aimclub/FEDOT/blob/main/test/integration/remote/test_remote_composer.py) | This code file in the parent repository FEDOT serves the critical purpose of providing functionality for remote execution of machine learning pipelines. It enables users to trigger the execution of complex workflows on remote servers, facilitating distributed computing and efficient resource utilization. |

</details>

<details closed><summary>test.sensitivity</summary>

| File | Summary |
| --- | --- |
| [test_sensitivity.py](https://github.com/aimclub/FEDOT/blob/main/test/sensitivity/test_sensitivity.py) | Implements sensitivity analysis for a pipelines hyperparameters. Uses mock data and tests the analysis methods functionality. |

</details>

<details closed><summary>test.unit</summary>

| File | Summary |
| --- | --- |
| [common_tests.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/common_tests.py) | Ensures predictive consistency for model robustness. |
| [test_utils.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/test_utils.py) | Tests `default_fedot_data_dir`, `labels_to_dummy_probs`, and `save_file_to_csv`. Ensures data directory creation, converts labels to dummy probabilities, and saves a DataFrame to CSV, testing the functionality of core utility functions. |

</details>

<details closed><summary>test.unit.preprocessing</summary>

| File | Summary |
| --- | --- |
| [test_pipeline_preprocessing.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/preprocessing/test_pipeline_preprocessing.py) | Fedot/core/data/input_data.py`This code file in the `FEDOT` repositorys `core` module serves a crucial role in managing input data for various machine learning tasks. It encapsulates functionality to handle data loading, preprocessing, and transformation, ensuring seamless data integration for downstream processes within the framework. By abstracting these data operations into a dedicated component, it promotes modularity and scalability in the system architecture, enhancing the overall flexibility and maintainability of the ML workflows implemented using the `FEDOT` framework. |
| [test_preprocessors.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/preprocessing/test_preprocessors.py) | This code file in the `FEDOT` repository plays a critical role in managing data preprocessing for machine learning models. It provides essential functionalities for cleaning, transforming, and preparing raw data to be suitable for input into the machine learning pipelines defined in the parent repository. By handling these preprocessing tasks efficiently, this code file ensures that the models built using the `FEDOT` framework can work with high-quality data, ultimately leading to more accurate predictions and insights. |
| [test_preprocessing_through_api.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/preprocessing/test_preprocessing_through_api.py) | The code file in question serves the critical function of defining the core functionality and services offered by the FEDOT repository. It plays a key role in orchestrating various components such as API interactions, core algorithms, explainability features, preprocessing steps, remote services, structural analysis, and utilities. This code file essentially encapsulates the essence of the FEDOT project and provides a comprehensive overview of its capabilities and offerings within the machine learning domain. |

</details>

<details closed><summary>test.unit.explainability</summary>

| File | Summary |
| --- | --- |
| [test_pipeline_explanation.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/explainability/test_pipeline_explanation.py) | Fedot/api/make_prediction.py`This code file in the `fedot` repositorys `api` module serves a critical role in enabling users to make predictions using the FEDOT framework. By providing a streamlined interface for invoking prediction functionalities, this file abstracts complex prediction logic and facilitates seamless integration of machine learning models. Its purpose is pivotal in simplifying the prediction process and enhancing the usability of the framework for end-users. |

</details>

<details closed><summary>test.unit.adapter</summary>

| File | Summary |
| --- | --- |
| [test_adapt_verification_rules.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/adapter/test_adapt_verification_rules.py) | Verifies pipeline rules behavior when adapting with an innovative adapter. Tests rules for task operations, primary nodes, data flow conflicts, and data connections correctness. Ensures rules compatibility with both optimized graphs and pipelines. |
| [test_adapt_pipeline.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/adapter/test_adapt_pipeline.py) | This code file in the `FEDOT` repository plays a crucial role in enabling efficient data preprocessing for machine learning workflows. It empowers users to seamlessly clean, transform, and manipulate raw data before feeding it into the AI models. By providing a suite of preprocessing functionalities, this code promotes data quality and enhances the overall predictive performance of the models developed using the parent repositorys architecture. |

</details>

<details closed><summary>test.unit.data_operations</summary>

| File | Summary |
| --- | --- |
| [test_data_operation_params.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/data_operations/test_data_operation_params.py) | This code file in the `FEDOT/examples` directory showcases practical implementations using the FEDOT framework. It serves as a demonstration of utilizing the core functionalities to build and analyze machine learning pipelines for both simple and advanced scenarios. The examples provided here illustrate the flexibility and efficiency of the FEDOT library in solving real-world problems through structured workflows and data manipulation. |
| [test_time_series_operations.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/data_operations/test_time_series_operations.py) | The code file in question plays a crucial role within the FEDOT repository by providing advanced functionality for importing and exporting projects. It enables seamless transfer of machine learning models and pipelines, facilitating collaboration and reproducibility across various projects and datasets. This feature enhances the overall usability and versatility of the FEDOT framework, making it easier for users to work with complex machine learning workflows efficiently. |
| [test_data_operations_implementations.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/data_operations/test_data_operations_implementations.py) | This code file within the FEDOT repository plays a crucial role in enabling advanced workflow management for the open-source project. It facilitates the creation, import, and export of predictive modeling projects, showcasing the flexibility and versatility of the framework. By providing these capabilities, the code empowers users to efficiently work with machine learning pipelines and experiment with different modeling approaches, contributing to the overall extensibility and usability of the FEDOT platform. |
| [test_data_definition.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/data_operations/test_data_definition.py) | This code file within the FEDOT repository is crucial for providing an intuitive API that allows users to interact with the core functionality of the FEDOT framework. By encapsulating key features and operations in an accessible manner, the code promotes ease of use and seamless integration with the frameworks machine learning capabilities. It serves as a gateway for developers to leverage FEDOTs advanced modeling and data preprocessing tools effectively within their projects. |

</details>

<details closed><summary>test.unit.tasks</summary>

| File | Summary |
| --- | --- |
| [test_multi_task.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/tasks/test_multi_task.py) | Verifies multi-task pipeline prediction accuracy by integrating classification and regression tasks. Handles complex data preprocessing and model fitting, ensuring correct label predictions for each task type. Maintains data source consistency and tracks feature dimensions throughout the pipeline structure. |
| [test_regression.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/tasks/test_regression.py) | This code file in the FEDOT repository serves the critical purpose of providing essential utility functions for various aspects of the framework, such as data preprocessing, model explainability, and structural analysis. It plays a key role in enabling the core functionalities of the FEDOT framework to operate effectively and efficiently. |
| [test_multi_ts_forecast.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/tasks/test_multi_ts_forecast.py) | This code file within the FEDOT repository serves as a core component responsible for orchestrating machine learning workflows. It provides functionality for composing, training, and evaluating complex machine learning pipelines tailored to specific use cases. By leveraging this code, users can efficiently experiment with various predictive modeling techniques and optimize the performance of their predictive tasks with ease. |
| [test_gapfilling.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/tasks/test_gapfilling.py) | This code file in the FEDOT repository plays a critical role in implementing advanced machine learning workflows using the FEDOT framework. It focuses on orchestrating the construction of complex pipelines for automated model building and optimization. The code enables seamless integration of custom data preprocessing, feature engineering, and algorithm selection, empowering users to create sophisticated machine learning solutions with ease. Overall, it enhances the repositorys architecture by providing a versatile and scalable approach to tackling diverse data science challenges. |
| [test_classification.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/tasks/test_classification.py) | This code file in the FEDOT repository serves the critical function of providing essential APIs for interacting with the core functionality of the FEDOT framework. Through these APIs, users can easily leverage the frameworks capabilities for building and analyzing automated machine learning pipelines. It acts as a gateway for developers to seamlessly integrate the powerful features of FEDOT into their projects, enabling efficient experimentation and deployment of machine learning solutions. |
| [test_clustering.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/tasks/test_clustering.py) | Tests clustering pipelines fit accuracy by generating synthetic data and assessing mean ROC AUC across multiple iterations. Validates clustering model performance with a defined threshold. |
| [test_forecasting.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/tasks/test_forecasting.py) | This code file in the FEDOT repository serves the critical purpose of providing a structured interface for interacting with machine learning workflows. It enables users to easily define, customize, and execute complex data processing and modeling pipelines. This functionality is essential for automating and optimizing the creation of machine learning solutions within the parent repositorys architecture. |

</details>

<details closed><summary>test.unit.utilities</summary>

| File | Summary |
| --- | --- |
| [window_size_selector.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/utilities/window_size_selector.py) | Validates window size selection criteria through randomized testing ensuring correct behavior with various parameters for robust algorithm testing. |
| [memory.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/utilities/memory.py) | Logs memory usage data while active and inactive. Captures additional info in active mode, with logged measures and assertion checks. Ensures no message is captured in the non-active state. |

</details>

<details closed><summary>test.unit.multimodal</summary>

| File | Summary |
| --- | --- |
| [data_generators.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/multimodal/data_generators.py) | This code file in the `FEDOT` repository serves the purpose of providing essential APIs for building and executing complex machine learning workflows using the FEDOT framework. It enables users to create custom data processing pipelines, define model structures, and analyze the performance and explainability of the generated models. The critical features include streamlined access to core functionalities, seamless integration with preprocessing tools, and the ability to interact with various remote services for distributed computing. |
| [test_multimodal.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/multimodal/test_multimodal.py) | This code file in the FEDOT repository serves the critical function of providing essential API functionalities for the FEDOT framework. It enables users to interact with the core features of the framework, facilitating the creation and management of complex machine learning pipelines. By interfacing with this code, users can leverage the power of FEDOT for developing advanced predictive models efficiently. |

</details>

<details closed><summary>test.unit.optimizer</summary>

| File | Summary |
| --- | --- |
| [test_external.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/optimizer/test_external.py) | Code File SummaryThe code file in question serves as a crucial component within the `FEDOT` repositorys architecture. It plays a key role in enabling advanced machine learning capabilities for building and deploying custom pipelines using the FEDOT framework. By leveraging this code, users can effortlessly create, evaluate, and optimize complex data processing workflows to enhance predictive modeling and streamline decision-making processes. |
| [test_tuner_timer.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/optimizer/test_tuner_timer.py) | Verifies the TunerTimer class performance by measuring the time spent executing a loop against a specified time limit. |
| [test_pipeline_objective_eval.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/optimizer/test_pipeline_objective_eval.py) | SummaryThis code file in the `FEDOT` repository plays a crucial role in enabling the creation and execution of advanced machine learning workflows using the FEDOT framework. It facilitates the seamless orchestration of complex data processing and modeling tasks, empowering developers to build robust predictive models efficiently. |

</details>

<details closed><summary>test.unit.optimizer.gp_operators</summary>

| File | Summary |
| --- | --- |
| [test_mutation.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/optimizer/gp_operators/test_mutation.py) | This code file in the `FEDOT` repository focuses on providing core functionalities for building and analyzing machine learning workflows through the `FEDOT` framework. It plays a crucial role in enabling users to construct complex data processing pipelines and gain insights into the structural composition of these workflows. The code supports the overarching goal of the repository, which is to empower developers with tools for creating robust and explainable machine learning models. |

</details>

<details closed><summary>test.unit.composer</summary>

| File | Summary |
| --- | --- |
| [test_metrics.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/composer/test_metrics.py) | This code file within the FEDOT repository facilitates the management and processing of data for machine learning workflows. It plays a pivotal role in orchestrating data preprocessing steps and ensuring the compatibility of input data with machine learning models. By handling data transformation and cleaning operations, this code promotes efficient and effective model training and evaluation within the broader architecture of the repository. |
| [test_mutation_params.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/composer/test_mutation_params.py) | Verifies hyperparameter modification behavior for lagged operations and alpha values correctness. Handles unknown operation scenarios gracefully. |

</details>

<details closed><summary>test.unit.api</summary>

| File | Summary |
| --- | --- |
| [test_presets.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/api/test_presets.py) | This code file in the FEDOT repository plays a crucial role in enabling advanced machine learning workflows for automated modeling. It provides essential functionalities for data preprocessing, model explanation, and structural analysis within the framework. By leveraging these features, users can build and deploy sophisticated machine learning pipelines efficiently and effectively. |
| [test_api_builder.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/api/test_api_builder.py) | This code file in the parent repository FEDOT plays a crucial role in providing functionalities for building and analyzing machine learning pipelines. It focuses on core operations such as data preprocessing, model interpretation, and structural analysis within the ML workflow. By leveraging the features in this code file, developers can efficiently construct and inspect complex ML pipelines for various tasks. |
| [test_main_api.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/api/test_main_api.py) | This code file in the FEDOT repository serves the critical purpose of providing remote functionality for the framework. It enables users to interact with FEDOTs core features from a remote location, enhancing collaboration and accessibility. This feature aligns with the repositorys architecture focused on democratizing AI solutions and fostering community engagement through open-source contributions. |
| [test_api_safety.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/api/test_api_safety.py) | This code file in the `FEDOT` repository plays a crucial role in enabling advanced data modeling and automation workflows. It provides essential APIs and utilities for core functionalities such as model building, preprocessing, explainability, and structural analysis. By leveraging this code, users can efficiently analyze and manipulate data for various machine learning tasks, making the repository a valuable resource for developing sophisticated data science solutions. |
| [test_assumption_builder.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/api/test_assumption_builder.py) | This code file in the FEDOT repository plays a crucial role in providing a set of utilities for various tasks within the framework. It contributes to the core functionalities of the project, enhancing the overall user experience and aiding in the smooth execution of machine learning workflows. |
| [test_api_params.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/api/test_api_params.py) | This code file in the `FEDOT` repository contributes to the projects core functionality. It plays a vital role in implementing and managing the workflow orchestration of the machine learning pipelines. By organizing the execution steps and data processing tasks, this code ensures efficient and effective model training and deployment processes. It significantly enhances the scalability and performance of the project by streamlining the end-to-end pipeline operations. |

</details>

<details closed><summary>test.unit.pipelines</summary>

| File | Summary |
| --- | --- |
| [test_pipeline_builder.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_pipeline_builder.py) | This code file within the FEDOT repository plays a crucial role in implementing advanced machine learning workflows for automated data modeling. It facilitates the creation of complex data pipelines by leveraging a wide range of algorithms and techniques. By abstracting the underlying complexities, it empowers users to build and deploy sophisticated machine learning models with ease. This code promotes modular design principles and extensibility, enabling seamless integration of custom components. In essence, it simplifies the process of developing effective machine learning solutions and fosters collaboration within the open-source community. |
| [test_node_cache.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_node_cache.py) | This code file in the `FEDOT` repositorys `fedot` module serves the critical purpose of providing core functionalities for the FEDOT framework. It plays a key role in enabling the implementation of machine learning workflows and structuring data preprocessing tasks. By leveraging this code, users can harness essential utilities for model explainability, remote computation, and structural analysis within the FEDOT ecosystem. |
| [test_pipeline_comparison.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_pipeline_comparison.py) | This code file in the parent repository FEDOT contributes to the core functionality of the project. It enhances the API of the FEDOT framework by providing critical features for data preprocessing, model interpretability, and structural analysis. By incorporating these features, the code file empowers users to streamline their data processing workflows, gain insights into model decision-making processes, and conduct in-depth analyses of model structures within the FEDOT ecosystem. |
| [test_pipeline_structure.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_pipeline_structure.py) | This code file in the `FEDOT` repository, specifically within the `fedot` package, focuses on providing essential functionalities for machine learning workflows. It plays a critical role in orchestrating data preprocessing, model building, explainability analysis, and remote data processing. By leveraging the core capabilities of the `fedot` package, users can efficiently design and analyze complex machine learning pipelines. |
| [test_operation_params.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_operation_params.py) | Tests operation parameters updating and retrieval. Verifies updated parameters match expected values. Validates retrieval of specific parameters with optional default values. |
| [test_decompose_pipelines.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_decompose_pipelines.py) | Code File SummaryThis code file in the FEDOT repository plays a crucial role in enabling advanced machine learning workflows and automation. It empowers users to build and optimize complex pipelines for data processing and modeling effortlessly. By leveraging intuitive APIs and powerful core functionalities, this code fosters seamless integration of different data sources, model structures, and analysis methods. Its key features include enhancing explainability, streamlining preprocessing tasks, conducting structural analysis, and providing utilities for efficient workflow management. Ultimately, this code file encapsulates the essence of democratizing machine learning through open-source collaboration and innovation within the FEDOT ecosystem. |
| [test_pipeline.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_pipeline.py) | This code file in the `FEDOT` repository plays a crucial role in enabling customizable feature generation within the framework. By implementing a flexible and extensible feature engineering module, it empowers users to efficiently create and incorporate domain-specific features into their machine learning workflows. This capability aligns with the repositorys focus on democratizing machine learning by providing a comprehensive set of tools and functionalities for building and deploying predictive models. |
| [test_node.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_node.py) | This code file in the `FEDOT` repository plays a critical role in enabling advanced machine learning workflows through its innovative API features. By providing a user-friendly interface to interact with the core functionalities of the repository, it empowers developers to effortlessly build, analyze, and optimize complex models for various tasks. Through this code, users can leverage the full potential of the underlying machine learning capabilities, driving impactful and efficient data-driven solutions. |
| [test_pipeline_parameters.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_pipeline_parameters.py) | Tests if time series forecasting pipeline parameters are correctly changed and updated. Verifies content, custom parameters, and descriptive ID alignment after parameter modification. Validates adherence to new parameter values for the pipeline. |
| [test_pipeline_ts_wrappers.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_pipeline_ts_wrappers.py) | Code File SummaryThe code file in question plays a crucial role in enabling advanced data processing capabilities within the FEDOT repository. It provides key functionalities for creating, managing, and optimizing machine learning workflows. By leveraging this code, users can easily design and execute complex data pipelines, empowering seamless experimentation and iteration in data analysis tasks. This component serves as a cornerstone for driving efficient data processing workflows and enhancing the overall functionality of the repository architecture. |
| [test_pipeline_node_factory.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_pipeline_node_factory.py) | This code file in the `FEDOT` repository plays a critical role in enabling the integration of external data sources with the framework. By implementing a flexible data import and export functionality, it empowers users to seamlessly work with diverse datasets, enhancing the adaptability and usability of the overall system. |
| [test_reproducibility.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_reproducibility.py) | Ensures the reproducibility of pipeline evaluations by validating identical results with fixed random seeds using the Fedot framework. Test script verifies consistency in prediction outcomes after sequential pipeline fits and predicts, emphasizing result uniformity. |
| [test_pipeline_verification.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/test_pipeline_verification.py) | The code file in this repository under `FEDOT/fedot/api` serves as a crucial component within the parent projects architecture. It facilitates the interaction with various functionalities and services provided by the core system. This code contributes to the overarching goal of enabling users to easily access and utilize the core features of the project through a well-defined and accessible interface. |

</details>

<details closed><summary>test.unit.pipelines.prediction_intervals</summary>

| File | Summary |
| --- | --- |
| [test_prediction_intervals.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/prediction_intervals/test_prediction_intervals.py) | The code file in this repository under `FEDOT/examples/advanced/` serves the purpose of showcasing complex implementation scenarios and advanced usage of the FEDOT framework. It exhibits how to leverage the core functionalities in intricate setups, providing insight into sophisticated data processing and modeling techniques. This code file contributes to the repositorys architecture by demonstrating real-world applications and guiding users on optimizing performance and accuracy through advanced workflows. |
| [test_solver_mutations.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/prediction_intervals/test_solver_mutations.py) | This code file in the FEDOT repository contributes to the core functionality of the open-source project. It enables users to perform advanced data processing and model building tasks with ease. The critical features include API integration, core algorithms, explainability tools, remote execution capabilities, preprocessing functions, and structural analysis utilities. By leveraging this code, developers can efficiently analyze and create complex machine learning workflows within the FEDOT framework. |
| [test_mutations.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/pipelines/prediction_intervals/test_mutations.py) | Verifies uniqueness among mutations in prediction intervals pipelines through distance comparison. Tests mutation generation and ensures distinct structures by leveraging graph distance calculations. |

</details>

<details closed><summary>test.unit.dag</summary>

| File | Summary |
| --- | --- |
| [test_graph_operator.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/dag/test_graph_operator.py) | Tests ensure proper processing of Pipeline and OptNodes in a graph. The functions test node connections and type handling. Post-processing method validates node types for correct functionality. |
| [test_graph_utils.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/dag/test_graph_utils.py) | Implements functions for comparing graph nodes and graphs within the DAG module, facilitating node and graph comparisons. Supports finding identical nodes, checking if graphs are the same, and locating specific nodes within a graph based on predefined criteria. |

</details>

<details closed><summary>test.unit.validation</summary>

| File | Summary |
| --- | --- |
| [test_table_cv.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/validation/test_table_cv.py) | Auto_ml_pipeline.py`This code file in the `FEDOT` repository focuses on creating an automated machine learning pipeline for solving complex problems. It leverages the core functionalities of `FEDOT` to streamline the process of model building, optimization, and evaluation. By encapsulating key ML operations, this file enables users to efficiently construct and fine-tune predictive models, leading to enhanced automation and productivity within the ML workflow of the parent repository. |
| [test_time_series_cv.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/validation/test_time_series_cv.py) | This code file in the `FEDOT` repository plays a crucial role in facilitating the explainability of machine learning models developed using the FEDOT framework. By incorporating transparency into the decision-making process of these models, this code contributes significantly to enhancing trust and understanding of the model predictions. |

</details>

<details closed><summary>test.unit.remote</summary>

| File | Summary |
| --- | --- |
| [test_remote_run.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/remote/test_remote_run.py) | Tests remote pipeline fitting with different data types using a RemoteEvaluator in local mode. FitPipeline method executes classification, time series, and multivariate time series tasks with specified configurations, verifying successful completion. |
| [test_remote_custom.py](https://github.com/aimclub/FEDOT/blob/main/test/unit/remote/test_remote_custom.py) | Code File SummaryThis code file in the `FEDOT` repository plays a crucial role in orchestrating the core functionalities of the system. It focuses on managing the end-to-end workflow design and execution processes, providing users with essential tools to define, optimize, and interpret machine learning pipelines. By leveraging this code, developers can effectively harness the power of automated modeling and streamline the experimentation lifecycle within the repositorys architecture. |

</details>

<details closed><summary>examples</summary>

| File | Summary |
| --- | --- |
| [README.rst](https://github.com/aimclub/FEDOT/blob/main/examples/README.rst) | Introduces FEDOT examples for new and advanced users, showcasing basic and advanced tasks like classification, regression, time series forecasting, and interpretability, along with compatibility with other autoML solutions and remote execution capabilities. |
| [project_import_export.py](https://github.com/aimclub/FEDOT/blob/main/examples/project_import_export.py) | Manages exporting/importing ML projects as ZIP files for reproducibility. Retrieves data paths, trains a pipeline, and evaluates it using ROC AUC. Facilitates saving and loading pipelines and data for seamless model sharing and reproducibility. |

</details>

<details closed><summary>examples.advanced</summary>

| File | Summary |
| --- | --- |
| [surrogate_optimization.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/surrogate_optimization.py) | Implements surrogate optimization for time series forecasting using a customized model and AutoML with Fedot. Generates in-sample forecasts and visualizations with tunable parameters and performance metrics, enhancing predictive capabilities for advanced forecasting tasks in the repository architecture. |
| [profiler_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/profiler_example.py) | Demonstrates profiling credit scoring problem with MemoryProfiler and TimeProfiler. Sets random seed, retrieves data paths, and profiles the problem utilizing memory and time profilers for performance analysis. |
| [multitask_classification_regression.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/multitask_classification_regression.py) | This code file in the `FEDOT` repository plays a crucial role in managing data preprocessing tasks for machine learning workflows. It provides essential functionality for cleaning, transforming, and preparing datasets before they are used in the core machine learning algorithms. By ensuring data quality and compatibility, this code contributes to the overall effectiveness and efficiency of the machine learning models developed using the repositorys architecture. |
| [evo_operators_comparison.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/evo_operators_comparison.py) | This code file in the `FEDOT` repository plays a crucial role in enabling users to define custom machine learning pipelines through a flexible and intuitive interface. By leveraging this code, developers can easily create, optimize, and deploy complex data processing and modeling workflows. The file empowers users to efficiently experiment with various algorithms and data transformations, ultimately fostering innovation and performance improvement within the machine learning domain. |
| [multimodal_text_num_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/multimodal_text_num_example.py) | This code file in the `FEDOT` repository serves the crucial purpose of providing a centralized interface for interacting with various core functionalities such as API services, data preprocessing, model explainability, and structural analysis. By encapsulating these features, it enables seamless integration and manipulation of data workflows, contributing to the repositorys overarching architecture aimed at enhancing machine learning model development and deployment processes. |
| [multi_modal_pipeline.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/multi_modal_pipeline.py) | The code file in this repository plays a crucial role in enabling the orchestration and management of machine learning workflows. It facilitates the streamlined construction and evaluation of complex models through automated processes. Its key contribution lies in optimizing the efficiency and performance of model development pipelines within the parent repositorys architecture. |
| [parallelization_comparison.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/parallelization_comparison.py) | Model_training.py`This code file within the `FEDOT` repository plays a crucial role in training machine learning models using the FEDOT framework. It leverages the core functionalities provided by the parent repository, enabling users to create and optimize complex models for various tasks.Key features include:-Initiating automated model training processes-Handling data preprocessing and feature engineering-Optimizing model architecture and hyperparameters-Facilitating the evaluation of model performance-Supporting seamless integration with FEDOT's explainability and structural analysis componentsBy encapsulating these key functionalities, `model_training.py` empowers users to efficiently build and fine-tune machine learning models within the broader ecosystem of the FEDOT repository. |
| [gpu_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/gpu_example.py) | The code file in the `fedot/api` directory serves as the entry point for external interactions with the FEDOT repository. Its primary function is to expose a set of high-level functions and classes that enable users to easily leverage the repositorys machine learning and data processing capabilities. This API component abstracts the underlying complexities, providing a user-friendly interface for integrating FEDOTs functionality into various projects and applications. |
| [multiobj_optimisation.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/multiobj_optimisation.py) | Demonstrates multi-objective optimization in classification using Fedot, showcasing model fitting, prediction, and visualization. Uses various metrics, seed setting, and specified data files for training and evaluation within the repositorys advanced examples structure. |
| [additional_learning.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/additional_learning.py) | The code file in this repository contributes to the core functionality of the FEDOT project by providing key components for data preprocessing, feature engineering, and model optimization. It plays a crucial role in enabling the construction and evaluation of machine learning pipelines for time series forecasting and other predictive modeling tasks within the FEDOT framework. |
| [pipeline_sensitivity.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/pipeline_sensitivity.py) | This code file in the `FEDOT` repository plays a crucial role in enabling advanced customization and execution of machine learning workflows using the FEDOT framework. It enhances the core functionality by providing an intuitive and flexible interface for users to define, optimize, and interpret complex machine learning pipelines. This contributes significantly to the repositorys goal of empowering users to efficiently build and deploy sophisticated machine learning models. |

</details>

<details closed><summary>examples.advanced.structural_analysis</summary>

| File | Summary |
| --- | --- |
| [complex_analysis_with_requirements.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/structural_analysis/complex_analysis_with_requirements.py) | Analyzes pipeline structure with deletion, node replacement, and hyperparameters sensitivity. Generates insights for improving machine learning models. |
| [structural_analysis_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/structural_analysis/structural_analysis_example.py) | Repository StructureWithin the `FEDOT/` repository, the `test_gpu_strategy.py` file in the `test/` directory serves a critical role in ensuring the performance and compatibility of the software with GPU strategies. It facilitates the validation of GPU-specific functionality, contributing to the overall robustness and efficiency of the system. |
| [pipelines_access.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/structural_analysis/pipelines_access.py) | This code file in the FEDOT repository plays a critical role in facilitating advanced feature engineering and modeling capabilities within the framework. It enables efficient data preprocessing, structural analysis, and model explainability, providing a robust foundation for building complex machine learning workflows. |
| [dataset_access.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/structural_analysis/dataset_access.py) | Define functions to retrieve scoring, KC2, and cholesterol datasets for model training & testing within the advanced structural analysis module. Utilizes tasks for classification & regression, splitting data for training. Path setup leverages the project root and csv files in the real_cases data directory. |

</details>

<details closed><summary>examples.advanced.fedot_based_solutions</summary>

| File | Summary |
| --- | --- |
| [external_optimizer.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/fedot_based_solutions/external_optimizer.py) | Implements a custom external optimizer for Fedots AutoML with a random search algorithm. It specifies available operations and optimizes model performance for a classification task using real-case data. |

</details>

<details closed><summary>examples.advanced.remote_execution</summary>

| File | Summary |
| --- | --- |
| [ts_composer_with_integration.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/remote_execution/ts_composer_with_integration.py) | This code file in the FEDOT repository plays a crucial role in enabling advanced data analysis by providing a versatile framework for automating machine learning workflows. It facilitates the construction and evaluation of complex models, making it easier to extract insights from data sets. The code fosters collaboration and innovation by offering a unified interface for building, testing, and refining machine learning pipelines efficiently. |
| [remote_fit_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/remote_execution/remote_fit_example.py) | This code file in the `FEDOT/fedot` directory of the repository serves a crucial role in providing the core functionality for the project. It contributes to the API, core processing, explainability, preprocessing, remote functionality, structural analysis, and various utilities within the projects ecosystem. It plays a central part in enabling the high-level features and capabilities of the FEDOT framework, making it a key component of the repositorys architecture. |

</details>

<details closed><summary>examples.advanced.decompose</summary>

| File | Summary |
| --- | --- |
| [regression_refinement_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/decompose/regression_refinement_example.py) | This code file in the FEDOT repository plays a crucial role in enabling remote communication and collaboration for the FEDOT framework. It facilitates seamless interactions between distributed components, enhancing the scalability and efficiency of the system. By abstracting the complexities of remote functionality, this code promotes modularity and simplifies integration for developers working on remote-based features within FEDOT. |
| [refinement_forecast_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/decompose/refinement_forecast_example.py) | This code file in the `FEDOT` repository plays a crucial role in orchestrating the creation and management of machine learning pipelines. It enables users to define and execute complex workflows for predictive modeling tasks with ease. By encapsulating various data preprocessing, model building, and evaluation steps, this code empowers users to experiment with different algorithms and configurations efficiently. In the broader architecture of the repository, this code file serves as a centerpiece for building end-to-end machine learning solutions using a modular and extensible approach. |
| [classification_refinement_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/decompose/classification_refinement_example.py) | This code file in the FEDOT repository contributes to the parent architecture by implementing essential functionalities for creating and managing machine learning workflows. It enables users to define complex data processing pipelines for predictive modeling tasks. By utilizing this code, developers can seamlessly orchestrate the flow of data preprocessing, feature engineering, model training, and evaluation within the framework of the repository's machine learning infrastructure. |

</details>

<details closed><summary>examples.advanced.time_series_forecasting</summary>

| File | Summary |
| --- | --- |
| [composing_pipelines.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/time_series_forecasting/composing_pipelines.py) | This code file within the FEDOT repository contributes a key feature focused on enhancing the explainability of machine learning models. By providing methods to interpret and understand complex model outputs, it enriches the overall functionality of the repository, aligning with the core mission of promoting transparency and insights into model decision-making processes. This feature empowers users to gain deeper understanding and confidence in the models developed using the FEDOT framework. |
| [prediction_intervals.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/time_series_forecasting/prediction_intervals.py) | The code file in this repositorys `FEDOT/` directory provides essential functionality for managing and analyzing the structure of data pipelines within the `fedot` module. It plays a crucial role in facilitating the core operations of the parent repository, contributing to the seamless creation and evaluation of machine learning workflows. |
| [custom_model_tuning.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/time_series_forecasting/custom_model_tuning.py) | This code file within the FEDOT repository serves to provide essential functionality for structuring and analyzing data within the FEDOT framework. It contributes to the core features of the repository, supporting the development of machine learning workflows and enabling effective data preprocessing. The code plays a critical role in facilitating the overall functionality and utility of the FEDOT framework for users working on machine learning projects. |
| [sparse_lagged_tuning.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/time_series_forecasting/sparse_lagged_tuning.py) | This code file in the FEDOT repository plays a crucial role in providing functionality for structuring and analyzing data within the machine learning framework. It facilitates core operations related to data preprocessing, model explanation, and remote capabilities. The code contributes significantly to the architectures modularity and flexibility, enabling seamless integration of various machine learning components. |
| [nemo.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/time_series_forecasting/nemo.py) | The code file in the repositorys `FEDOT/` directory provides essential functions for building and managing machine learning workflows using the FEDOT framework. It enables users to create complex data processing pipelines efficiently. This code contributes to the core functionality of the project by facilitating the seamless orchestration of various data preprocessing and model training steps within the frameworks architecture. |
| [multistep.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/time_series_forecasting/multistep.py) | Auto_ml_pipeline.py`This code file in the `FEDOT` repository orchestrates an automated machine learning (AutoML) pipeline for building and optimizing predictive models. It integrates with various components in the `fedot` package, leveraging its AI capabilities to streamline model development. The file encapsulates logic for data preprocessing, model selection, hyperparameter tuning, and model evaluation, offering a comprehensive solution for automating the ML workflow. It plays a pivotal role in democratizing machine learning by empowering users to efficiently create high-performing models without deep expertise. |
| [exogenous.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/time_series_forecasting/exogenous.py) | This code file in the `FEDOT` repository plays a crucial role in enabling seamless interoperability between various components within the system. It facilitates efficient communication and data exchange protocols, ensuring smooth integration and collaboration among different modules. By providing a standardized interface for interaction, this code promotes modularity and enhances the overall flexibility of the system architecture. Its design empowers developers to easily extend functionality and incorporate new features with minimal friction, ultimately fostering a dynamic and robust ecosystem within the repository. |
| [nemo_multiple.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/time_series_forecasting/nemo_multiple.py) | This code file in the `FEDOT` repository is focused on providing core functionalities for the FEDOT framework. It plays a crucial role in handling data preprocessing, feature engineering, model structuring, and explainability within the framework. By leveraging this code, users can efficiently build, analyze, and interpret complex automated machine learning pipelines. It significantly contributes to the versatility and robustness of the FEDOT framework, enabling users to develop advanced machine learning solutions with ease. |
| [multi_ts_arctic_forecasting.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/time_series_forecasting/multi_ts_arctic_forecasting.py) | This code file in the FEDOT repository plays a crucial role in orchestrating the explanation generation process for machine learning models. It provides a clear and intuitive interface for users to interpret the decision-making logic behind model predictions. By leveraging this code, developers can enhance the transparency and trustworthiness of their models, fostering better understanding and adoption within the community. |

</details>

<details closed><summary>examples.advanced.automl</summary>

| File | Summary |
| --- | --- |
| [pipeline_from_automl.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/automl/pipeline_from_automl.py) | Executes AutoML pipeline with custom time limit, calculating ROC AUC metric from train and test data. Introduces pipeline nodes for data scaling, TPOT, LDA, and Random Forest operations. |
| [tpot_vs_fedot.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/automl/tpot_vs_fedot.py) | This code file in the FEDOT repository plays a crucial role in enabling advanced workflow management for creating and analyzing machine learning pipelines. It provides essential functionalities for orchestrating the execution and evaluation of complex ML models, contributing significantly to the projects overarching goal of facilitating efficient and effective ML experimentation. |
| [tpot_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/automl/tpot_example.py) | This code file within the `FEDOT` repository serves the critical purpose of enabling advanced project import and export functionalities. It facilitates the seamless transfer of projects between different environments within the repositorys architecture. |
| [h2o_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/advanced/automl/h2o_example.py) | The code file in the repositorys `FEDOT/examples` directory showcases usage scenarios and practical applications of the parent repositorys core functionalities. It offers real-world use cases, demonstrating how the features and capabilities of the repository can be leveraged to solve various problems. This code file serves as a valuable resource for developers looking to understand and implement the repository's tools in different contexts, providing insights into effective utilization and integration strategies. |

</details>

<details closed><summary>examples.simple</summary>

| File | Summary |
| --- | --- |
| [pipeline_import_export.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/pipeline_import_export.py) | Workflow.py`The `workflow.py` file in the `FEDOT` repository orchestrates end-to-end pipeline execution for complex machine learning tasks. It seamlessly integrates data preprocessing, model training, and result evaluation, providing a streamlined approach to building and assessing ML workflows. This critical component enhances collaboration and accelerates development by encapsulating best practices and promoting standardized workflows within the parent repositorys architecture. |
| [pipeline_visualization.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/pipeline_visualization.py) | The code file in question contains critical features that enable the orchestration and execution of machine learning workflows within the parent repositorys architecture. It plays a pivotal role in automating the data preprocessing, model selection, hyperparameter tuning, and model evaluation processes. This code ensures seamless integration with various APIs and facilitates explainability and structural analysis of the machine learning models generated. By encapsulating these essential functionalities, it empowers users to leverage the repositorys capabilities effectively for developing and deploying machine learning solutions. |
| [pipeline_tuning_with_iopt.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/pipeline_tuning_with_iopt.py) | This code file in the `FEDOT` repository serves the critical function of enabling advanced project import and export capabilities within the system. It allows for seamless integration of external data and models, facilitating efficient workflows for users working on real-world cases. By supporting these features, the code enhances the overall versatility and usability of the parent repositorys architecture. |
| [pipeline_log.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/pipeline_log.py) | Demonstrates setting up a logging framework for a classification pipeline. Initializes and configures logging settings, then creates and fits a pipeline using training data. |
| [pipeline_tune.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/pipeline_tune.py) | This code file in the FEDOT repository serves the critical function of providing a cohesive structure for various modules within the project. By organizing components such as APIs, core functionalities, explainability tools, preprocessing modules, and more, it ensures efficient development and maintenance of the machine learning workflow framework. |
| [pipeline_and_history_visualization.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/pipeline_and_history_visualization.py) | Visualize composing history and best pipeline using PipelineHistoryVisualizer. Load OptHistory, restore PipelineAdapter, and show visualizations including fitness line, fitness box, operations KDE, and animated bar chart. |

</details>

<details closed><summary>examples.simple.interpretable</summary>

| File | Summary |
| --- | --- |
| [api_explain.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/interpretable/api_explain.py) | Illustrate pipeline interpretation with a classification problem using explainability methods. Generates a visual explanation of a simple pipeline built with the Fedot framework. By specifying features, classes, and model parameters, it enhances interpretability for machine learning models. |
| [pipeline_explain.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/interpretable/pipeline_explain.py) | Generates and visualizes an interpretable explanation for a machine learning pipeline in a cancer classification scenario. Uses a surrogate decision tree method to explain the pipelines predictions, providing insights into feature importance. |

</details>

<details closed><summary>examples.simple.time_series_forecasting</summary>

| File | Summary |
| --- | --- |
| [cgru.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/time_series_forecasting/cgru.py) | Demonstrates time series forecasting using a CGRU pipeline, showcasing serialization and visualization in the FEDOT repository structure. |
| [tuning_pipelines.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/time_series_forecasting/tuning_pipelines.py) | SummaryThis code file in the `FEDOT` repository plays a crucial role in orchestrating the core functionality related to generating and analyzing data workflows. It is responsible for managing the interactions between different modules within the system to enable the seamless creation and evaluation of data processing pipelines. By encapsulating the workflow generation logic, this code promotes modularity and extensibility within the repositorys architecture, ultimately empowering developers to experiment with various data transformations and predictive modeling techniques efficiently. |
| [gapfilling.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/time_series_forecasting/gapfilling.py) | Optimize_workflow.py`The `optimize_workflow.py` file in the `FEDOT` repository aims to enhance the efficiency of workflow configurations within the `FEDOT` framework. This code file contributes critical capabilities to automatically optimize workflows, enabling users to streamline their machine learning processes effectively. By leveraging this functionality, developers can achieve optimal workflow setups and boost the overall performance and productivity of their models within the `FEDOT` ecosystem. |
| [ts_pipelines.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/time_series_forecasting/ts_pipelines.py) | The code file in the repository `FEDOT` plays a crucial role in facilitating advanced machine learning workflows. It enhances the parent repositorys architecture by providing key functionalities for building, analyzing, and interpreting machine learning models. This code enables users to develop sophisticated data pipelines and conduct comprehensive model evaluations effortlessly. |
| [fitted_values.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/time_series_forecasting/fitted_values.py) | This code file in the FEDOT repository contributes essential functionality for automated machine learning workflows. It plays a key role in orchestrating and managing the pipeline of data preprocessing, model building, and result interpretation. By leveraging this code, users can efficiently create and execute complex machine learning pipelines, enhancing productivity and decision-making processes in various domains. |
| [api_forecasting.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/time_series_forecasting/api_forecasting.py) | The code file in this repositorys `FEDOT` folder serves a crucial role in facilitating remote interactions with the system. It enables users to interface with the core functionalities of the project from external environments, streamlining data processing and model building tasks. This feature enhances the projects accessibility and usability by allowing seamless integration with various platforms and tools for enhanced workflow flexibility. |

</details>

<details closed><summary>examples.simple.cli_application</summary>

| File | Summary |
| --- | --- |
| [cli_ts_call.bat](https://github.com/aimclub/FEDOT/blob/main/examples/simple/cli_application/cli_ts_call.bat) | Executes time series forecasting via the Fedot API CLI, training and testing on provided CSV data, predicting sea height with a forecast length of 10, and a timeout of 0.1 seconds. |
| [cli_classification_call.bat](https://github.com/aimclub/FEDOT/blob/main/examples/simple/cli_application/cli_classification_call.bat) | Enables CLI classification calls, integrating with parent repositorys API for classification problem with timeout settings. |
| [cli_regression_call.bat](https://github.com/aimclub/FEDOT/blob/main/examples/simple/cli_application/cli_regression_call.bat) | Executes a CLI application for regression task using specified Python path. Navigates to `fedot/api` and runs `fedot_cli.py` with train and test data, inferring model performance within a timeout. |
| [cli_call_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/cli_application/cli_call_example.py) | Executes CLI applications for time series forecasting, classification, and regression problems. Facilitates running.bat files, changing environment paths, and reading predictions from a CSV file. Supports seamless interaction with the FEDOT repositorys functionality. |

</details>

<details closed><summary>examples.simple.regression</summary>

| File | Summary |
| --- | --- |
| [api_regression.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/regression/api_regression.py) | Demonstrates running automated regression model training and prediction using data and predefined presets. Utilizes Fedot framework, logging, and visualization options for prediction evaluation. |
| [regression_pipelines.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/regression/regression_pipelines.py) | Regression_three_depth_manual_pipeline` combines random forest, KNN, and decision tree. `regression_ransac_pipeline` integrates RANSAC, scaling, and Lasso regression. Constructed pipelines enhance model flexibility in regression tasks within the repositorys architecture. |
| [regression_with_tuning.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/regression/regression_with_tuning.py) | This code file in the repository contributes to the functionality that enables advanced data preprocessing within the FEDOT framework. By handling complex data preprocessing tasks efficiently, it empowers users to prepare their datasets effectively for downstream machine learning workflows. Through its implementation, it ensures that the data is processed accurately and in a structured manner, enhancing the overall performance and reliability of machine learning models developed using the FEDOT framework. |

</details>

<details closed><summary>examples.simple.classification</summary>

| File | Summary |
| --- | --- |
| [api_classification.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/classification/api_classification.py) | Demonstrates classification model training and prediction using Fedot framework. Configurable for visualization and hyperparameter tuning. Achieves robust model evaluation through metrics. |
| [multiclass_prediction.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/classification/multiclass_prediction.py) | This code file in the `FEDOT` repository plays a crucial role in enabling the integration and interoperability of diverse machine learning models within the framework. It achieves this by providing a unified interface for model composition, simplifying the creation of complex pipelines for data processing and analysis. This functionality significantly enhances the flexibility and scalability of the overall system architecture, empowering developers to build sophisticated and efficient machine learning workflows with ease. |
| [classification_pipelines.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/classification/classification_pipelines.py) | This code file in the `FEDOT` repository plays a crucial role in enabling seamless communication between different components of the system. It facilitates efficient data preprocessing, structural analysis, and model explainability. By harnessing the functionalities within this code, the repositorys architecture is empowered to deliver advanced solutions while maintaining a streamlined workflow. |
| [resample_example.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/classification/resample_example.py) | This code file plays a pivotal role in the FEDOT repository by orchestrating the core functionality related to data preprocessing and feature engineering. It handles the transformation and cleansing of raw data inputs, preparing them for subsequent analysis and modeling within the FEDOT framework. Leveraging this code, users can enhance the quality and relevance of their data, enabling more accurate and effective machine learning workflows. |
| [classification_with_tuning.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/classification/classification_with_tuning.py) | This code file in the `FEDOT` repository plays a crucial role in enabling the seamless import and export of machine learning projects within the framework. It facilitates the sharing of machine learning workflows across different environments, ensuring compatibility and ease of use for developers working on diverse projects. |
| [image_classification_problem.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/classification/image_classification_problem.py) | Implements image classification using CNN pipelines & TensorFlow. Calculates ROC-AUC metric for validation. Loads datasets, fits pipeline, predicts, and evaluates the model performance. |

</details>

<details closed><summary>examples.simple.api_builder</summary>

| File | Summary |
| --- | --- |
| [multiple_ts_forecasting_tasks.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/api_builder/multiple_ts_forecasting_tasks.py) | Generates multiple time series forecasting models using Fedot, with preset configurations, evolution setup, and pipeline evaluation. This script builds, fits, predicts, and visualizes models for each dataset in a specified folder. |
| [classification_with_api_builder.py](https://github.com/aimclub/FEDOT/blob/main/examples/simple/api_builder/classification_with_api_builder.py) | Implements classification pipeline setup and evaluation using FedotBuilder in the repository structures examples folder, demonstrating model fitting, prediction, and visualization for a real cases scoring data. |

</details>

<details closed><summary>examples.real_cases</summary>

| File | Summary |
| --- | --- |
| [multivariate_ts_forecasting.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/multivariate_ts_forecasting.py) | Autotuning.py`This code file, `autotuning.py`, plays a crucial role in the parent repositorys architecture by enabling automatic tuning of hyperparameters in machine learning models. This feature enhances the performance and efficiency of the models by dynamically adjusting parameters based on the data characteristics. By integrating this functionality, the code promotes a streamlined workflow for users, allowing them to achieve optimal model configurations without manual intervention. |
| [time_series_gapfilling_case.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/time_series_gapfilling_case.py) | This code file within the FEDOT repository serves the crucial function of providing an interface for interacting with the core functionality of the system. It enables users to leverage the advanced features for building and analyzing machine learning workflows without delving into complex technical details. By abstracting the intricacies of the system, this code promotes ease of use and fosters efficient workflow creation and analysis in a user-friendly manner. |
| [kc2_sourcecode_defects_classification.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/kc2_sourcecode_defects_classification.py) | Implements data preprocessing and model training for sourcecode defect classification. Uses Fedot for auto ML and a baseline model comparison in the KC2 dataset scenario. |
| [metocean_forecasting_problem.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/metocean_forecasting_problem.py) | This code file in the `FEDOT` repository plays a crucial role in facilitating advanced data analysis and modeling tasks using the FEDOT framework. It empowers users to create custom machine learning workflows, leveraging a variety of data preprocessing and model structuring techniques. By integrating with the core functionalities of the repository, this code file enables users to build, analyze, and optimize machine learning pipelines tailored to their specific data sets and requirements. |
| [multi_ts_level_forecasting.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/multi_ts_level_forecasting.py) | This code file in the FEDOT repository plays a crucial role in enabling the orchestration and management of machine learning workflows within the framework. It facilitates the creation of complex data processing pipelines and model ensembles for advanced analytics tasks. By leveraging this component, users can design, optimize, and execute machine learning experiments efficiently, fostering innovation and robustness in their projects. |
| [spam_detection.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/spam_detection.py) | This code file in the `FEDOT` repository is a critical feature for the projects architecture. It focuses on achieving seamless integration with external systems by providing a robust set of APIs for data processing and machine learning workflows. The file plays a key role in enabling the project to interact efficiently with various data sources and streamline the machine learning pipeline, contributing significantly to the overall functionality and versatility of the repository. |
| [dataset_preparation.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/dataset_preparation.py) | Manages unpacking archived datasets securely, preventing path traversal attacks by verifying extracted files locations. Automatically unpacks if the archive is present and not already extracted; otherwise, confirms the archive is already unpacked. |
| [multi_target_levels_forecasting.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/multi_target_levels_forecasting.py) | Optimize_hyperparams.py`This code file in the `FEDOT` repository plays a crucial role in optimizing hyperparameters for machine learning models. By leveraging sophisticated algorithms and techniques, it automates the process of fine-tuning model parameters to enhance predictive performance. The `optimize_hyperparams.py` file significantly contributes to the overall efficiency and effectiveness of the machine learning workflow within the parent repository by streamlining the hyperparameter optimization phase. |

</details>

<details closed><summary>examples.real_cases.river_levels_prediction</summary>

| File | Summary |
| --- | --- |
| [river_level_case_composer.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/river_levels_prediction/river_level_case_composer.py) | This code file in the FEDOT repository plays a crucial role in enabling the efficient import and export of machine learning projects. It enhances the repositorys architecture by facilitating seamless sharing and collaboration on projects built using FEDOTs capabilities. |
| [river_level_case_manual.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/river_levels_prediction/river_level_case_manual.py) | This code file within the FEDOT repository serves the critical purpose of providing essential utility functions and tools to support various aspects of the framework. It complements the core functionality of FEDOT by offering essential functions for preprocessing, remote operations, explainability, and structural analysis. By encapsulating these critical utilities, this code enhances the overall robustness and versatility of the FEDOT framework, empowering users to efficiently manipulate and analyze data for improved machine learning workflows. |

</details>

<details closed><summary>examples.real_cases.credit_scoring</summary>

| File | Summary |
| --- | --- |
| [credit_scoring_problem_multiobj.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/credit_scoring/credit_scoring_problem_multiobj.py) | Auto_ml_pipeline.py`The `auto_ml_pipeline.py` code file in the `FEDOT` repository orchestrates an automated machine learning pipeline construction process. It leverages the repositorys modular architecture to seamlessly integrate various machine learning tasks and algorithms. This code facilitates the streamlined creation of complex ML pipelines within the framework, enhancing efficiency and enabling rapid experimentation with diverse models and data configurations. |
| [credit_scoring_problem.py](https://github.com/aimclub/FEDOT/blob/main/examples/real_cases/credit_scoring/credit_scoring_problem.py) | This code file within the FEDOT repository plays a crucial role in enabling seamless import and export of machine learning projects. By providing functionalities for project serialization and deserialization, it ensures effortless sharing and collaboration across different environments. This feature promotes project reproducibility, facilitates model evaluation, and fosters scalable experimentation within the repositorys machine learning framework. |

</details>

---

##  Getting Started

###  Prerequisites

**Python**: `version x.y.z`

###  Installation

Build the project from source:

1. Clone the FEDOT repository:
```sh
❯ git clone https://github.com/aimclub/FEDOT
```

2. Navigate to the project directory:
```sh
❯ cd FEDOT
```

3. Install the required dependencies:
```sh
❯ pip install -r requirements.txt
```

###  Usage

To run the project, execute the following command:

```sh
❯ python main.py
```

###  Tests

Execute the test suite using the following command:

```sh
❯ pytest
```

---

##  Project Roadmap

- [X] **`Task 1`**: <strike>Implement feature one.</strike>
- [ ] **`Task 2`**: Implement feature two.
- [ ] **`Task 3`**: Implement feature three.

---

##  Contributing

Contributions are welcome! Here are several ways you can contribute:

- **[Report Issues](https://github.com/aimclub/FEDOT/issues)**: Submit bugs found or log feature requests for the `FEDOT` project.
- **[Submit Pull Requests](https://github.com/aimclub/FEDOT/blob/main/CONTRIBUTING.md)**: Review open PRs, and submit your own PRs.
- **[Join the Discussions](https://github.com/aimclub/FEDOT/discussions)**: Share your insights, provide feedback, or ask questions.

<details closed>
<summary>Contributing Guidelines</summary>

1. **Fork the Repository**: Start by forking the project repository to your github account.
2. **Clone Locally**: Clone the forked repository to your local machine using a git client.
   ```sh
   git clone https://github.com/aimclub/FEDOT
   ```
3. **Create a New Branch**: Always work on a new branch, giving it a descriptive name.
   ```sh
   git checkout -b new-feature-x
   ```
4. **Make Your Changes**: Develop and test your changes locally.
5. **Commit Your Changes**: Commit with a clear message describing your updates.
   ```sh
   git commit -m 'Implemented new feature x.'
   ```
6. **Push to github**: Push the changes to your forked repository.
   ```sh
   git push origin new-feature-x
   ```
7. **Submit a Pull Request**: Create a PR against the original project repository. Clearly describe the changes and their motivations.
8. **Review**: Once your PR is reviewed and approved, it will be merged into the main branch. Congratulations on your contribution!
</details>

<details closed>
<summary>Contributor Graph</summary>
<br>
<p align="left">
   <a href="https://github.com{/aimclub/FEDOT/}graphs/contributors">
      <img src="https://contrib.rocks/image?repo=aimclub/FEDOT">
   </a>
</p>
</details>

---

##  License

This project is protected under the [SELECT-A-LICENSE](https://choosealicense.com/licenses) License. For more details, refer to the [LICENSE](https://choosealicense.com/licenses/) file.

---

##  Acknowledgments

- List any resources, contributors, inspiration, etc. here.

---
