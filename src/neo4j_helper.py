from neo4j import GraphDatabase, basic_auth
from yfiles_jupyter_graphs import GraphWidget


class Neo4jHelper:

    def __init__(self, neo4j_host="neo4j-bootcamp-db", neo4j_port=7687, neo4j_user="neo4j", neo4j_password="password",
                 neo4j_db="neo4j"):
        self.neo4j_host = neo4j_host
        self.neo4j_port = neo4j_port
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.neo4j_db = neo4j_db
        self._driver = GraphDatabase.driver(
            f"bolt://{neo4j_host}:{neo4j_port}", auth=basic_auth(neo4j_user, neo4j_password)
        )

    def __del__(self):
        self._driver.close()
    def clear_database(self):
        with self._driver.session(database=self.neo4j_db) as session:
            session.run("MATCH (n) DETACH DELETE n")

    @staticmethod
    def default_node_caption(node: dict):
        if "label" in node["properties"]:
            if len(node["properties"]["label"]) > 0:
                return node["properties"]["label"]
        return str(node["id"])

    def execute_cypher(
            self, cyper_query,
            as_graph=True,
            caption=None,
            size_mapping: tuple[int, int] = None
    ) -> GraphWidget or None:
        with self._driver.session(database=self.neo4j_db) as session:
            result = session.run(cyper_query)
            if as_graph:
                graph = result.graph()
                w = GraphWidget(overview_enabled=True, graph=graph)
                if isinstance(caption, str):
                    w.set_node_label_mapping(
                        lambda x: x["properties"][caption] if caption else Neo4jHelper.default_node_caption
                    )
                elif callable(caption):
                    w.set_node_label_mapping(caption)
                else:
                    w.set_node_label_mapping(Neo4jHelper.default_node_caption)
                w.set_sidebar(False)
                if size_mapping:
                    w.set_node_size_mapping(lambda index, node: size_mapping)
                return w
            else:
                print(result.consume().counters)

    def execute_cypher_file(self, cyper_path: str, as_graph=False):
        with open(cyper_path) as f:
            queries = f.read()
        return self.execute_cypher(queries, as_graph)

    def show_all(self, caption=None, size_mapping: tuple[int, int] = None):
        g = self.execute_cypher("MATCH (n) -[r]-> (m) RETURN n,r,m", caption=caption, size_mapping=size_mapping)
        g.show()


if __name__ == '__main__':
    neo4j = Neo4jHelper(neo4j_host="localhost")
    g = neo4j.execute_cypher(
        "CREATE (n:Person:`Software Engineer` {email:'sorkhpar@outlook.com'}) RETURN n",
        caption="email",
        size_mapping=(200, 200)
    )
    del neo4j
    g.show()
