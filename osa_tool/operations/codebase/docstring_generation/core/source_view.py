class SourceView:
    def __init__(self, source: str):
        self.source = source
        self.bytes = source.encode("utf-8")

    def text(self, node):
        return self.bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
