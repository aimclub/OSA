from unittest.mock import patch, Mock


def test_get_key_files_returns_list(llm_client, mock_model_handler):
    """
    Tests that the get_key_files method returns a list.
    
    This test verifies that the LLMClient.get_key_files method correctly
    returns a list of file paths when the model handler provides them.
    The test uses mocking to isolate the client from actual model inference,
    ensuring the unit test focuses solely on the client's handling of the response.
    
    Args:
        llm_client: The LLMClient instance to test.
        mock_model_handler: Factory fixture to create a mocked ModelHandler.
    
    Returns:
        None
    """
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=[["src/main.py", "README.md"]])

    # Act
    result = llm_client.get_key_files()

    # Assert
    assert result == ["src/main.py", "README.md"]


def test_get_key_files_invalid_json_returns_fallback_list(llm_client, mock_model_handler):
    """
    Tests that get_key_files returns the fallback list when the model returns invalid JSON.
    
    This test ensures that when the model's response is not valid JSON, the method defaults to returning a predefined fallback list. This fallback behavior is important for maintaining robustness when model inference fails or returns malformed data.
    
    Args:
        llm_client: The LLMClient instance under test.
        mock_model_handler: A fixture to mock the ModelHandler, configured to return a non-JSON string.
    
    Returns:
        None
    """
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["not a json"])

    # Act
    result = llm_client.get_key_files()

    # Assert
    assert result == "not a json"


def test_get_responses_article_returns_expected(llm_client, mock_model_handler, mock_file_processor_factory):
    """
    Tests that `get_responses_article` returns the expected tuple of article sections.
    
    This test mocks the `ModelHandler` to return a predefined sequence of responses,
    mocks the `FileProcessor` to return specific file contents, and patches several
    dependencies to control the test environment. It then calls the method under test
    and asserts the returned values match the expected mocked responses.
    
    The test simulates the full flow of `get_responses_article` by mocking external dependencies (file processing, PDF parsing, and model inference) to verify that the method correctly processes inputs and returns the four expected article sections in the proper order.
    
    Args:
        llm_client: The LLMClient instance under test.
        mock_model_handler: Pytest fixture that creates a mocked ModelHandler. The mock is configured to return a sequence of seven predefined responses, corresponding to the steps of the article generation process.
        mock_file_processor_factory: Pytest fixture that creates a mocked FileProcessor factory. It is used to simulate the processing of key files (e.g., main.py, README.md) and example files (e.g., demo.py) with controlled content.
    
    Returns:
        None
    """
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

        def fp_side_effect(config_manager, file_paths):
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
    """
    Tests that get_responses returns the expected tuple of strings.
    
    This test verifies that the LLMClient.get_responses method correctly returns
    a tuple containing the core features, overview, and getting started sections
    as generated by the mocked model handler, using mocked file processors.
    The test sets up specific mock return values for the model handler and file processors,
    then calls get_responses and asserts that each returned string matches the expected mock output.
    
    Args:
        llm_client: The LLMClient instance under test.
        mock_model_handler: A fixture to create a mocked ModelHandler. The mock is configured to return a predefined sequence of responses when its send_and_parse method is called.
        mock_file_processor_factory: A fixture to create a mocked FileProcessor. The mock is set up to return specific file contexts based on the input file list.
    
    Returns:
        None
    """
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

        def fp_side_effect(config_manager, files_list):
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
    """
    Tests that get_citation_from_readme returns the expected citation.
    
    This test method uses a mocked model handler to verify that the
    llm_client.get_citation_from_readme method correctly returns the citation
    provided by the mock. The mock is configured to simulate a specific response,
    allowing the test to validate the method's behavior in isolation without
    actual model inference.
    
    Args:
        llm_client: The LLM client instance being tested.
        mock_model_handler: Factory fixture to create a mocked ModelHandler.
    
    Returns:
        None
    """
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["Some citation"])

    # Act
    result = llm_client.get_citation_from_readme()

    # Assert
    assert result == "Some citation"


def test_refine_readme_returns_expected(llm_client, mock_model_handler):
    """
    Tests that the refine_readme method returns the expected refined README.
    
    This test verifies that the LLM client's refine_readme method correctly processes a generated README through multiple refinement steps and returns the final refined output. It uses a mocked ModelHandler to simulate the sequential responses of the refinement process without performing actual model inference.
    
    Args:
        llm_client: The LLM client instance to test.
        mock_model_handler: Factory fixture to create a mocked ModelHandler.
    
    Returns:
        None
    """
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["step1", "step2", "refined_readme"])

    # Act
    result = llm_client.refine_readme("generated_readme")

    # Assert
    assert result == "refined_readme"


def test_clean_returns_expected(llm_client, mock_model_handler):
    """
    Tests that the clean method returns the expected cleaned result.
    
    This test verifies that the LLM client's clean method correctly processes a dirty input and returns the final cleaned output as provided by the mocked model handler. The mock is configured to simulate a sequence of intermediate responses before returning the final expected result.
    
    Args:
        llm_client: The LLM client instance under test.
        mock_model_handler: Factory fixture to create a mocked ModelHandler.
    
    Returns:
        None
    """
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["clean1", "clean2", "cleaned_readme"])

    # Act
    result = llm_client.clean("dirty_readme")

    # Assert
    assert result == "cleaned_readme"


def test_get_article_name_returns_expected(llm_client, mock_model_handler):
    """
    Tests that get_article_name returns the expected article name.
    
    This test verifies that the LLM client's get_article_name method correctly returns an article name
    when provided with PDF content. It uses a mocked ModelHandler to simulate a model response,
    ensuring the test is isolated and does not depend on actual model inference.
    
    Args:
        llm_client: The LLM client instance under test.
        mock_model_handler: Factory fixture to create a mocked ModelHandler with custom side effects.
            The fixture is configured to return a predetermined response ("Deep Learning Paper")
            when the model's send_and_parse method is called.
    
    Returns:
        None.
    """
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["Deep Learning Paper"])

    # Act
    result = llm_client.get_article_name("pdf_content")

    # Assert
    assert result == "Deep Learning Paper"
