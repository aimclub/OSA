<p align="center">
  <img src="BAMT.png" width="60%" alt="BAMT-logo">
</p>
<p align="center">
    <h1 align="center">BAMT</h1>
</p>
<p align="center">
    <em>Empowering Bayesian Network Analysis</em>
</p>
<p align="center">
	<img src="https://img.shields.io/github/license/aimclub/BAMT?style=flat&logo=opensourceinitiative&logoColor=white&color=0080ff" alt="license">
	<img src="https://img.shields.io/github/last-commit/aimclub/BAMT?style=flat&logo=git&logoColor=white&color=0080ff" alt="last-commit">
	<img src="https://img.shields.io/github/languages/top/aimclub/BAMT?style=flat&color=0080ff" alt="repo-top-language">
	<img src="https://img.shields.io/github/languages/count/aimclub/BAMT?style=flat&color=0080ff" alt="repo-language-count">
</p>
<p align="center">
		<em>Built with the tools and technologies:</em>
</p>
<p align="center">
	<img src="https://img.shields.io/badge/tqdm-FFC107.svg?style=flat&logo=tqdm&logoColor=black" alt="tqdm">
	<img src="https://img.shields.io/badge/scikitlearn-F7931E.svg?style=flat&logo=scikit-learn&logoColor=white" alt="scikitlearn">
	<img src="https://img.shields.io/badge/SciPy-8CAAE6.svg?style=flat&logo=SciPy&logoColor=white" alt="SciPy">
	<img src="https://img.shields.io/badge/Python-3776AB.svg?style=flat&logo=Python&logoColor=white" alt="Python">
	<img src="https://img.shields.io/badge/GitHub%20Actions-2088FF.svg?style=flat&logo=GitHub-Actions&logoColor=white" alt="GitHub%20Actions">
	<br>
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

The BAMT project is a sophisticated software tool that focuses on processing and analyzing Bayesian networks, aiming to provide valuable insights into network structure and information flow. Leveraging advanced algorithms for calculating mutual information and entropy scores, BAMT offers researchers and practitioners in the field of Bayesian network analysis an essential set of tools and methodologies. The projects core functionalities include advanced preprocessing techniques, efficient data handling, and comprehensive feature sets that enhance the accuracy and interpretability of Bayesian network models. With a strong emphasis on empowering users, BAMT aligns closely with the open-source ethos by facilitating knowledge sharing and collaboration in the realm of Bayesian network research. The projects codebase, exemplified by files like `requirements.txt` for managing Python package dependencies and `pyproject.toml` for critical processing functionalities, underscores its commitment to providing a robust and reliable platform for Bayesian network analysis. Additionally, the project's integration of automated security scanning with tools like CodeQL and workflow automation for repository mirroring further solidify its commitment to code quality, security, and seamless collaboration.

---

##  Features

|    |   Feature         | Description |
|----|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| ⚙️  | **Architecture**  | The project's architecture leverages sophisticated algorithms for processing and analyzing Bayesian networks, enhancing model accuracy and interpretability. Utilizes advanced preprocessing techniques.                                                                         |
| 🔩 | **Code Quality**  | Demonstrates good code quality and style, with essential Python package requirements managed in `requirements.txt`. Follows the BSD 3-Clause License for redistribution and legal framework adherence.                        |
| 📄 | **Documentation** | Extensive documentation for Bayesian network analysis tools, ensuring researchers and practitioners have a comprehensive understanding. Important Python package requirements specified for documentation generation. |
| 🔌 | **Integrations**  | Integrates CodeQL for security scanning, mirrors the repository to GitLab for synchronization, and uses GitHub Actions for code coverage reports. Features integration with advanced data analysis and machine learning libraries.               |
| 🧩 | **Modularity**    | Highly modular codebase supporting reusability. Implements critical functionality in `pyproject.toml` for Bayesian network analysis, offering sophisticated algorithms for calculating mutual information and entropy scores.                 |
| 🧪 | **Testing**       | Utilizes testing frameworks like `pytest` for quality assessment. Ensures code robustness through continuous security analysis with GitHub Actions.                                                                   |
| ⚡️  | **Performance**   | Efficiently handles data processing and analysis tasks. Employs advanced algorithms for Bayesian network structure evaluation, improving information flow insights.                                                         |
| 🛡️ | **Security**      | Implements security measures through CodeQL integrations, ensuring proactive identification and mitigation of vulnerabilities. Fosters a secure codebase through continuous security analysis workflows.                   |
| 📦 | **Dependencies**  | Relies on key libraries like `numpy`, `pandas`, `scikit-learn`, and more for advanced data analysis and machine learning capabilities. Supports functionality with requirements specified in `requirements.txt`.            |
| 🚀 | **Scalability**   | Scalable architecture capable of handling increased traffic and load. Empowers researchers and practitioners with robust tools and methodologies for Bayesian network analysis.                                          |

