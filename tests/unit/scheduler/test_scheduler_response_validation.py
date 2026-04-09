from osa_tool.scheduler.response_validation import PromptConfig


def test_prompt_config_safe_validate_coerces_invalid_field():
    # Arrange
    raw = {"readme": "not-a-bool", "report": True}

    # Act
    cfg = PromptConfig.safe_validate(raw)

    # Assert
    assert cfg.report is True
    assert cfg.readme is False


def test_prompt_config_safe_validate_ignores_unknown_keys():
    # Arrange
    raw = {"readme": True, "unknown_future_flag": 123}

    # Act
    cfg = PromptConfig.safe_validate(raw)

    # Assert
    assert cfg.readme is True
