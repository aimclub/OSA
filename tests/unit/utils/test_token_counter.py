from unittest.mock import MagicMock, patch

from osa_tool.utils.token_counter import count_tokens, truncate_to_tokens


def test_empty_string_returns_zero():
    # Act
    n = count_tokens("")

    # Assert
    assert n == 0


def test_none_returns_zero():
    # Act
    n = count_tokens(None)

    # Assert
    assert n == 0


def test_returns_positive_for_non_empty():
    # Act
    result = count_tokens("hello world")

    # Assert
    assert result > 0


def test_longer_text_has_more_tokens():
    # Act
    short = count_tokens("hello")
    long = count_tokens("hello world, this is a longer sentence with more tokens")

    # Assert
    assert long > short


@patch("osa_tool.utils.token_counter._get_encoder")
def test_uses_specified_encoding(mock_get_encoder):
    # Arrange
    mock_enc = MagicMock()
    mock_enc.encode.return_value = [1, 2, 3]
    mock_get_encoder.return_value = mock_enc

    # Act
    result = count_tokens("test text", "p50k_base")

    # Assert
    mock_get_encoder.assert_called_with("p50k_base")
    assert result == 3


def test_truncate_empty_string_returns_empty():
    # Act
    out = truncate_to_tokens("", 100)

    # Assert
    assert out == ""


def test_truncate_zero_budget_returns_empty():
    # Act
    out = truncate_to_tokens("hello world", 0)

    # Assert
    assert out == ""


def test_truncate_short_text_unchanged():
    # Arrange
    text = "hello"

    # Act
    result = truncate_to_tokens(text, 1000)

    # Assert
    assert result == text


@patch("osa_tool.utils.token_counter._get_encoder")
def test_truncate_start_mode_keeps_beginning(mock_get_encoder):
    # Arrange
    mock_enc = MagicMock()
    mock_enc.encode.return_value = [10, 20, 30, 40, 50]
    mock_enc.decode.return_value = "first three"
    mock_get_encoder.return_value = mock_enc

    # Act
    result = truncate_to_tokens("full text", 3, mode="start")

    # Assert
    mock_enc.decode.assert_called_once_with([10, 20, 30])
    assert result == "first three"


@patch("osa_tool.utils.token_counter._get_encoder")
def test_truncate_end_mode_keeps_end(mock_get_encoder):
    # Arrange
    mock_enc = MagicMock()
    mock_enc.encode.return_value = [10, 20, 30, 40, 50]
    mock_enc.decode.return_value = "last three"
    mock_get_encoder.return_value = mock_enc

    # Act
    result = truncate_to_tokens("full text", 3, mode="end")

    # Assert
    mock_enc.decode.assert_called_once_with([30, 40, 50])
    assert result == "last three"


@patch("osa_tool.utils.token_counter._get_encoder")
def test_truncate_middle_out_mode_keeps_both_ends(mock_get_encoder):
    # Arrange
    mock_enc = MagicMock()
    mock_enc.encode.return_value = [10, 20, 30, 40, 50, 60]
    mock_enc.decode.return_value = "both ends"
    mock_get_encoder.return_value = mock_enc

    # Act
    result = truncate_to_tokens("full text", 4, mode="middle-out")

    # Assert
    mock_enc.decode.assert_called_once_with([10, 20, 50, 60])
    assert result == "both ends"


@patch("osa_tool.utils.token_counter._get_encoder")
def test_truncate_text_within_budget_returned_as_is(mock_get_encoder):
    # Arrange
    mock_enc = MagicMock()
    mock_enc.encode.return_value = [10, 20, 30]
    mock_get_encoder.return_value = mock_enc

    # Act
    result = truncate_to_tokens("short text", 10)

    # Assert
    assert result == "short text"
    mock_enc.decode.assert_not_called()
