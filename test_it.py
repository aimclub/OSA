from osa_tool.config.settings import ConfigManager
from osa_tool.operations.analysis.repository_validation.paper_parsing.structured_parser import StructuredPaperParser

config = ConfigManager()
settings = config.config.llm.for_validation          # not get_model_settings("validation")

parser = StructuredPaperParser.from_model_settings(
    "/home/lameus/Projects/layout-aware-doc-segmentation/data/kerr_part.pdf", settings
)
print(parser.data_extractor())
