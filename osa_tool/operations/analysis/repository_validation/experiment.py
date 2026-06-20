class Experiment:
    def __init__(
        self, description_from_paper="", impl_src_path="", reasoning="", missing="", correspondence_percent=None
    ):
        self.description_from_paper = description_from_paper
        self.impl_src_path = impl_src_path  # implementation of experiment in the provided repo
        self.reasoning = reasoning
        self.missing = missing
        self.correspondence_percent = correspondence_percent
