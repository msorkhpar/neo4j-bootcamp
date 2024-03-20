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
                 caption: callable or str = default_node_caption, node_size: tuple[int, int] = (50, 50)):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name
        self.caption = caption
        self.node_size = node_size


class Neo4jHelper:
    _instance = None
    _driver = None
    _config = None

    def __init__(self, config: Neo4jConfig = Neo4jConfig()):
        self._config = config
        self._driver: Driver = GraphDatabase.driver(
            f"bolt://{config.host}:{config.port}", auth=basic_auth(config.user, config.password)
        )

    def __del__(self):
        self._driver.close()

    def clear_database(self) -> None:
        with self._driver.session(database=self._config.db_name) as session:
            session.run("MATCH (n) DETACH DELETE n")

    @staticmethod
    def setup_movie_graph() -> Neo4jHelper:
        def movie_caption(node):
            return (
                node["properties"].get("title", "")
                if "title" in node["properties"]
                else node["properties"].get("name", "")
            )

        helper = Neo4jHelper(Neo4jConfig(caption=movie_caption, node_size=(120, 120)))
        helper.clear_database()
        helper.cypher_file("./01_movie_graph_setup.cypher").execute()
        return helper

    def cypher(self, cypher_query: str) -> CypherQueryBuilder:
        return CypherQueryBuilder(self._config, self._driver, Query(cypher_query))

    def cypher_file(self, cyper_path: str) -> CypherQueryBuilder:
        with open(cyper_path) as f:
            queries = f.read()
        return self.cypher(queries)

    def show_all(self, caption=None, layout=GraphLayout.ORGANIC, size_mapping: tuple[int, int] = None) -> None:
        (
            self.cypher("MATCH (n) -[r]-> (m) RETURN n,r,m")
            .with_node_size(size_mapping)
            .with_caption(caption)
            .show(layout)
        )


class CypherQueryBuilder:
    def __init__(self, config: Neo4jConfig, driver: Driver, cypher_query: Query):
        self.driver = driver
        self.db_name = config.db_name
        self.caption = config.caption
        self.node_size = config.node_size
        self.cypher_query = cypher_query

    def with_caption(self, caption) -> CypherQueryBuilder:
        if caption is not None:
            self.caption = caption
        return self

    def with_node_size(self, size: tuple[int, int]) -> CypherQueryBuilder:
        self.node_size = size
        return self

    def execute(self) -> SummaryCounters:
        with self.driver.session(database=self.db_name) as session:
            result = session.run(self.cypher_query)
            return result.consume().counters

    def execute_for_graph(self) -> GraphWidget:

        with self.driver.session(database=self.db_name) as session:
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
        with self.driver.session(database=self.db_name) as session:
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
    neo4j = Neo4jHelper(Neo4jConfig(host="localhost"))
    g = neo4j.cypher("CREATE (n:Person:`Software Engineer` {email:'a@outlook.com'}) RETURN n").with_caption(
        "email").with_node_size((200, 200)).execute_for_graph()
    del neo4j
    g.show()
