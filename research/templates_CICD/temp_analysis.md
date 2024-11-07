Ссылки на список шаблонов для настройки CI/CD:
-
[**Репозиторий awesome-actions**](https://github.com/sdras/awesome-actions?tab=readme-ov-file#community-resources)

[**Маркетплейс**](https://github.com/marketplace?type=actions)

Инструменты от команды GitHub Actions:
-
1. [**Super-Linter**](https://github.com/marketplace/actions/super-linter)

Набор линтеров и анализаторов кода.
- Поддерживает большое количество языков программирования
- Распараллеливание запуска линтеров
- Запуск в github actions

2. [**Checkout**](https://github.com/marketplace/actions/checkout)

Позволяет получить доступ процессу к репозиторию.
- Настройка извлечения файлов (от корневых файлов до всех версий и ветвей)
- Работа с несколькими репозиториями одновременно

3. [**Cache**](https://github.com/marketplace/actions/cache)

Позволяет кэшировать зависимости и собирать выходные данные для сокращения времени выполнения рабочего процесса.

4. [**Setup Python**](https://github.com/marketplace/actions/setup-python)

- Установка версии Python или PyPy и (по умолчанию) добавление ее в PATH
- Необязательное кэширование зависимостей для pip, pipenv и poetry
- Регистрация сопоставителей проблем для вывода ошибок

5. [**Labeler**](https://github.com/marketplace/actions/labeler)

Автоматически маркирует новые запросы на основе пути к изменяемым файлам или имени ветки.

Другие инструменты:
-
1. [**TruffleHog OSS**](https://github.com/marketplace/actions/trufflehog-oss)

Инструмент для обнаружения, классификации, проверки и анализа секретов.
- Поиск секретов в Git, чатах, вики, логах, платформах тестирования API, хранилищах, файловых системах и других.

2. [**OpenCommit (BETA)**](https://github.com/marketplace/actions/opencommit-improve-commits-with-ai)

Переименовывает коммиты из непонятных `fix1` в более осмысленные.
- Основан на работе с LLM (OpenAI, LLama и другие)

3. [**GH Release**](https://github.com/marketplace/actions/gh-release)

Используется для создания релизов GitHub в виртуальных средах Linux, Windows и macOS.

4. [**mirror-repository**](https://github.com/marketplace/actions/mirror-repository)

Используется для зеркалирования коммитов в другие удаленные репозитории.

- Зеркало на GitLab, BitBucket или другие GitHub репозитории.
- Так же есть несколько похожих инструментов: [Repo Mirror Sync](https://github.com/marketplace/actions/repo-mirror-sync), [Mirroring Repository](https://github.com/marketplace/actions/mirroring-repository)

5. [**Publish a Python distribution package to PyPI**](https://github.com/marketplace/actions/pypi-publish)

Позволяет загружать пакеты Python в каталог PyPI

Инструменты Docker:
-
1. [**Docker Login**](https://github.com/marketplace/actions/docker-login)

Используется для входа в реестр Docker.

2. [**Build and push Docker images**](https://github.com/marketplace/actions/build-and-push-docker-images)

Используется для сборки и отправки образов Docker с помощью Buildx с полной поддержкой функций, предоставляемых набором инструментов Moby BuildKit builder. Включает в себя многоплатформенную сборку, секреты, удаленный кэш и т. д., а также различные варианты развертывания/пространства имен builder.

3. [**Docker Setup Buildx**](https://github.com/marketplace/actions/docker-setup-buildx)

Используется для настройки Buildx.

4. [**Docker Metadata action**](https://github.com/marketplace/actions/docker-metadata-action)

Используется для извлечения метаданных.

