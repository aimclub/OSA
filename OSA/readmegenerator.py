import os
from readmeai.config.settings import ConfigLoader
from readmeai.main import readme_generator

# Path to save README.md
file_to_save = os.path.join(os.getcwd(), "examples", "README.md")
# Path to configs
config_loader = ConfigLoader(config_dir="config")

readme_generator(config_loader, file_to_save)
