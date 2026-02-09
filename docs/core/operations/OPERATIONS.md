# Available Operations

This document is auto-generated. Do not edit manually.

---

| Name | Priority | Intents | Scopes | Args Schema | Executor | Method |
|------|----------|---------|--------|-------------|----------|--------|
| `generate_report` | 5 | new_task | full_repo, analysis | — | `ReportGenerator` | `build_pdf` |
| `translate_dirs` | 40 | new_task | full_repo, codebase | — | `RepositoryStructureTranslator` | `rename_directories_and_files` |
| `generate_docstrings` | 50 | new_task, feedback | full_repo, codebase | GenerateDocstringsArgs | `DocstringsGenerator` | `run` |
| `ensure_license` | 60 | new_task | full_repo, docs | EnsureLicenseArgs | `LicenseCompiler` | `run` |
| `generate_documentation` | 65 | new_task | full_repo, docs | — | `generate_documentation` | `—` |
| `generate_requirements` | 67 | new_task | full_repo, codebase | — | `RequirementsGenerator` | `generate` |
| `generate_readme` | 70 | new_task, feedback | full_repo, docs | GenerateReadmeArgs | `ReadmeAgent` | `generate_readme` |
| `translate_readme` | 75 | new_task, feedback | full_repo, docs | TranslateReadmeArgs | `ReadmeTranslator` | `translate_readme` |
| `generate_about` | 80 | new_task | full_repo, docs | — | `AboutGenerator` | `generate_about_content` |