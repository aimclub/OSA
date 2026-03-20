import pytest

from osa_tool.scheduler.response_validation import PromptConfig


def test_prompt_config_default_values():
    """
    Verifies that a new instance of PromptConfig is initialized with the correct default boolean and None values.
    
    This test case ensures that all configuration flags (report, translate_dirs, docstring, ensure_license, community_docs, readme, organize, and about) are set to their expected initial states. This is important because the PromptConfig object controls which documentation and enhancement features are enabled when the OSA Tool processes a repository. Validating defaults helps prevent unintended behavior from incorrect initial configurations.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    config = PromptConfig()

    # Assert
    assert config.report is False
    assert config.translate_dirs is False
    assert config.docstring is False
    assert config.ensure_license is None
    assert config.community_docs is False
    assert config.readme is False
    assert config.organize is False
    assert config.about is False


def test_prompt_config_with_valid_data():
    """
    Verifies that the PromptConfig class correctly initializes all fields when provided with a valid dictionary of configuration data.
    
    This test ensures that when a dictionary with all expected configuration keys and valid values is passed to the PromptConfig constructor, each corresponding attribute is properly set on the resulting instance. It validates the basic initialization behavior of the configuration class.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    data = {
        "report": True,
        "translate_dirs": True,
        "docstring": True,
        "ensure_license": "mit",
        "community_docs": True,
        "readme": True,
        "organize": True,
        "about": True,
    }
    config = PromptConfig(**data)

    # Assert
    assert config.report is True
    assert config.translate_dirs is True
    assert config.docstring is True
    assert config.ensure_license == "mit"
    assert config.community_docs is True
    assert config.readme is True
    assert config.organize is True
    assert config.about is True


def test_prompt_config_with_invalid_license():
    """
    Verifies that the PromptConfig class correctly handles and stores an invalid license string.
    
    This test case ensures that the configuration object accepts the 'ensure_license' input during initialization and assigns it to the corresponding attribute without modification or validation errors at the object level. The test is important because it confirms that the configuration does not perform any implicit validation or transformation of the license string, allowing invalid values to be stored as provided.
    
    Args:
        data: A dictionary containing the key 'ensure_license' with a test value.
        config: An instance of PromptConfig initialized with the test data.
    
    Steps:
        1. Arrange: Prepare test data with an invalid license string.
        2. Act: Instantiate PromptConfig with the test data.
        3. Assert: Verify that the 'ensure_license' attribute matches the input exactly.
    """
    # Arrange
    data = {"ensure_license": "invalid_license"}
    config = PromptConfig(**data)

    # Assert
    assert config.ensure_license == "invalid_license"


def test_prompt_config_extra_fields_ignored():
    """
    Verifies that the PromptConfig class ignores any extra fields provided during initialization.
    
    This test ensures that when a dictionary containing unexpected keys is unpacked into the PromptConfig constructor, only the defined attributes are set and the additional fields are not attached to the resulting object. This behavior is important for maintaining a strict schema and preventing accidental attribute creation from arbitrary input data.
    
    Args:
        data: A dictionary containing both a valid key ("report") and an extra key ("extra_field") to test the ignore behavior.
        config: An instance of PromptConfig created by unpacking the data dictionary.
    
    The test confirms:
        - The valid attribute ("report") is correctly set on the config object.
        - The extra field is not attached as an attribute to the config object.
    """
    # Arrange
    data = {"report": True, "extra_field": "should_be_ignored"}
    config = PromptConfig(**data)

    # Assert
    assert config.report is True
    assert not hasattr(config, "extra_field")


def test_prompt_config_safe_validate_with_valid_data():
    """
    Tests that `PromptConfig.safe_validate` correctly processes a dictionary of valid data.
    
    This test verifies that when a complete and valid data dictionary is provided
    to the `safe_validate` method, the resulting `PromptConfig` object is instantiated
    with all field values matching the input data. This ensures the validation
    process does not alter or default any values when the input is fully correct.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    data = {
        "report": True,
        "translate_dirs": False,
        "docstring": True,
        "ensure_license": "bsd-3",
        "community_docs": False,
        "readme": True,
        "organize": False,
        "about": True,
    }

    # Act
    config = PromptConfig.safe_validate(data)

    # Assert
    assert config.report is True
    assert config.translate_dirs is False
    assert config.docstring is True
    assert config.ensure_license == "bsd-3"
    assert config.community_docs is False
    assert config.readme is True
    assert config.organize is False
    assert config.about is True


def test_prompt_config_safe_validate_with_invalid_types():
    """
    Tests the safe_validate method of PromptConfig with input containing invalid data types.
    
    This test verifies that when the safe_validate method receives a dictionary
    where some values have incorrect types (e.g., a string where a boolean is expected),
    the method correctly handles these by falling back to default values for the
    affected fields while preserving valid values. This ensures robust configuration
    handling, preventing crashes due to malformed input while maintaining valid
    configuration where possible.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    data = {
        "report": "not_a_boolean",
        "translate_dirs": True,
        "docstring": 123,
        "ensure_license": "mit",
        "community_docs": "not_boolean",
        "readme": True,
        "organize": None,
        "about": True,
    }

    # Act
    config = PromptConfig.safe_validate(data)

    # Assert
    assert config.report is False
    assert config.translate_dirs is True
    assert config.docstring is False
    assert config.ensure_license == "mit"
    assert config.community_docs is False
    assert config.readme is True
    assert config.organize is False
    assert config.about is True


