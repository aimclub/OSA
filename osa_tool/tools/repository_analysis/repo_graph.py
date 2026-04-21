from pathlib import Path
from typing import Iterable
from typing import Optional

import libcst as cst
import networkx as nx
import torch
import torch.nn as nn
import torch.nn.functional as F
from libcst.metadata import MetadataWrapper, QualifiedNameProvider
from torch_geometric.nn import RGATConv
from torch_geometric.utils import negative_sampling
from transformers import AutoTokenizer, AutoModel

from osa_tool.utils.logger import logger

EDGE_TYPES = ["contains", "imports", "calls"]
NODE_TYPES = ["module", "class", "function"]


class RepositoryGraph:
    """
    Builds a graph representation of a repository.

    Node types: module, class, function
    Edge types: contains, imports, calls
    """

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.resolve()
        self.graph = nx.DiGraph()
        self.__function_name_to_node: dict[str, list[str]] = {}
        self.__graph_embedder = _GraphEmbedder()
        self.__graph_enrich = _GraphEmbeddingTrainer()

    @property
    def nodes(self):
        return self.graph.nodes()

    def build(self, source_files: Iterable[str]) -> nx.DiGraph:
        """
        Main entry point. Accepts a list of absolute file paths
        and returns a populated directed graph.
        """
        for filepath in source_files:
            self._process_file(Path(filepath))

        self.__resolve_calls()
        self.graph = self.__graph_embedder.embed(self.graph)
        self.graph = self.__graph_enrich.train(self.graph)

        return self.graph

    def _process_file(self, filepath: Path) -> None:
        module_id = self.__module_id(filepath)
        source = filepath.read_text(encoding="utf-8", errors="ignore")

        try:
            tree = cst.parse_module(source)
        except cst.ParserSyntaxError:
            return

        self.graph.add_node(
            module_id,
            node_type="module",
            name=module_id,
            file=str(filepath),
            source=source,
        )

        visitor = _RepoVisitor(module_id, filepath, self.repo_path)
        logger.info(f"Processing file: {filepath}")
        logger.info(f"Tree type: {type(tree)}, body length: {len(tree.body)}")
        wrapper = MetadataWrapper(tree)
        wrapper.visit(visitor)

        for node_id, attrs in visitor.nodes:
            self.graph.add_node(node_id, **attrs)

        for src, dst, attrs in visitor.edges:
            self.graph.add_edge(src, dst, **attrs)

        # register function nodes for later call resolution
        for node_id, attrs in visitor.nodes:
            if attrs["node_type"] == "function":
                name = attrs["name"]
                self.__function_name_to_node.setdefault(name, []).append(node_id)

        # register import edges (module -> module)
        for imported_module_name in visitor.imported_modules:
            self.graph.add_node(
                imported_module_name,
                node_type="module",
                name=imported_module_name,
                file=None,
                source=None,
            )
            self.graph.add_edge(
                module_id,
                imported_module_name,
                edge_type="imports",
            )

        # store raw call info for cross-file resolution later
        for caller_id, callee_name in visitor.raw_calls:
            self.graph.nodes[module_id].setdefault("_pending_calls", [])
            # store on the graph object itself for the resolution pass
            if not hasattr(self, "_pending_calls"):
                self._pending_calls: list[tuple[str, str]] = []
            self._pending_calls.append((caller_id, callee_name))

    def __resolve_calls(self) -> None:
        if not hasattr(self, "_pending_calls"):
            return

        for caller_id, callee_name in self._pending_calls:
            candidates = self.__function_name_to_node.get(callee_name, [])
            for callee_id in candidates:
                if caller_id != callee_id:
                    self.graph.add_edge(caller_id, callee_id, edge_type="calls")

    def __module_id(self, filepath: Path) -> str:
        """Converts an absolute file path to a dot-separated module identifier."""
        try:
            rel = filepath.relative_to(self.repo_path)
        except ValueError:
            rel = filepath
        parts = list(rel.with_suffix("").parts)
        return ".".join(parts)


