import pytest
import sys
from osa_tool.arguments_parser import get_cli_args


class TestArgumentParser:

    @pytest.fixture
    def repo_url(self):
        return "https://github.com/user/repo"

    @staticmethod
    def run_parser(args):
        sys.argv = ["arguments_parser.py"] + args
        return get_cli_args()

    def test_required_repository(self):
        with pytest.raises(SystemExit):
            self.run_parser([])

    def test_repository_url(self, repo_url):
        args = self.run_parser(["-r", repo_url])
        assert args.repository == repo_url

        args = self.run_parser(["--repository", repo_url])
        assert args.repository == repo_url

    def test_default_api(self, repo_url):
        args = self.run_parser(["-r", repo_url])
        assert args.api == "llama"

    def test_api_choice(self, repo_url):
        api_choice = ["llama", "openai", "ollama"]
        for api in api_choice:
            args = self.run_parser(["-r", repo_url, "--api", api])
            assert args.api == api

        with pytest.raises(SystemExit):
            self.run_parser(["-r", repo_url, "--api", "invalid_api"])

    def test_base_url(self, repo_url):
        custom_base_url = "https://custom-api.com/v1"
        args = self.run_parser(["-r", repo_url, "--base-url", custom_base_url])
        assert args.base_url == custom_base_url

    def test_default_base_url(self, repo_url):
        args = self.run_parser(["-r", repo_url])
        assert args.base_url == "https://api.openai.com/v1"

    def test_model_selection(self, repo_url):
        model_choice = "gpt-4"
        args = self.run_parser(["-r", repo_url, "--model", model_choice])
        assert args.model == model_choice

    def test_default_model(self, repo_url):
        args = self.run_parser(["-r", repo_url])
        assert args.model == "gpt-3.5-turbo"

    def test_article_flag(self, repo_url):
        article_url = "https://example.com/article.pdf"

        args = self.run_parser(["-r", repo_url, "--article"])
        assert args.article == ""

        args = self.run_parser(["-r", repo_url, "--article", article_url])
        assert args.article == article_url

    def test_translate_dirs_flag(self, repo_url):
        args = self.run_parser(["-r", repo_url, "--translate-dirs"])
        assert args.translate_dirs is True

        args = self.run_parser(["-r", repo_url])
        assert args.translate_dirs is False
