import os
import argparse
from readmeai.config.settings import ConfigLoader, GitSettings
from readmeai.main import readme_generator


def main():
    # Create a command line argument parser
    parser = argparse.ArgumentParser(
        description="Generate README.md for a GitHub repository"
    )
    parser.add_argument("repo_url",
                        type=str,
                        help="URL of the GitHub repository"
                        )

    args = parser.parse_args()
    repo_url = args.repo_url

    readme_agent(repo_url)


def readme_agent(repo_url: str) -> None:
    # Loading configurations and updating repo_url
    config_loader = ConfigLoader(config_dir="OSA/config")
    config_loader.config.git = GitSettings(repository=repo_url)

    # Path to save README.md
    output_dir = os.path.join(os.getcwd(),
                              "examples",
                              config_loader.config.git.name,
                              )
    os.makedirs(output_dir, exist_ok=True)
    file_to_save = os.path.join(output_dir, "README.md")

    # Generate README.md
    readme_generator(config_loader, file_to_save)


if __name__ == "__main__":
    main()
