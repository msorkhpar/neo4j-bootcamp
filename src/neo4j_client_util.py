from __future__ import annotations
from enum import Enum
import json

from neo4j import GraphDatabase, basic_auth, Driver, Query
from neo4j._work.summary import SummaryCounters
from neo4j.graph import Graph
from yfiles_jupyter_graphs import GraphWidget
from pandas import DataFrame


def default_node_caption(node: dict) -> str:
    if "label" in node["properties"]:
        if len(node["properties"]["label"]) > 0:
            return node["properties"]["label"]
    return str(node["id"])


class GraphLayout(Enum):
    CIRCULAR = "circular"
    HIERARCHIC = "hierarchic"
    ORGANIC = "organic"
    ORTHOGONAL = "orthogonal"
    RADIAL = "radial"
    TREE = "tree"
    ORTHOGONAL_EDGE = "orthogonal_edge_router"
    ORGANIC_EDGE = "organic-organic_edge_router"


class Neo4jConfig:
    def __init__(self, host="neo4j-bootcamp-db", port=7687, user="neo4j", password="password", db_name="neo4j",
                 caption: callable | str = default_node_caption, node_size: tuple[int, int] = (50, 50)):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name
        self.caption = caption
        self.node_size = node_size


class Neo4jClient:
    _instance = None
    _config = None

    def __init__(self, config: Neo4jConfig = Neo4jConfig()):
        self._config = config

    def clear_database(self) -> None:
        with Neo4jQueryExecutor(self._config, Query("MATCH (n) DETACH DELETE n")) as executor:
            executor.execute()

    @staticmethod
    def setup_movie_graph() -> Neo4jClient:
        def movie_caption(node):
            return (
                node["properties"].get("title", "")
                if "title" in node["properties"]
                else node["properties"].get("name", "")
            )

        helper = Neo4jClient(Neo4jConfig(caption=movie_caption, node_size=(120, 120)))
        helper.clear_database()
        with helper.cypher_file("./01_movie_graph_setup.cypher") as executor:
            executor.execute()
        return helper

    def cypher(self, cypher_query: str) -> Neo4jQueryExecutor:
        return Neo4jQueryExecutor(self._config, Query(cypher_query))

    def cypher_file(self, cyper_path: str) -> Neo4jQueryExecutor:
        with open(cyper_path) as f:
            queries = f.read()
        return self.cypher(queries)

    def show_all(self, caption=None, layout=GraphLayout.ORGANIC, size_mapping: tuple[int, int] = None) -> None:
        with self.cypher("MATCH (n) -[r]-> (m) RETURN n,r,m") as executor:
            (
                executor.with_caption(caption)
                .with_node_size(size_mapping)
                .show(layout)
            )


class Neo4jQueryExecutor:
    def __init__(self, config: Neo4jConfig, cypher_query: Query):
        self._driver = None
        self.config = config
        self.db_name = config.db_name
        self.caption = config.caption
        self.node_size = config.node_size
        self.cypher_query = cypher_query

    def __enter__(self):
        if not self._driver:
            self._driver = GraphDatabase.driver(
                f"bolt://{self.config.host}:{self.config.port}",
                auth=basic_auth(self.config.user, self.config.password)
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._driver:
            self._driver.close()
            self._driver = None

    def with_caption(self, caption) -> Neo4jQueryExecutor:
        if caption is not None:
            self.caption = caption
        return self

    def with_node_size(self, size: tuple[int, int]) -> Neo4jQueryExecutor:
        self.node_size = size
        return self

    def execute(self) -> SummaryCounters:
        if not self._driver:
            raise ValueError("Driver is not initialized. Use with statement to use this builder")
        with self._driver.session(database=self.db_name) as session:
            result = session.run(self.cypher_query)
            return result.consume().counters

    def execute_for_graph(self) -> GraphWidget:
        if not self._driver:
            raise ValueError("Driver is not initialized. Use with statement to use this builder")
        with self._driver.session(database=self.db_name) as session:
            graph: Graph = session.run(self.cypher_query).graph()
            print(f"Number of Nodes:[{len(graph.nodes)}], Number of Edges:[{len(graph.relationships)}]")
            widget = GraphWidget(overview_enabled=True, graph=graph)
            widget.set_sidebar(False)
            widget.set_node_label_mapping(self.caption)
            if isinstance(self.caption, str):
                widget.set_node_label_mapping(
                    lambda x: x["properties"][self.caption] if self.caption else default_node_caption
                )

            if self.node_size:
                widget.set_node_size_mapping(lambda index, node: self.node_size)
            return widget

    def show(self, layout=GraphLayout.ORGANIC) -> None:
        widget = self.execute_for_graph()
        widget.set_graph_layout(layout.value)
        widget.show()

    def execute_for_dataframe(self) -> DataFrame:
        if not self._driver:
            raise ValueError("Driver is not initialized. Use with statement to use this builder")
        with self._driver.session(database=self.db_name) as session:
            result = session.run(self.cypher_query)
            dataframe = DataFrame([dict(record) for record in result])
            return dataframe

    def execute_for_list(self) -> list:
        dataframe = self.execute_for_dataframe()
        json_array = json.loads(dataframe.to_json(orient="records"))
        return json_array

    def execute_for_dictionary(self) -> dict:
        json_array = self.execute_for_list()
        if len(json_array) > 1:
            raise ValueError("Multiple records have been returned, but only one is being fetched.")
        else:
            return json_array[0]


if __name__ == '__main__':
    neo4j = Neo4jClient(Neo4jConfig(host="localhost"))
    g = neo4j.cypher("CREATE (n:Person:`Software Engineer` {email:'a@outlook.com'}) RETURN n").with_caption(
        "email").with_node_size((200, 200)).execute_for_graph()
    del neo4j
    g.show()
