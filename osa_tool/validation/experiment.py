class Experiment:
    def __init__(self, description_from_paper=""):
        self.description_from_paper = description_from_paper
        self.impl_src_path = ""  # implementation of experiment in the provided repo
        self.missing = ""
        self.correspondence_percent = None
