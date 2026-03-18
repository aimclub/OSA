from unittest.mock import MagicMock, patch

from osa_tool.utils.token_counter import count_tokens, truncate_to_tokens


class TestCountTokens:

    def test_empty_string_returns_zero(self):
        assert count_tokens("") == 0

    def test_none_returns_zero(self):
        assert count_tokens(None) == 0

    def test_returns_positive_for_non_empty(self):
        result = count_tokens("hello world")
        assert result > 0

    def test_longer_text_has_more_tokens(self):
        short = count_tokens("hello")
        long = count_tokens("hello world, this is a longer sentence with more tokens")
        assert long > short

    @patch("osa_tool.utils.token_counter._get_encoder")
    def test_uses_specified_encoding(self, mock_get_encoder):
        mock_enc = MagicMock()
        mock_enc.encode.return_value = [1, 2, 3]
        mock_get_encoder.return_value = mock_enc

        result = count_tokens("test text", "p50k_base")

        mock_get_encoder.assert_called_with("p50k_base")
        assert result == 3


class TestTruncateToTokens:

    def test_empty_string_returns_empty(self):
        assert truncate_to_tokens("", 100) == ""

    def test_zero_budget_returns_empty(self):
        assert truncate_to_tokens("hello world", 0) == ""

    def test_short_text_unchanged(self):
        text = "hello"
        result = truncate_to_tokens(text, 1000)
        assert result == text

    @patch("osa_tool.utils.token_counter._get_encoder")
    def test_start_mode_keeps_beginning(self, mock_get_encoder):
        mock_enc = MagicMock()
        mock_enc.encode.return_value = [10, 20, 30, 40, 50]
        mock_enc.decode.return_value = "first three"
        mock_get_encoder.return_value = mock_enc

        result = truncate_to_tokens("full text", 3, mode="start")

        mock_enc.decode.assert_called_once_with([10, 20, 30])
        assert result == "first three"

    @patch("osa_tool.utils.token_counter._get_encoder")
    def test_end_mode_keeps_end(self, mock_get_encoder):
        mock_enc = MagicMock()
        mock_enc.encode.return_value = [10, 20, 30, 40, 50]
        mock_enc.decode.return_value = "last three"
        mock_get_encoder.return_value = mock_enc

        result = truncate_to_tokens("full text", 3, mode="end")

        mock_enc.decode.assert_called_once_with([30, 40, 50])
        assert result == "last three"

    @patch("osa_tool.utils.token_counter._get_encoder")
    def test_middle_out_mode_keeps_both_ends(self, mock_get_encoder):
        mock_enc = MagicMock()
        mock_enc.encode.return_value = [10, 20, 30, 40, 50, 60]
        mock_enc.decode.return_value = "both ends"
        mock_get_encoder.return_value = mock_enc

        result = truncate_to_tokens("full text", 4, mode="middle-out")

        # half = 4 // 2 = 2 → first 2 + last 2
        mock_enc.decode.assert_called_once_with([10, 20, 50, 60])
        assert result == "both ends"

    @patch("osa_tool.utils.token_counter._get_encoder")
    def test_text_within_budget_returned_as_is(self, mock_get_encoder):
        mock_enc = MagicMock()
        mock_enc.encode.return_value = [10, 20, 30]
        mock_get_encoder.return_value = mock_enc

        result = truncate_to_tokens("short text", 10)

        assert result == "short text"
        mock_enc.decode.assert_not_called()