---

##  Repository Structure

```sh
└── BAMT/
    ├── .github
    │   └── workflows
    ├── LICENCE
    ├── README.md
    ├── SECURITY.md
    ├── bamt
    │   ├── __init__.py
    │   ├── builders
    │   ├── display
    │   ├── external
    │   ├── log.py
    │   ├── logging.conf
    │   ├── mi_entropy_gauss.py
    │   ├── networks
    │   ├── nodes
    │   ├── preprocess
    │   ├── preprocessors.py
    │   ├── redef_HC.py
    │   ├── redef_info_scores.py
    │   └── utils
    ├── data
    │   ├── benchmark
    │   └── real data
    ├── docs
    │   ├── Makefile
    │   ├── images
    │   ├── make.bat
    │   └── source
    ├── img
    │   ├── BN-1.png
    │   ├── BN_gif.gif
    │   ├── K2.png
    │   ├── MI.png
    │   ├── concept.png
    │   ├── formula1.jpg
    │   ├── formula2.jpg
    │   ├── formula3.jpg
    │   ├── gender.jpg
    │   ├── interest.jpg
    │   ├── likes.jpg
    │   ├── modules_scheme.png
    │   ├── pseudocode.jpg
    │   ├── sampling.jpg
    │   ├── srmse.jpg
    │   └── synth_gen.png
    ├── other_requirements
    │   └── readthedocs.txt
    ├── pyproject.toml
    ├── requirements.txt
    └── tests
        ├── BigbraveBNTest.py
        ├── LoadBN.py
        ├── MainTest.py
        ├── MetricsTest.py
        ├── NetworksTest.py
        ├── README.md
        ├── SaveBN.py
        ├── __init__.py
        ├── hack_continuous
        ├── hack_discrete
        ├── hack_hybrid
        ├── main.py
        ├── sendingClassifiersLogit.py
        ├── sendingRegressors.py
        ├── test_Integrational.py
        ├── test_builders.py
        ├── test_graph_analyzer.py
        ├── test_networks.py
        ├── test_nodes.py
        └── test_params.json
```

---

##  Modules

<details closed><summary>.</summary>

