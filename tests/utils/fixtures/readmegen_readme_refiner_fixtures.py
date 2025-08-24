import json


class DummyLLM:
    def __init__(self, response=None):
        self.called_with = None
        self.response = response or json.dumps(
            {"badges": "BADGES", "Introduction": "Intro text", "Usage": "Usage text"}
        )

    def refine_readme(self, sections):
        self.called_with = sections
        return self.response