class _RepoVisitor(cst.CSTVisitor):
    def __init__(self, module_id: str, filepath: Path, repo_root: Path):
        super().__init__()

        self.module_id = module_id
        self.filepath = filepath
        self.repo_root = repo_root

        self.nodes: list[tuple[str, dict]] = []
        self.edges: list[tuple[str, str, dict]] = []
        self.imported_modules: list[str] = []
        self.raw_calls: list[tuple[str, str]] = []

        # Stack tracks the current logical parent (module, class, or function)
        self._scope_stack: list[str] = [module_id]

    def visit_Import(self, node: cst.Import) -> None:
        pass  # handled via ImportFrom and ImportStar

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module is not None:
            module_name = self.__dotted_name(node.module)
            if module_name:
                self.imported_modules.append(module_name)

    def visit_Import_names(self, node: cst.Import) -> None:
        if isinstance(node, cst.Import) and isinstance(node.names, (list,)):
            for alias in node.names:
                if isinstance(alias, cst.ImportAlias):
                    name = self.__dotted_name(alias.name)
                    if name:
                        self.imported_modules.append(name)

    def visit_Call(self, node: cst.Call) -> None:
        callee_name = self.__extract_callee_name(node.func)
        if callee_name:
            self.raw_calls.append((self._current_scope(), callee_name))

    def _current_scope(self) -> str:
        return self._scope_stack[-1]

    def __extract_source(self, node: cst.CSTNode) -> str:
        try:
            return cst.parse_module("").code_for_node(node)
        except Exception:
            return ""

    def __dotted_name(self, node: cst.BaseExpression) -> Optional[str]:
        if isinstance(node, cst.Attribute):
            left = self.__dotted_name(node.value)
            right = node.attr.value
            if left:
                return f"{left}.{right}"
            return right
        if isinstance(node, cst.Name):
            return node.value
        return None

    def __extract_callee_name(self, node: cst.BaseExpression) -> Optional[str]:
        if isinstance(node, cst.Name):
            return node.value
        if isinstance(node, cst.Attribute):
            return node.attr.value
        return None


class _GraphEmbedder:
    """
    Init graph node embeddings.
    Each node is embedded using its source text, in isolation.
    Embeddings are stored as 'embedding' attribute on each node in-place.
    """

    MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
    MAX_TOKENS = 512

    def __init__(self, device: Optional[str] = None):
        self.__device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.__tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        self.__model = AutoModel.from_pretrained(self.MODEL_NAME).to(self.__device)
        self.__model.eval()

    def embed(self, graph: nx.DiGraph) -> nx.DiGraph:
        """
        Iterates over all nodes in the graph, computes embeddings
        and stores them as node attributes. Returns the same graph instance.
        """
        for node_id, attrs in graph.nodes(data=True):
            text = self.__prepare_input(attrs)
            embedding = self.__embed_text(text)
            graph.nodes[node_id]["embedding"] = embedding

        return graph

    def __prepare_input(self, attrs: dict) -> str:
        """
        Constructs the text input for a node based on its type and attributes.
        Falls back to node name if no source is available.
        """
        node_type = attrs.get("node_type", "unknown")
        source = attrs.get("source") or ""
        name = attrs.get("name") or ""

        if not source:
            return name

        if node_type == "module":
            return self.__extract_module_docstring(source) or name

        return source

    def __embed_text(self, text: str) -> list[float]:
        """
        Tokenizes text, runs it through and returns the CLS token
        vector as a plain Python list of floats.
        """
        tokens = self.__tokenizer(
            text,
            return_tensors="pt",
            max_length=self.MAX_TOKENS,
            truncation=True,
            padding="max_length",
        )
        tokens = {k: v.to(self.__device) for k, v in tokens.items()}

        with torch.no_grad():
            output = self.__model(**tokens)

        cls_vector = output.last_hidden_state[:, 0, :]
        return cls_vector.squeeze().cpu().tolist()

    def __extract_module_docstring(self, source: str) -> Optional[str]:
        """
        Attempts to extract the module-level docstring from raw source text
        without fully parsing the AST, by looking for the first triple-quoted string.
        """
        import ast

        try:
            tree = ast.parse(source)
            return ast.get_docstring(tree)
        except SyntaxError:
            return None


class _RGATEncoder(nn.Module):
    """
    Relational Graph Attention Network encoder.
    Produces enriched node embeddings using edge-type-specific attention.
    """

    def __init__(
        self,
        in_channels: int = 768,
        hidden_channels: int = 768,
        out_channels: int = 768,
        num_heads: int = 4,
        num_relations: int = len(EDGE_TYPES),
        dropout: float = 0.1,
    ):
        super().__init__()

        self.conv1 = RGATConv(
            in_channels=in_channels,
            out_channels=hidden_channels // num_heads,
            num_relations=num_relations,
            heads=num_heads,
            dropout=dropout,
        )
        self.conv2 = RGATConv(
            in_channels=hidden_channels,
            out_channels=out_channels,
            num_relations=num_relations,
            heads=1,
            dropout=dropout,
        )
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_type: torch.Tensor,
    ) -> torch.Tensor:
        x = self.conv1(x, edge_index, edge_type)
        x = F.elu(x)
        x = self.dropout(x)
        x = self.conv2(x, edge_index, edge_type)
        return x


