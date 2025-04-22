# GitHub Action Workflow Generator

This module provides a tool for generating GitHub Action workflows for Python repositories. It can create customizable CI/CD pipelines that include:

- Automated unit test execution
- Automated code formatting using Black
- Automated PEP 8 compliance checks (using flake8 or pylint)
- Advanced autopep8 formatting with PR comments
- Slash command for fixing PEP8 issues
- Optional PyPI publication

## Usage

The workflow generator can be used as part of the Open-Source-Advisor tool by adding the `--generate-workflows` flag to your command:

```bash
python -m osa_tool.run --repository https://github.com/username/repo --generate-workflows
```

### Customizing Workflows

You can customize the generated workflows using the following command-line arguments:

| Argument | Description | Default |
|----------|-------------|---------|
| `--workflows-output-dir` | Directory where the workflow files will be saved | `.github/workflows` |
| `--include-tests` | Include unit tests workflow | `True` |
| `--include-black` | Include Black formatter workflow | `True` |
| `--include-pep8` | Include PEP 8 compliance workflow | `True` |
| `--include-autopep8` | Include autopep8 formatter workflow | `False` |
| `--include-fix-pep8` | Include fix-pep8 command workflow | `False` |
| `--include-pypi` | Include PyPI publish workflow | `False` |
| `--python-versions` | Python versions to test against | `3.8 3.9 3.10` |
| `--pep8-tool` | Tool to use for PEP 8 checking (flake8 or pylint) | `flake8` |
| `--use-poetry` | Use Poetry for packaging | `False` |
| `--branches` | Branches to trigger the workflows on | `main master` |
| `--codecov-token` | Use Codecov token for uploading coverage | `False` |
| `--include-codecov` | Include Codecov coverage step in a unit tests workflow | `True` |

### Example

Generate all workflows for a repository:

```bash
python -m osa_tool.run --repository https://github.com/username/repo \
  --generate-workflows \
  --include-tests \
  --include-black \
  --include-pep8 \
  --include-autopep8 \
  --include-fix-pep8 \
  --include-pypi \
  --python-versions 3.8 3.9 3.10 \
  --pep8-tool flake8 \
  --use-poetry \
  --branches main develop \
  --codecov-token \
  --include-codecov
```

## Generated Workflows

### Unit Tests Workflow

The unit tests workflow runs your tests on multiple Python versions and operating systems. It can also upload code coverage to Codecov.

Example:
```yaml
name: Unit Tests
'on':
  push:
    branches:
    - main
    - develop
  pull_request:
    branches:
    - main
    - develop
  workflow_dispatch: {}
jobs:
  test:
    name: Run Tests
    runs-on: ${{ matrix.os }}
    timeout-minutes: 15
    strategy:
      matrix:
        os:
        - ubuntu-latest
        python-version:
        - '3.8'
        - '3.9'
        - '3.10'
    steps:
    - name: Checkout repo
      uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: pip install -r requirements.txt && pip install pytest pytest-cov
    - name: Run tests
      run: pytest tests/ --cov=.
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      with:
        token: ${{ secrets.CODECOV_TOKEN }}
```

### Black Formatter Workflow

The Black formatter workflow checks your code formatting using Black.

Example:
```yaml
name: Black Formatter
'on':
- push
- pull_request
jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
    - name: Checkout repo
      uses: actions/checkout@v4
    - name: Run Black
      uses: psf/black@stable
      with:
        options: --check --diff
        src: .
        jupyter: 'false'
```

### PEP 8 Compliance Workflow

The PEP 8 compliance workflow checks your code against PEP 8 style guidelines using flake8 or pylint.

Example:
```yaml
name: PEP 8 Compliance
on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
jobs:
  lint:
    name: Run flake8
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4
      - name: Set up Python 3.10
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install flake8
      - name: Run flake8
        run: flake8
```

### Autopep8 Workflow