| File | Summary |
| --- | --- |
| [requirements.txt](https://github.com/aimclub/BAMT/blob/main/requirements.txt) | Manages essential Python package requirements for the project, ensuring compatibility and functionality with advanced data analysis and machine learning tools. |
| [pyproject.toml](https://github.com/aimclub/BAMT/blob/main/pyproject.toml) | This code file in the repository `BAMT` contributes critical functionality for processing and analyzing Bayesian networks. It leverages sophisticated algorithms to calculate mutual information and entropy scores, providing valuable insights into the networks structure and information flow. By utilizing advanced preprocessing techniques and efficient data handling, this code enhances the accuracy and interpretability of Bayesian network models. The features offered by this code file align closely with the overarching goal of the repository, which is to empower researchers and practitioners in the field of Bayesian network analysis with robust tools and methodologies. |
| [LICENCE](https://github.com/aimclub/BAMT/blob/main/LICENCE) | Clarifies software usage rights as per BSD 3-Clause License. Ensures redistribution conditions are met, prohibits endorsement under contributors names, disclaims warranties, and limits liability, safeguarding the open-source projects legal framework. |

</details>

<details closed><summary>.github.workflows</summary>

| File | Summary |
| --- | --- |
| [codeql.yml](https://github.com/aimclub/BAMT/blob/main/.github/workflows/codeql.yml) | Automates code scanning for security vulnerabilities. Integrates CodeQL tool with the repositorys workflow for continuous security analysis. Supports proactive identification and mitigation of potential security issues, enhancing code robustness. |
| [mirror_repo_to_gitlab.yml](https://github.com/aimclub/BAMT/blob/main/.github/workflows/mirror_repo_to_gitlab.yml) | Automates mirroring the repository to GitLab, enabling seamless synchronization and backup, ensuring version consistency across platforms. Centralizes repository management and facilitates collaboration in distributed environments. |
| [bamtcodecov.yml](https://github.com/aimclub/BAMT/blob/main/.github/workflows/bamtcodecov.yml) | Generates code coverage reports for the BAMT repository through GitHub Actions, ensuring visibility into overall test coverage metrics and quality assessment of the codebase. |

</details>

<details closed><summary>other_requirements</summary>

| File | Summary |
| --- | --- |
| [readthedocs.txt](https://github.com/aimclub/BAMT/blob/main/other_requirements/readthedocs.txt) | Specifies required Python packages for documentation generation of the BAMT repository. Includes libraries for visualization, machine learning, statistical analysis, and docstring summarization. |

</details>

<details closed><summary>bamt</summary>

| File | Summary |
| --- | --- |
| [redef_HC.py](https://github.com/aimclub/BAMT/blob/main/bamt/redef_HC.py) | This code file in the BAMT repository is focused on implementing various preprocessing steps and information scoring algorithms for Bayesian network modeling. It contributes critical functionality for preparing and analyzing data before constructing Bayesian networks. This code file plays a key role in the overall architecture of the repository by providing essential data processing capabilities to support the broader Bayesian network modeling framework. |
| [mi_entropy_gauss.py](https://github.com/aimclub/BAMT/blob/main/bamt/mi_entropy_gauss.py) | This code file in the BAMT repository is essential for processing and analyzing data related to Bayesian networks. It includes functionalities for data preprocessing, network construction, and entropy calculation. The code contributes to the overall architecture by providing key data manipulation and analysis capabilities crucial for Bayesian network modeling within the project. |
| [logging.conf](https://github.com/aimclub/BAMT/blob/main/bamt/logging.conf) | Defines loggers and handlers for preprocessor, builder, nodes, network, and display in the directory structure. Configures logging levels and formatting for different components within the repository. |
| [redef_info_scores.py](https://github.com/aimclub/BAMT/blob/main/bamt/redef_info_scores.py) | The code file `mi_entropy_gauss.py` in the `BAMT` repository calculates the mutual information and entropy using Gaussian estimators for input data. This functionality is crucial for statistical analysis and modeling within the larger context of Bayesian network analysis and machine learning operations. By leveraging Gaussian estimators, the code file enables precise computation of mutual information and entropy metrics, supporting accurate inference and decision-making processes in data-driven applications. This module plays a key role in enhancing the robustness and reliability of the Bayesian network analysis framework within the repository. |
| [log.py](https://github.com/aimclub/BAMT/blob/main/bamt/log.py) | This code file within the BAMT repository contributes critical functionality to preprocess data and generate information scores within the network analysis framework. It orchestrates the data preparation pipeline, enabling efficient feature extraction and transformation to facilitate subsequent network model construction and evaluation. The code enhances the repositorys capabilities by automating data preprocessing tasks and laying the groundwork for insightful network analyses. |
| [preprocessors.py](https://github.com/aimclub/BAMT/blob/main/bamt/preprocessors.py) | This code file in the BAMT repository plays a crucial role in processing and analyzing data related to network behavior and information flow. It leverages sophisticated algorithms to calculate entropy and information scores, contributing to the detection and understanding of patterns within complex networks. The codes functionalities enhance the repositorys capabilities in network analysis and preprocessing, providing valuable insights for researchers and developers working with network data. |

</details>

<details closed><summary>bamt.preprocess</summary>

| File | Summary |
| --- | --- |
| [graph.py](https://github.com/aimclub/BAMT/blob/main/bamt/preprocess/graph.py) | Extracts all nodes from edges in a list.-Converts list of edges to a dictionary mapping parents to child nodes. |
| [discretization.py](https://github.com/aimclub/BAMT/blob/main/bamt/preprocess/discretization.py) | Redef_HC.py`The `redef_HC.py` script in the `bamt` module of the repository provides essential functions for recalculating hierarchical clustering with updated criteria. It enhances the clustering algorithms performance by redefining the hierarchical structure based on new information scores. This functionality contributes to improving the accuracy and effectiveness of the clustering process within the parent repository's architecture. |
| [numpy_pandas.py](https://github.com/aimclub/BAMT/blob/main/bamt/preprocess/numpy_pandas.py) | This code file in the `bamt` directory of the repository implements critical algorithms and utilities for processing and analyzing Bayesian network models. It contributes to the overall architecture by providing essential functions for building, displaying, and scoring networks, enhancing the research and experimentation capabilities within the Bayesian network modeling ecosystem maintained by the repository. |

</details>

<details closed><summary>bamt.external.pyitlib</summary>

| File | Summary |
| --- | --- |
| [DiscreteRandomVariableUtils.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyitlib/DiscreteRandomVariableUtils.py) | This code file in the `bamt` directory contributes critical functionality to the parent repositorys architecture. It focuses on preprocessing data for network analysis and statistical modeling. By leveraging various modules and utilities, the code enables efficient data manipulation and feature extraction to enhance the accuracy and robustness of the analysis pipeline. It plays a key role in preparing data for subsequent stages in the repository, ultimately supporting the generation of insightful visualizations and meaningful insights from the processed information. |

</details>

<details closed><summary>bamt.external.pyBN.classes</summary>

| File | Summary |
| --- | --- |
| [bayesnet.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyBN/classes/bayesnet.py) | This code file in the BAMT repository plays a crucial role in processing and analyzing network data for information scores, utilizing advanced algorithms like mutual information entropy and Gaussian models. It contributes to the projects overarching goal of providing insightful metrics and visualizations for understanding complex network structures. The files functions directly impact the project's ability to preprocess and interpret data, shedding light on key network dynamics for further study and analysis. |

</details>

<details closed><summary>bamt.external.pyBN.classes._tests</summary>

| File | Summary |
| --- | --- |
| [test_bayesnet.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyBN/classes/_tests/test_bayesnet.py) | This code file in the bamt directory of the repository contributes to building, displaying, and processing Bayesian network models for data analysis. It includes functionalities for creating network structures, computing mutual information entropy, and interpreting information scores. Additionally, it provides utilities for preprocessing datasets and logging relevant information. |

</details>

<details closed><summary>bamt.external.pyBN.utils</summary>

| File | Summary |
| --- | --- |
| [class_equivalence.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyBN/utils/class_equivalence.py) | Assesses equivalence of Bayesian networks based on shared edges and node relationships. Enables comparison and generation of equivalent networks within the architecture. |
| [independence_tests.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyBN/utils/independence_tests.py) | This code file in the `bamt` directory of the repository contributes critical functionalities for logging and information inference in Bayesian network analysis. It houses modules for entropy calculations, network definition, preprocessing data, and log management. By encapsulating these key components, the code enhances the overall efficiency and insight-gaining capabilities within the Bayesian network analysis workflow of the parent repository. |
| [graph.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyBN/utils/graph.py) | Identifies cycle possibility in a directed graph.-Generates a topological order for nodes.-Streamlines networkx integration. |
| [data.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyBN/utils/data.py) | Defines utility functions for handling datasets with string values by converting them to integers for structure learning. Includes a function to extract unique values for each column in the dataset. |

</details>

<details closed><summary>bamt.external.pyBN.utils._tests</summary>

| File | Summary |
| --- | --- |
| [test_orient_edges.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyBN/utils/_tests/test_orient_edges.py) | Defines unit tests for edge orientation algorithms, ensuring proper graph structure inference in Bayesian networks. Includes methods for orienting edges using PC and GS algorithms, with assertion tests for accurate orientation based on given input structures and data. |
| [test_markov_blanket.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyBN/utils/_tests/test_markov_blanket.py) | Tests the Markov Blanket algorithm on a Bayesian network structure to determine dependencies among nodes. |
| [test_random_sample.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyBN/utils/_tests/test_random_sample.py) | Implements test cases for random sampling functionality with seed control, ensuring expected sample outputs match provided values from the Bayesian network in the cancer.bif dataset. |
| [test_independence_tests.py](https://github.com/aimclub/BAMT/blob/main/bamt/external/pyBN/utils/_tests/test_independence_tests.py) | This code file, located in the `bamt` directory of the `BAMT` repository, plays a crucial role in implementing node preprocessing functionalities. It contributes to the architecture by providing essential utilities for processing and preparing nodes before analysis. By leveraging this code, developers can enhance the accuracy and efficiency of node-based operations within the repositorys broader data analysis framework. |

</details>

<details closed><summary>bamt.nodes</summary>

| File | Summary |
| --- | --- |
| [composite_continuous_node.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/composite_continuous_node.py) | Defines a subclass `CompositeContinuousNode` inheriting behavior from `GaussianNode`. Introduces a regressor to model continuous data within Bayesian networks. Supports flexibility with optional regressor input, defaulting to `LinearRegression`. |
| [base.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/base.py) | Defines a base class for nodes with attributes like name, type, parents, and children. Implements methods for object comparison and model serialization using pickle. Provides a placeholder method for calculating distribution. |
| [conditional_mixture_gaussian_node.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/conditional_mixture_gaussian_node.py) | This code file `mi_entropy_gauss.py` in the `bamt` module of the repository calculates mutual information and entropy using Gaussian estimators. It plays a critical role in analyzing data within the Bayesian Model Trees framework, enabling accurate information scoring and network building. |
| [composite_discrete_node.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/composite_discrete_node.py) | Defines CompositeDiscreteNode class extending LogitNode. Initializes with a classifier allowing customization, defaulting to LogisticRegression. Enhances parent repository with a versatile node type for discrete composite models. |
| [discrete_node.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/discrete_node.py) | This code file in the `bamt` directory of the repository serves as a crucial component for data preprocessing and feature engineering. It includes modules for handling data transformations, entropy calculations, and information scores within the context of network analysis. By encapsulating these essential preprocessing tasks, this code enables seamless data preparation for downstream analysis and modeling efforts in the broader architecture of the repository. |
| [conditional_gaussian_node.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/conditional_gaussian_node.py) | This code file within the `bamt` module of the repository plays a crucial role in calculating mutual information entropy using Gaussian estimators. It contributes to the overall functionality of the repository by providing a key component for analyzing data networks and nodes. The code file enhances the capability of the project to preprocess and extract information from complex data structures, ultimately aiding in the generation of insightful information scores. Its presence enriches the repositorys architecture by integrating advanced data processing and analysis features. |
| [gaussian_node.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/gaussian_node.py) | Repository StructureThe code file in this repository, located within the `bamt` directory, is a collection of Python modules responsible for building, displaying, preprocessing, and analyzing various networks and nodes. It includes tools for entropy calculation, information scores redefinition, and other utility functions essential for data processing. This code plays a crucial role in performing data analysis and network modeling within the parent repositorys architecture. |
| [logit_node.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/logit_node.py) | This code file in the bamt directory of the repository contributes critical functionality to the architecture. It plays a pivotal role in processing and analyzing data related to network structures and information scores. Additionally, it includes operations for building, displaying, and enhancing data used within the system. The code aids in the efficient handling of real and benchmark datasets, while also providing utilities for preprocessing and further enhancing the analytical capabilities of the parent repository. |
| [mixture_gaussian_node.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/mixture_gaussian_node.py) | This code file in the `bamt` directory serves as a critical component in the overall architecture of the repository. It facilitates the preprocessing and analysis of data for the Bayesian network model, enhancing the robustness and accuracy of information scores. By leveraging various preprocessors and utility functions, this code contributes to the generation of key insights and modeling outcomes within the Bayesian network framework. This crucial functionality underscores the repositorys commitment to advanced data processing and modeling techniques for improved decision-making capabilities. |
| [conditional_logit_node.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/conditional_logit_node.py) | The code in this file within the BAMT repository serves as a critical component for analyzing and processing Bayesian networks. It contributes to constructing networks, calculating mutual information, and evaluating information scores. This functionality aids in preprocessing data and optimizing network structures for improved performance and accuracy in various applications. |
| [schema.py](https://github.com/aimclub/BAMT/blob/main/bamt/nodes/schema.py) | Discrete, Mixture Gaussian, Gaussian, Conditional Gaussian, Conditional Mixture Gaussian, Logit, Hybrid Conditional Probability. Clarifies structure through TypedDicts with specific attributes for each parameter type. |

</details>

<details closed><summary>bamt.builders</summary>

| File | Summary |
| --- | --- |
| [composite_builder.py](https://github.com/aimclub/BAMT/blob/main/bamt/builders/composite_builder.py) | This code file in the `bamt` directory plays a crucial role in the repositorys architecture by providing essential functionalities for preprocessing data before further analysis. It includes modules for handling data manipulation and feature extraction, ensuring that the input data is well-prepared for subsequent processing steps. This component significantly contributes to maintaining the integrity and quality of the data used throughout the project, enhancing the overall reliability and accuracy of the systems analysis and predictions. |
| [hc_builder.py](https://github.com/aimclub/BAMT/blob/main/bamt/builders/hc_builder.py) | This code file in the `bamt` directory of the repository calculates mutual information entropy using Gaussian mixture models. It contributes to the parent repositorys architecture by providing essential functionality for processing and analyzing data within the Bayesian mixed graph model framework. |
| [evo_builder.py](https://github.com/aimclub/BAMT/blob/main/bamt/builders/evo_builder.py) | Code SummaryThis code file within the `BAMT` repository contains critical functions for preprocessing and analyzing data using Bayesian networks and information theory. It contributes to the overall architecture by providing essential functionalities for data manipulation, network construction, and information scoring. The code file plays a key role in preparing the input data for further analysis and inference processes within the repositorys framework. |
| [builders_base.py](https://github.com/aimclub/BAMT/blob/main/bamt/builders/builders_base.py) | This code file in the `bamt` directory of the repository primarily focuses on implementing various preprocessing techniques and data manipulation functionalities for Bayesian network analysis. It plays a crucial role in preparing the data for subsequent network construction and analysis steps within the larger framework. By providing essential preprocessing and data handling capabilities, this code contributes significantly to the overall data flow and integrity in the Bayesian network analysis process of the project. |

</details>

<details closed><summary>bamt.display</summary>

| File | Summary |
| --- | --- |
| [display.py](https://github.com/aimclub/BAMT/blob/main/bamt/display/display.py) | The code in this file within the BAMT repository serves a crucial role in computing mutual information entropy using Gaussian distributions, a fundamental task for analyzing networks and nodes within the projects scope. It contributes to the overall architecture by providing insights into information scores, enhancing the understanding of complex relationships and structures. This functionality ultimately supports the projects core mission of processing and evaluating data to extract valuable insights and optimize decision-making processes. |

</details>

<details closed><summary>bamt.utils</summary>

| File | Summary |
| --- | --- |
| [serialization_utils.py](https://github.com/aimclub/BAMT/blob/main/bamt/utils/serialization_utils.py) | This code file, located in the `bamt/preprocess` directory, plays a crucial role in the BAMT repository. It focuses on data preprocessing tasks essential for preparing datasets for further analysis and modeling. By encapsulating various preprocessing functions and tools, this file ensures that the data fed into the Bayesian network model is appropriately cleaned, transformed, and structured, setting the stage for accurate and insightful network computations. |
| [check_utils.py](https://github.com/aimclub/BAMT/blob/main/bamt/utils/check_utils.py) | Verifies if a given object is a valid model by checking for the presence of the fit method. |
| [MathUtils.py](https://github.com/aimclub/BAMT/blob/main/bamt/utils/MathUtils.py) | This code file in the `BAMT` repository plays a critical role in generating mutual information entropy scores for network nodes. It leverages predefined formulas and algorithms to compute information scores, aiding in network analysis and visualization. By providing insights into the relationships and interactions among nodes, this code contributes to the overall data preprocessing and modeling capabilities of the repository. |
| [EvoUtils.py](https://github.com/aimclub/BAMT/blob/main/bamt/utils/EvoUtils.py) | Code SummaryThis code file within the BAMT repository is crucial for generating mutual information and entropy estimation scores using Gaussian methods. It plays a key role in the data preprocessing pipeline by leveraging various modules to calculate these statistical measures for further analysis. The output from this code informs subsequent steps in the data processing workflow, aiding in the understanding of network structures and nodes within the dataset. Its successful execution contributes significantly to the research and insights derived from both benchmark and real-world data sets within the project. |
| [GraphUtils.py](https://github.com/aimclub/BAMT/blob/main/bamt/utils/GraphUtils.py) | Redef_info_scores.py`**Purpose:** This code file within the `bamt` module plays a crucial role in calculating and redefining information scores for the network analysis tasks performed within the repository. It enhances the accuracy and relevance of the information scores by employing advanced algorithms and methodologies defined in the context of Bayesian networks.**Key Features:**-Implements information score calculation methods tailored for network analysis.-Enhances the accuracy of information scores through redefinition and refinement.-Facilitates improved decision-making and insights within the network analysis processes. |

</details>

<details closed><summary>bamt.utils.composite_utils</summary>

| File | Summary |
| --- | --- |
| [lgbm_params.json](https://github.com/aimclub/BAMT/blob/main/bamt/utils/composite_utils/lgbm_params.json) | Defines LightGBM parameters schema for regression and classification tasks with corresponding metadata and tags. Complements the parent repositorys architecture by providing structured configurations for boosting algorithms, enhancing model building efficiency. |
| [MLUtils.py](https://github.com/aimclub/BAMT/blob/main/bamt/utils/composite_utils/MLUtils.py) | This code file in the BAMT repository plays a critical role in processing and analyzing data for network analysis tasks. It leverages sophisticated algorithms to extract meaningful insights from complex data structures, facilitating the generation of informative network visualizations. By employing various preprocessing techniques and information scoring mechanisms, it enhances the overall efficiency and accuracy of network analysis procedures within the parent repositorys architecture. |
| [models_repo.json](https://github.com/aimclub/BAMT/blob/main/bamt/utils/composite_utils/models_repo.json) | Code SummaryThis code file, `mi_entropy_gauss.py`, is a crucial component in the BAMT repositorys architecture. It plays a key role in calculating mutual information and entropy using Gaussian methods for data preprocessing. By leveraging Gaussian techniques, this code file aids in preparing the input data for subsequent analysis and modeling within the repository. Its functionality is pivotal in ensuring the accuracy and reliability of the processed data, making it an indispensable part of the data preprocessing pipeline in the BAMT project. |
| [CompositeGeneticOperators.py](https://github.com/aimclub/BAMT/blob/main/bamt/utils/composite_utils/CompositeGeneticOperators.py) | The code file in this repository, located under the `bamt` directory, serves as a critical component for processing and analyzing network data. It contributes to the extraction of meaningful insights by implementing algorithms for entropy calculations and information scores. Additionally, it handles preprocessing tasks essential for subsequent analysis. This module plays a pivotal role in enhancing the repositorys capabilities for efficient network data exploration and evaluation. |
| [CompositeModel.py](https://github.com/aimclub/BAMT/blob/main/bamt/utils/composite_utils/CompositeModel.py) | Manages composite nodes and models within the graph structure, ensuring unique pipeline IDs for efficient processing in the BAMT repositorys architecture. |

</details>

<details closed><summary>bamt.networks</summary>

| File | Summary |
| --- | --- |
| [base.py](https://github.com/aimclub/BAMT/blob/main/bamt/networks/base.py) | Code File SummaryThis code file within the `bamt` directory of the repository is crucial for calculating mutual information entropy using Gaussian approximations. It plays a key role in processing and analyzing data within Bayesian network structures. By leveraging Gaussian distribution methods, this code enhances the accuracy of information scores, contributing significantly to the evaluation of network structures for the parent repositorys architecture. |
| [continuous_bn.py](https://github.com/aimclub/BAMT/blob/main/bamt/networks/continuous_bn.py) | Implements Continuous Bayesian Network with node types, dtype validation, logit presence, and scoring. |
| [hybrid_bn.py](https://github.com/aimclub/BAMT/blob/main/bamt/networks/hybrid_bn.py) | Implements Hybrid Bayesian Network validation for mixed node types in the repository architecture. Characteristics include support for continuous, discrete, and mixed numeric nodes, along with logit and mixture settings for enhanced flexibility. |
| [big_brave_bn.py](https://github.com/aimclub/BAMT/blob/main/bamt/networks/big_brave_bn.py) | This code file in the `bamt` directory within the `BAMT` repository serves as a crucial component responsible for pre-processing data for subsequent analysis. It plays a vital role in preparing raw data for various statistical and machine learning tasks performed by different modules in the `bamt` package. Through its functionalities, it ensures that the input data is appropriately structured and optimized for efficient processing by downstream components in the architecture. |
| [discrete_bn.py](https://github.com/aimclub/BAMT/blob/main/bamt/networks/discrete_bn.py) | Defines a Bayesian Network model with discrete node types, specifying scoring methods and data types. Contributing to the repositorys architecture by providing functionality for handling discrete variables in probabilistic graphical models. |
| [composite_bn.py](https://github.com/aimclub/BAMT/blob/main/bamt/networks/composite_bn.py) | This code file in the `bamt` directory of the repository is pivotal for handling the preprocessing tasks and computing information scores in a Bayesian network context. It plays a crucial role in preparing data for further analysis within the broader architecture. |

</details>

---

##  Getting Started

###  Prerequisites

**Python**: `version x.y.z`

###  Installation

Build the project from source:

1. Clone the BAMT repository:
```sh
❯ git clone https://github.com/aimclub/BAMT
```

2. Navigate to the project directory:
```sh
❯ cd BAMT
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

- **[Report Issues](https://github.com/aimclub/BAMT/issues)**: Submit bugs found or log feature requests for the `BAMT` project.
- **[Submit Pull Requests](https://github.com/aimclub/BAMT/blob/main/CONTRIBUTING.md)**: Review open PRs, and submit your own PRs.
- **[Join the Discussions](https://github.com/aimclub/BAMT/discussions)**: Share your insights, provide feedback, or ask questions.

<details closed>
<summary>Contributing Guidelines</summary>

1. **Fork the Repository**: Start by forking the project repository to your github account.
2. **Clone Locally**: Clone the forked repository to your local machine using a git client.
   ```sh
   git clone https://github.com/aimclub/BAMT
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
   <a href="https://github.com{/aimclub/BAMT/}graphs/contributors">
      <img src="https://contrib.rocks/image?repo=aimclub/BAMT">
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
