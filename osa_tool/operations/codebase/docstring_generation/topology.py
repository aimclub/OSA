from typing import List, Set, Tuple
from collections import defaultdict, deque
from osa_tool.utils.logger import logger


class DependencyGraph:
    """
    Constructs and maintains a directed graph representing the call dependencies between functions and methods within a codebase.
    
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
        
        WHY:
        This constructor builds a directed graph representing import dependencies between files.
        It creates both forward and reverse adjacency lists to enable efficient dependency traversal and cycle detection.
        The graph is constructed immediately upon initialization to ensure the object is ready for subsequent queries.
        
        The method initializes the following attributes:
        - parsed_structure: Stores the input parsed structure for reference.
        - graph: Forward adjacency list mapping each file to its direct dependencies (files it imports).
        - reverse_graph: Reverse adjacency list mapping each file to its dependents (files that import it).
        - nodes: Placeholder for potential node metadata (currently an empty dictionary).
        - node_to_file: Mapping from node identifiers to file paths (currently empty until populated by _build_graph).
        
        After setting up the data structures, it calls _build_graph() to populate the graph based on the imports in parsed_structure.
        """
        self.parsed_structure = parsed_structure
        self.graph = defaultdict(set)
        self.reverse_graph = defaultdict(set)
        self.nodes = {}
        self.node_to_file = {}

        self._build_graph()

    def _build_graph(self):
        """
        Build dependency graph from parsed structure.
        
        This method constructs a directed dependency graph by processing the parsed structure of source files. It creates nodes for each method and function, then establishes edges based on method calls to represent dependencies between them.
        
        Args:
            self: The DependencyGraph instance containing parsed_structure, nodes, node_to_file, graph, and reverse_graph.
        
        Why:
            The graph is built to enable analysis of dependencies within the codebase, such as identifying call hierarchies or potential circular dependencies. Nodes are keyed by a unique identifier combining file path and method/function name to avoid collisions. Dependencies are derived from the 'method_calls' metadata of each node, linking caller to callee.
        
        Returns:
            None. The method populates internal structures (nodes, node_to_file, graph, reverse_graph) but does not return a value.
        """
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
                            "metadata": method,
                        }
                        self.node_to_file[node_id] = file_path

                elif item["type"] == "function":
                    function_name = item["details"]["method_name"]
                    node_id = f"{file_path}:{function_name}"

                    self.nodes[node_id] = {
                        "type": "function",
                        "file": file_path,
                        "name": function_name,
                        "metadata": item["details"],
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
        Resolve a method call to a node ID within the dependency graph.
        
        The method determines the node ID corresponding to a given call name by considering the caller's context (file and class) and searching through the graph's nodes. It handles different call formats, such as instance methods, class methods, and standalone functions, by constructing candidate node IDs and checking for their existence in the graph.
        
        Args:
            caller_node_id: ID of the calling node, used to determine the caller's file and class context.
            call_name: Name of the called function or method. This can be in various formats:
                - "foo": a standalone function.
                - "self.bar": an instance method called on the same class.
                - "ClassName.baz": a class method or a method from another class.
        
        Returns:
            The resolved node ID if a matching node is found; otherwise, None.
        
        Why:
            This resolution is necessary to map dynamic method calls in the source code to static nodes in the dependency graph, enabling accurate dependency tracking and analysis. It supports the tool's goal of understanding and documenting code structure by linking callers to their dependencies.
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
        """
        Get metadata for a node.
        
        This method retrieves the metadata dictionary associated with a given node ID from the graph's internal node storage. It is used to access node-specific information stored during graph construction or analysis, such as labels, properties, or other attributes.
        
        Args:
            node_id: The unique identifier of the node whose metadata is being requested.
        
        Returns:
            The metadata dictionary for the specified node. If the node ID does not exist in the graph, an empty dictionary is returned instead.
        """
        return self.nodes.get(node_id, {})

    def get_dependencies(self, node_id: str) -> Set[str]:
        """
        Get direct dependencies of a node.
        
        Args:
            node_id: The identifier of the node whose dependencies are requested.
        
        Returns:
            A set containing the identifiers of all nodes that the specified node directly depends on.
            Returns an empty set if the node has no dependencies or if the node_id is not found in the graph.
        """
        return self.graph.get(node_id, set())

    def get_statistics(self) -> dict:
        """
        Get graph statistics for debugging.
        
        This method computes key metrics about the dependency graph structure, useful for understanding its complexity and verifying its state during development or troubleshooting.
        
        Args:
            self: The DependencyGraph instance.
        
        Returns:
            A dictionary containing the following statistics:
                - total_nodes: Total number of nodes in the graph.
                - total_edges: Total number of directed dependency edges in the graph.
                - nodes_with_dependencies: Count of nodes that have at least one outgoing dependency edge.
                - max_dependencies_per_node: The highest number of dependencies any single node has.
                - average_dependencies: The average number of dependencies per node (edges divided by nodes). Returns 0 if the graph is empty.
        """
        total_nodes = len(self.nodes)
        total_edges = sum(len(deps) for deps in self.graph.values())
        nodes_with_deps = sum(1 for deps in self.graph.values() if deps)
        max_deps = max((len(deps) for deps in self.graph.values()), default=0)

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_with_dependencies": nodes_with_deps,
            "max_dependencies_per_node": max_deps,
            "average_dependencies": total_edges / total_nodes if total_nodes > 0 else 0,
        }


def build_dependency_graph(parsed_structure: dict) -> DependencyGraph:
    """
    Build dependency graph from parsed structure.
    
    Args:
        parsed_structure: Output from OSA_TreeSitter.analyze_directory(). Contains the parsed code structure used to construct the graph.
    
    Returns:
        DependencyGraph instance: The constructed graph, which is logged with node count and statistics for debugging and monitoring purposes.
    """
    graph = DependencyGraph(parsed_structure)

    stats = graph.get_statistics()
    logger.info(f"Dependency graph ready: {len(graph.nodes)} nodes")
    logger.debug(f"Dependency graph built: {stats}")

    return graph