def test_prompt_config_safe_validate_with_missing_fields():
    """
    Tests that `PromptConfig.safe_validate` correctly applies default values when required fields are missing.
    
    This test verifies that when a data dictionary is passed to `PromptConfig.safe_validate`
    containing only a subset of the expected fields, the resulting configuration object
    has the provided value for the given field and default values for all other fields.
    The test ensures the validation method gracefully handles incomplete input without error,
    which is critical for robust configuration handling in the OSA Tool.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    data = {
        "report": True,
    }

    # Act
    config = PromptConfig.safe_validate(data)

    # Assert
    assert config.report is True
    assert config.translate_dirs is False
    assert config.docstring is False
    assert config.ensure_license is None
    assert config.community_docs is False
    assert config.readme is False
    assert config.organize is False
    assert config.about is False


def test_prompt_config_safe_validate_empty_data():
    """
    Tests that safe_validate returns a PromptConfig with default values when given empty data.
    
    This test verifies that when the safe_validate method is called with an empty
    dictionary, the resulting PromptConfig object has all its boolean flags set to
    False and the ensure_license field set to None, which are the expected default
    states. This ensures the validation method gracefully handles missing input by
    falling back to defaults, preventing configuration errors.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    data = {}

    # Act
    config = PromptConfig.safe_validate(data)

    # Assert
    assert config.report is False
    assert config.translate_dirs is False
    assert config.docstring is False
    assert config.ensure_license is None
    assert config.community_docs is False
    assert config.readme is False
    assert config.organize is False
    assert config.about is False


@pytest.mark.parametrize("license_value", ["bsd-3", "mit", "ap2", None, "gpl-3.0", "apache-2.0"])
def test_prompt_config_ensure_license_valid_values(license_value):
    """
    Verifies that the PromptConfig class correctly accepts and stores valid license values when provided via the 'ensure_license' field.
    
    Args:
        license_value: The license identifier or value being tested. This includes common open-source licenses like 'mit', 'apache-2.0', 'gpl-3.0', 'bsd-3', a custom identifier like 'ap2', or None to represent no license requirement.
    
    Why:
        This test ensures that the PromptConfig constructor properly handles a variety of valid license inputs without raising errors, confirming that the 'ensure_license' attribute is set exactly as provided. This validation is crucial for the tool's documentation automation, as license information is a key part of repository metadata and compliance.
    """
    # Arrange
    data = {"ensure_license": license_value}
    config = PromptConfig(**data)

    # Assert
    assert config.ensure_license == license_value


@pytest.mark.parametrize(
    "field_name", ["report", "translate_dirs", "docstring", "community_docs", "readme", "organize", "about"]
)
def test_prompt_config_boolean_fields_true(field_name):
    """
    Verifies that boolean configuration fields of PromptConfig are correctly set to True when initialized.
    
    This test ensures that each boolean field in PromptConfig properly accepts and stores a True value, confirming the configuration's integrity for enabling various tool features.
    
    Args:
        field_name: The name of the boolean attribute in the PromptConfig class to be tested. Valid values are: "report", "translate_dirs", "docstring", "community_docs", "readme", "organize", and "about".
    
    Returns:
        None.
    """
    # Arrange
    data = {field_name: True}
    config = PromptConfig(**data)

    # Assert
    assert getattr(config, field_name) is True


@pytest.mark.parametrize(
    "field_name", ["report", "translate_dirs", "docstring", "community_docs", "readme", "organize", "about"]
)
def test_prompt_config_boolean_fields_false(field_name):
    """
    Verifies that the boolean configuration fields of PromptConfig are correctly initialized to False when explicitly set to False in the input data.
    
    This test ensures that each boolean field in PromptConfig properly retains a False value when provided, confirming the configuration's correct handling of default or explicit false states. The test is parameterized to cover all relevant boolean fields.
    
    Args:
        field_name: The name of the boolean field being tested. Acceptable values are: "report", "translate_dirs", "docstring", "community_docs", "readme", "organize", and "about".
    
    Returns:
        None.
    """
    # Arrange
    data = {field_name: False}
    config = PromptConfig(**data)

    # Assert
    assert getattr(config, field_name) is False
