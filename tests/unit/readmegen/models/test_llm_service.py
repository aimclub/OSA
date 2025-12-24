from unittest.mock import patch, Mock


def test_get_key_files_returns_list(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=[["src/main.py", "README.md"]])

    # Act
    result = llm_client.get_key_files()

    # Assert
    assert result == ["src/main.py", "README.md"]


def test_get_key_files_invalid_json_returns_fallback_list(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["not a json"])

    # Act
    result = llm_client.get_key_files()

    # Assert
    assert result == "not a json"


def test_get_responses_article_returns_expected(llm_client, mock_model_handler, mock_file_processor_factory):
    # Arrange
    llm_client.model_handler = mock_model_handler(
        side_effect=[
            ["src/main.py", "README.md"],
            "files_summary",
            "pdf_summary",
            "overview_article",
            "content_article",
            "algorithms_article",
            "getting_started_article",
        ]
    )

    key_files_mock = mock_file_processor_factory(
        [
            ("main.py", "src/main.py", "print('hello')"),
            ("README.md", "README.md", "# My Project"),
        ]
    )
    example_files_mock = mock_file_processor_factory(
        [
            ("demo.py", "examples/demo.py", "run()"),
        ]
    )

    with (
        patch("osa_tool.operations.docs.readme_generation.context.files_contents.FileProcessor") as MockFP,
        patch("osa_tool.operations.docs.readme_generation.utils.extract_example_paths") as mock_extract_examples,
        patch("osa_tool.operations.docs.readme_generation.context.article_path.get_pdf_path") as mock_pdf_path,
        patch(
            "osa_tool.operations.docs.readme_generation.context.article_content.PdfParser.data_extractor"
        ) as mock_pdf_extract,
    ):

        def fp_side_effect(config_loader, file_paths):
            if any(f in file_paths for f in ["src/main.py", "README.md"]):
                return key_files_mock
            if "examples/demo.py" in file_paths:
                return example_files_mock
            return Mock()

        MockFP.side_effect = fp_side_effect
        mock_extract_examples.return_value = ["examples/demo.py"]
        mock_pdf_path.return_value = "fake.pdf"
        mock_pdf_extract.return_value = "pdf content"

        # Act
        overview, content, algorithms, getting_started = llm_client.get_responses_article("article.pdf")

    # Assert
    assert overview == "overview_article"
    assert content == "content_article"
    assert algorithms == "algorithms_article"
    assert getting_started == "getting_started_article"


def test_get_responses_returns_expected(llm_client, mock_model_handler, mock_file_processor_factory):
    # Arrange
    llm_client.model_handler = mock_model_handler(
        side_effect=[
            ["src/main.py"],
            "Core features here",
            "Project overview",
            "Run it",
        ]
    )

    key_files_mock = mock_file_processor_factory([("main.py", "src/main.py", "def main(): pass")])
    example_files_mock = mock_file_processor_factory([("demo.py", "examples/demo.py", "main()")])

    with (
        patch("osa_tool.operations.docs.readme_generation.context.files_contents.FileProcessor") as MockFP,
        patch("osa_tool.operations.docs.readme_generation.utils.extract_example_paths") as mock_extract,
    ):

        def fp_side_effect(config_loader, files_list):
            if "src/main.py" in files_list:
                return key_files_mock
            if "examples/demo.py" in files_list:
                return example_files_mock
            return Mock()

        MockFP.side_effect = fp_side_effect
        mock_extract.return_value = ["examples/demo.py"]

        # Act
        core, overview, getting_started = llm_client.get_responses()

    # Assert
    assert core == "Core features here"
    assert overview == "Project overview"
    assert getting_started == "Run it"


def test_get_citation_from_readme_returns_expected(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["Some citation"])

    # Act
    result = llm_client.get_citation_from_readme()

    # Assert
    assert result == "Some citation"


def test_refine_readme_returns_expected(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["step1", "step2", "refined_readme"])

    # Act
    result = llm_client.refine_readme("generated_readme")

    # Assert
    assert result == "refined_readme"


def test_clean_returns_expected(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["clean1", "clean2", "cleaned_readme"])

    # Act
    result = llm_client.clean("dirty_readme")

    # Assert
    assert result == "cleaned_readme"


def test_get_article_name_returns_expected(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["Deep Learning Paper"])

    # Act
    result = llm_client.get_article_name("pdf_content")

    # Assert
    assert result == "Deep Learning Paper"
