import pytest
import sys
from osa_tool.arguments_parser import get_cli_args


class TestArgumentParser:
    @staticmethod
    def run_parser(args):
        sys.argv = ["arguments_parser.py"] + args
        return get_cli_args()

    def test_required_repository(self):
        # Assert
        with pytest.raises(SystemExit):
            self.run_parser([])

    def test_repository_url_short(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url])
        # Assert
        assert args.repository == repo_url

    def test_repository_url_long(self, repo_url):
        # Act
        args = self.run_parser(["--repository", repo_url])
        # Assert
        assert args.repository == repo_url

    def test_default_api(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url])
        # Assert
        assert args.api == "llama"

    @pytest.mark.parametrize("api", ["llama", "openai", "ollama"])
    def test_api_choice(self, repo_url, api):
        # Act
        args = self.run_parser(["-r", repo_url, "--api", api])
        # Assert
        assert args.api == api

    def test_api_choice_error(self, repo_url):
        # Assert
        with pytest.raises(SystemExit):
            self.run_parser(["-r", repo_url, "--api", "invalid_api"])

    def test_base_url(self, repo_url):
        # Arrange
        custom_base_url = "https://custom-api.com/v1"
        # Act
        args = self.run_parser(["-r", repo_url, "--base-url", custom_base_url])
        # Assert
        assert args.base_url == custom_base_url

    def test_default_base_url(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url])
        # Assert
        assert args.base_url == "https://api.openai.com/v1"

    def test_model_selection(self, repo_url):
        # Arrange
        model_choice = "gpt-4"
        # Act
        args = self.run_parser(["-r", repo_url, "--model", model_choice])
        # Assert
        assert args.model == model_choice

    def test_default_model(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url])
        # Assert
        assert args.model == "gpt-3.5-turbo"

    @pytest.mark.parametrize("article", ["https://example.com/article.pdf", ""])
    def test_article_flag(self, repo_url, article):
        # Act
        args = self.run_parser(["-r", repo_url, "--article", article])
        # Assert
        assert args.article == article

    def test_translate_flag_true(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url, "--translate-dirs"])
        # Assert
        assert args.translate_dirs is True

    def test_translate_flag_false(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url])
        # Assert
        assert args.translate_dirs is False

    def test_delete_dir_flag_true(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url, "--delete-dir"])
        # Assert
        assert args.delete_dir is True

    def test_delete_dir_flag_false(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url])
        # Assert
        assert args.delete_dir is False

    def test_ensure_license_default(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url])
        # Assert
        assert args.ensure_license is None

    @pytest.mark.parametrize("license_type", ["bsd-3", "mit", "ap2"])
    def test_ensure_license_choices(self, repo_url, license_type):
        # Act
        args = self.run_parser(["-r", repo_url, "--ensure-license", license_type])
        # Assert
        assert args.ensure_license == license_type

    def test_ensure_license_const_value(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url, "--ensure-license"])
        # Assert
        assert args.ensure_license == "bsd-3"

    def test_ensure_license_invalid_choice(self, repo_url):
        # Assert
        with pytest.raises(SystemExit):
            self.run_parser(["-r", repo_url, "--ensure-license", "invalid_license"])

    def test_not_publish_flag_true(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url, "--not-publish-results"])
        # Assert
        assert args.not_publish_results is True

    def test_not_publish_flag_false(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url])
        # Assert
        assert args.not_publish_results is False

    def test_community_docs_flag_true(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url, "--community-docs"])
        # Assert
        assert args.community_docs is True

    def test_community_docs_flag_false(self, repo_url):
        # Act
        args = self.run_parser(["-r", repo_url])
        # Assert
        assert args.community_docs is False
