from __future__ import annotations
from enum import Enum
import json

from neo4j import GraphDatabase, basic_auth
from neo4j._work.summary import SummaryCounters
from yfiles_jupyter_graphs import GraphWidget
from pandas import DataFrame


def default_node_caption(node: dict):
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


class Neo4jHelper:

    def __init__(self, neo4j_host="neo4j-bootcamp-db", neo4j_port=7687, neo4j_user="neo4j", neo4j_password="password",
                 neo4j_db="neo4j", caption=default_node_caption, node_size: tuple[int, int] = None):
        self.neo4j_host = neo4j_host
        self.neo4j_port = neo4j_port
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.neo4j_db = neo4j_db
        self.caption = caption
        self.node_size = node_size
        self._driver = GraphDatabase.driver(
            f"bolt://{neo4j_host}:{neo4j_port}", auth=basic_auth(neo4j_user, neo4j_password)
        )

    def __del__(self):
        self._driver.close()

    def clear_database(self) -> None:
        with self._driver.session(database=self.neo4j_db) as session:
            session.run("MATCH (n) DETACH DELETE n")

    def cypher(self, cypher_query) -> CypherQueryBuilder:
        return Neo4jHelper.CypherQueryBuilder(self, cypher_query)

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
        def __init__(self, helper, cypher_query):
            self._driver = helper._driver
            self.neo4j_db = helper.neo4j_db
            self.caption = helper.caption
            self.node_size = helper.node_size
            self.cypher_query = cypher_query

        def with_caption(self, caption) -> Neo4jHelper.CypherQueryBuilder:
            if caption is not None:
                self.caption = caption
            return self

        def with_node_size(self, size: tuple[int, int]) -> Neo4jHelper.CypherQueryBuilder:
            self.node_size = size
            return self

        def execute(self) -> SummaryCounters:
            with self._driver.session(database=self.neo4j_db) as session:
                result = session.run(self.cypher_query)
                return result.consume().counters

        def execute_for_graph(self) -> GraphWidget:

            with self._driver.session(database=self.neo4j_db) as session:
                result = session.run(self.cypher_query)
                w = GraphWidget(overview_enabled=True, graph=result.graph())
                w.set_sidebar(False)
                w.set_node_label_mapping(self.caption)
                if isinstance(self.caption, str):
                    w.set_node_label_mapping(
                        lambda x: x["properties"][self.caption] if self.caption else default_node_caption
                    )

                if self.node_size:
                    w.set_node_size_mapping(lambda index, node: self.node_size)

                return w

        def show(self, layout=GraphLayout.ORGANIC) -> None:
            w = self.execute_for_graph()
            w.set_graph_layout(layout.value)
            w.show()

        def execute_for_dataframe(self) -> DataFrame:
            with self._driver.session(database=self.neo4j_db) as session:
                result = session.run(self.cypher_query)
                df = DataFrame([dict(record) for record in result])
                return df

        def execute_for_list(self) -> list:
            df = self.execute_for_dataframe()
            json_array = json.loads(df.to_json(orient="records"))
            return json_array

        def execute_for_dictionary(self) -> dict:
            json_array = self.execute_for_list()
            if len(json_array) > 1:
                raise ValueError("Multiple records have been returned, but only one is being fetched.")
            else:
                return json_array[0]


if __name__ == '__main__':
    neo4j = Neo4jHelper(neo4j_host="localhost")
    g = neo4j.cypher("CREATE (n:Person:`Software Engineer` {email:'a@outlook.com'}) RETURN n").with_caption(
        "email").with_node_size((200, 200)).execute_for_graph()
    del neo4j
    g.show()
