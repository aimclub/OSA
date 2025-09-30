# Workflow Generator

This module provides a tool for generating workflows for Python repositories. It can create customizable CI/CD pipelines that include:

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