class _LinkPredictor(nn.Module):
    """
    Predicts whether an edge exists between two nodes by
    computing a score from their embeddings.
    """

    def __init__(self, in_channels: int = 768):
        super().__init__()
        self.linear = nn.Linear(in_channels * 2, 1)

    def forward(
        self,
        src_embeddings: torch.Tensor,
        dst_embeddings: torch.Tensor,
    ) -> torch.Tensor:
        paired = torch.cat([src_embeddings, dst_embeddings], dim=-1)
        return self.linear(paired)


class _GraphEmbeddingTrainer:
    """
    Converts a NetworkX graph with node embeddings into a
    PyTorch Geometric format and trains the RGAT encoder via link prediction.
    """

    def __init__(
        self,
        device: Optional[str] = None,
        lr: float = 1e-4,
        epochs: int = 50,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.lr = lr
        self.epochs = epochs

        self.encoder = _RGATEncoder().to(self.device)
        self.predictor = _LinkPredictor().to(self.device)
        self.optimizer = torch.optim.Adam(
            list(self.encoder.parameters()) + list(self.predictor.parameters()),
            lr=self.lr,
        )

    def train(self, graph: nx.DiGraph) -> nx.DiGraph:
        """
        Trains the RGAT encoder on the given graph and writes enriched
        embeddings back onto the graph nodes. Returns the updated graph.
        """
        data, node_index = self.__convert(graph)

        x = data["x"].to(self.device)
        edge_index = data["edge_index"].to(self.device)
        edge_type = data["edge_type"].to(self.device)

        for epoch in range(self.epochs):
            self.encoder.train()
            self.predictor.train()
            self.optimizer.zero_grad()

            embeddings = self.encoder(x, edge_index, edge_type)
            loss = self.__link_prediction_loss(embeddings, edge_index)

            loss.backward()
            self.optimizer.step()

        self.encoder.eval()
        with torch.no_grad():
            final_embeddings = self.encoder(x, edge_index, edge_type)

        self.__write_embeddings_back(graph, final_embeddings, node_index)
        return graph

    def __link_prediction_loss(
        self,
        embeddings: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        """
        Computes binary cross-entropy loss over positive edges and
        an equal number of randomly sampled negative edges.
        """
        num_nodes = embeddings.size(0)

        neg_edge_index = negative_sampling(
            edge_index=edge_index,
            num_nodes=num_nodes,
            num_neg_samples=edge_index.size(1),
        )

        pos_scores = self.predictor(
            embeddings[edge_index[0]],
            embeddings[edge_index[1]],
        )
        neg_scores = self.predictor(
            embeddings[neg_edge_index[0]],
            embeddings[neg_edge_index[1]],
        )

        pos_loss = F.binary_cross_entropy_with_logits(pos_scores, torch.ones_like(pos_scores))
        neg_loss = F.binary_cross_entropy_with_logits(neg_scores, torch.zeros_like(neg_scores))

        return (pos_loss + neg_loss) / 2

    def __convert(self, graph: nx.DiGraph) -> tuple[dict, dict[str, int]]:
        """
        Converts a NetworkX graph into tensors suitable for RGATConv.
        Returns a data dict with x, edge_index, edge_type and a
        mapping from node_id to integer index.
        """
        nodes = list(graph.nodes(data=True))
        node_index = {node_id: i for i, (node_id, _) in enumerate(nodes)}

        embeddings = []
        for node_id, attrs in nodes:
            emb = attrs.get("embedding")
            if emb is None:
                emb = [0.0] * 768
            embeddings.append(emb)

        x = torch.tensor(embeddings, dtype=torch.float)

        edge_type_map = {et: i for i, et in enumerate(EDGE_TYPES)}
        src_list, dst_list, type_list = [], [], []

        for src, dst, attrs in graph.edges(data=True):
            edge_type = attrs.get("edge_type", "contains")
            src_list.append(node_index[src])
            dst_list.append(node_index[dst])
            type_list.append(edge_type_map.get(edge_type, 0))

        edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)
        edge_type = torch.tensor(type_list, dtype=torch.long)

        return {"x": x, "edge_index": edge_index, "edge_type": edge_type}, node_index

    def __write_embeddings_back(
        self,
        graph: nx.DiGraph,
        embeddings: torch.Tensor,
        node_index: dict[str, int],
    ) -> None:
        """
        Writes the trained RGAT embeddings back onto the NetworkX graph nodes,
        replacing the original embeddings.
        """
        embeddings_cpu = embeddings.cpu().tolist()
        for node_id, idx in node_index.items():
            graph.nodes[node_id]["embedding"] = embeddings_cpu[idx]
