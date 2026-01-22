from typing import List, Set, Tuple
from collections import defaultdict, deque
from osa_tool.utils.logger import logger


class DependencyGraph:
    """
    Builds and manages dependency graph for functions/methods.

    The graph represents "who calls whom" relationships where:
    - Node: unique identifier for a function/method (file_path:function_name)
    - Edge: A → B means "A calls B" (A depends on B)

    Topological sort ensures B is processed before A.
    """

    def __init__(self, parsed_structure: dict):
        """
        Initialize dependency graph from parsed structure.

        Args:
            parsed_structure: Output from OSA_TreeSitter.analyze_directory()
                Format: {file_path: {"structure": [...], "imports": {...}}}
        """
        self.parsed_structure = parsed_structure
        self.graph = defaultdict(set)
        self.reverse_graph = defaultdict(set)
        self.nodes = {}
        self.node_to_file = {}

        self._build_graph()

    def _build_graph(self):
        """Build dependency graph from parsed structure."""
        for file_path, file_meta in self.parsed_structure.items():
            structure = file_meta.get("structure", [])

            for item in structure:
                if item["type"] == "class":
                    class_name = item["name"]

                    for method in item["methods"]:
                        method_name = method["method_name"]
                        node_id = f"{file_path}:{class_name}.{method_name}"

                        self.nodes[node_id] = {
                            "type": "method",
                            "file": file_path,
                            "class": class_name,
                            "name": method_name,
                            "metadata": method
                        }
                        self.node_to_file[node_id] = file_path

                elif item["type"] == "function":
                    function_name = item["details"]["method_name"]
                    node_id = f"{file_path}:{function_name}"

                    self.nodes[node_id] = {
                        "type": "function",
                        "file": file_path,
                        "name": function_name,
                        "metadata": item["details"]
                    }
                    self.node_to_file[node_id] = file_path

        for node_id, node_info in self.nodes.items():
            metadata = node_info["metadata"]
            method_calls = metadata.get("method_calls", [])

            for call in method_calls:
                dependency_node = self._resolve_call(node_id, call)

                if dependency_node and dependency_node in self.nodes:
                    self.graph[node_id].add(dependency_node)
                    self.reverse_graph[dependency_node].add(node_id)

    def _resolve_call(self, caller_node_id: str, call_name: str) -> str:
        """
        Resolve a method call to a node ID.

        Args:
            caller_node_id: ID of the calling node
            call_name: Name of the called function (e.g., "foo", "self.bar", "ClassName.baz")

        Returns:
            Resolved node_id or None if not found
        """
        caller_file = self.node_to_file[caller_node_id]
        caller_info = self.nodes[caller_node_id]

        if call_name.startswith("self."):
            method_name = call_name.replace("self.", "")
            if caller_info["type"] == "method":
                class_name = caller_info["class"]
                node_id = f"{caller_file}:{class_name}.{method_name}"
                return node_id if node_id in self.nodes else None

        elif "." in call_name:
            parts = call_name.split(".")
            class_name = parts[0]
            method_name = ".".join(parts[1:])

            node_id = f"{caller_file}:{class_name}.{method_name}"
            if node_id in self.nodes:
                return node_id

            for file_path in self.parsed_structure.keys():
                node_id = f"{file_path}:{class_name}.{method_name}"
                if node_id in self.nodes:
                    return node_id

        else:
            node_id = f"{caller_file}:{call_name}"
            if node_id in self.nodes:
                return node_id

            for file_path in self.parsed_structure.keys():
                node_id = f"{file_path}:{call_name}"
                if node_id in self.nodes:
                    return node_id

        return None

    def get_node_metadata(self, node_id: str) -> dict:
        """Get metadata for a node."""
        return self.nodes.get(node_id, {})

    def get_dependencies(self, node_id: str) -> Set[str]:
        """Get direct dependencies of a node."""
        return self.graph.get(node_id, set())

    def get_statistics(self) -> dict:
        """Get graph statistics for debugging."""
        total_nodes = len(self.nodes)
        total_edges = sum(len(deps) for deps in self.graph.values())
        nodes_with_deps = sum(1 for deps in self.graph.values() if deps)
        max_deps = max((len(deps) for deps in self.graph.values()), default=0)

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_with_dependencies": nodes_with_deps,
            "max_dependencies_per_node": max_deps,
            "average_dependencies": total_edges / total_nodes if total_nodes > 0 else 0
        }


def build_dependency_graph(parsed_structure: dict) -> DependencyGraph:
    """
    Build dependency graph from parsed structure.

    Args:
        parsed_structure: Output from OSA_TreeSitter.analyze_directory()

    Returns:
        DependencyGraph instance
    """
    graph = DependencyGraph(parsed_structure)

    stats = graph.get_statistics()
    logger.info(f"Dependency graph ready: {len(graph.nodes)} nodes")
    logger.debug(f"Dependency graph built: {stats}")

    return graph