The autopep8 workflow checks your code for PEP 8 compliance and comments on pull requests.

Example:
```yaml
name: Format python code with autopep8
on:
  pull_request:
    branches: [main, master]
jobs:
  autopep8:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: autopep8
        id: autopep8
        uses: peter-evans/autopep8@v2
        with:
          args: --exit-code --max-line-length 120 --recursive --in-place --aggressive --aggressive .
      # Additional steps for commenting on pull requests
```

### Fix-PEP8 Command Workflow

The fix-pep8 command workflow automatically fixes PEP 8 issues when triggered by a slash command.

Example:
```yaml
name: fix-pep8-command
on:
  repository_dispatch:
    types: [fix-pep8-command]
jobs:
  fix-pep8:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.REPO_ACCESS_TOKEN }}
          repository: ${{ github.event.client_payload.pull_request.head.repo.full_name }}
          ref: ${{ github.event.client_payload.pull_request.head.ref }}
      - name: autopep8
        id: autopep8
        uses: peter-evans/autopep8@v2
        with:
          args: --exit-code --max-line-length 120 --recursive --in-place --aggressive --aggressive .
      - name: Commit autopep8 changes
        id: cap8c
        if: steps.autopep8.outputs.exit-code == 2
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          git commit -am "Automated autopep8 fixes"
          git push
```

### PyPI Publish Workflow

The PyPI publish workflow builds and publishes your package to PyPI.

Example:
```yaml
name: PyPI Publish
on:
  push:
    tags: ['*.*.*']
  workflow_dispatch:
permissions:
  contents: read
  id-token: write
jobs:
  pypi-publish:
    name: Upload release to PyPI
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/${{ github.event.repository.name }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      - name: Set up Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install setuptools wheel twine build
      - name: Build package
        run: python -m build
      - name: Publish package distributions to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

## Advanced Usage

For more advanced usage, you can import the `GitHubWorkflowGenerator` class directly in your Python code:

```python
from osa_tool.github_workflow import GitHubWorkflowGenerator

# Create a workflow generator
generator = GitHubWorkflowGenerator(output_dir=".github/workflows")

# Generate a unit test workflow
generator.generate_unit_test_workflow(
    python_versions=["3.8", "3.9", "3.10"],
    os_list=["ubuntu-latest", "windows-latest", "macos-latest"],
    dependencies_command="pip install -r requirements.txt",
    test_command="pytest tests/",
    branches=["main", "develop"],
    coverage=True,
    codecov_token=True
)

# Generate a Black formatter workflow
generator.generate_black_formatter_workflow(
    black_args="--check .",
    branches=["main", "develop"]
)

# Generate a PEP 8 compliance workflow
generator.generate_pep8_workflow(
    tool="flake8",
    args="--max-line-length=120",
    python_version="3.10",
    branches=["main", "develop"]
)

# Generate an autopep8 workflow
generator.generate_autopep8_workflow(
    max_line_length=120,
    aggressive_level=2,
    branches=["main", "develop"]
)

# Generate a fix-pep8 command workflow
generator.generate_fix_pep8_command_workflow(
    max_line_length=120,
    aggressive_level=2,
    repo_access_token=True
)

# Generate a slash command dispatch workflow
generator.generate_slash_command_dispatch_workflow(
    commands=["fix-pep8"],
    permission="none"
)

# Generate a PyPI publish workflow
generator.generate_pypi_publish_workflow(
    python_version="3.10",
    use_poetry=True,
    trigger_on_tags=True,
    trigger_on_release=False,
    manual_trigger=True
)

# Or generate all workflows at once
generator.generate_complete_workflow(
    include_tests=True,
    include_black=True,
    include_pep8=True,
    include_autopep8=True,
    include_fix_pep8=True,
    include_pypi=True,
    python_versions=["3.8", "3.9", "3.10"],
    pep8_tool="flake8",
    use_poetry=True,
    branches=["main", "develop"],
    codecov_token=True
)