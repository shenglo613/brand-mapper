import json
import os
import socket
import polars as pl

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text
from sshtunnel import SSHTunnelForwarder

from RootDefinitions import ROOT_DIR

log_folder = os.path.dirname(os.path.abspath(__file__))
SQL = "posgresql"

class DBHelper:
    def __init__(self, service="pg-sql", is_ssh=False):
        self.BASE_DIR = ROOT_DIR
        self.service = service
        self.is_ssh = is_ssh
        self.local_ip = socket.gethostbyname(socket.gethostname())
        self.config = self._read_config()
        if self._check_ssh():
            self.uri = self._ssh_forwarder(self.config[SQL][service])
        else:
            self.uri = self._compose_uri(self.config[SQL][service])
        self.engine = create_engine(
            self.uri,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=1800,
            poolclass=NullPool,
        )
        self.connection = self.engine.connect()
        self.session = sessionmaker(bind=self.engine)(bind=self.connection)

    def execute_select(self, query, disconnect=True) -> pl.DataFrame:
        result = self.session.execute(text(query))
        rows = result.fetchall()
        column_names = result.keys()

        if disconnect:
            self.session_close()

        df = pl.DataFrame(rows, schema=column_names)
        return df

    def execute_update(self, query, data, disconnect=True) -> int:
        count = 0
        try:
            result = self.execute_raw_sql(text(query), data)
            count = result.rowcount
            self.session.commit()
        except Exception as e:
            print(e)
            self.session.rollback()
        if disconnect:
            self.session_close()
        print(f"affected rows: {count}")
        return count

    def execute_delete(self, query, disconnect=True) -> int:
        count = 0
        try:
            result = self.execute_raw_sql(text(query))
            count = result.rowcount
            self.session.commit()
        except Exception as e:
            print(e)
            self.session.rollback()
        if disconnect:
            self.session_close()
        print(f"affected rows: {count}")
        return count

    @staticmethod
    def generate_update_query(df, table_name, sql_action="REPLACE INTO") -> str:
        if isinstance(df, pl.DataFrame):
            columns = df.columns
        else:
            columns = df.columns.values
        n_col = len(columns)
        query = f"{sql_action} {table_name}"
        params, bind_params = "(", "("
        for i, col in enumerate(columns):
            if i == (n_col - 1):
                params += f"{col})"
                bind_params += f":{col})"
            else:
                params += f"{col},"
                bind_params += f":{col},"
        query = f"{query} {params} VALUES {bind_params}"
        print(f"auto-generating SQL script, \n{query}")
        return query

    @staticmethod
    def generate_insert_conflict_query(
        df, table_name: str, unique_key=None, update_cols=None
    ) -> str:
        if update_cols is None:
            update_cols = []
        if unique_key is None:
            unique_key = []
        if df.is_empty():
            return ""

        if isinstance(df, pl.DataFrame):
            columns = df.columns
        else:
            columns = df.columns.values

        col_str = ", ".join(columns)
        values_list = []
        for row in df.to_dicts():
            row_values = []
            for c in columns:
                val = row[c]
                if val is None:
                    row_values.append("NULL")
                else:
                    row_values.append(f"'{val}'")
            values_list.append(f"({', '.join(row_values)})")

        values_str = ",\n".join(values_list)

        if unique_key:
            conflict_cols_str = ", ".join(unique_key)
            if update_cols:
                set_clauses = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_cols])
                conflict_clause = f"ON CONFLICT ({conflict_cols_str}) DO UPDATE SET {set_clauses}"
            else:
                conflict_clause = f"ON CONFLICT ({conflict_cols_str}) DO NOTHING"
        else:
            conflict_clause = ""

        sql = f"""
                INSERT INTO {table_name} ({col_str})
                VALUES
                {values_str}
                {conflict_clause}
                ;
                """

        return sql

    def _check_ssh(self):
        c0 = ("SSH" in self.config[SQL][self.service]) & (self.local_ip == "127.0.1.1")
        return c0 | self.is_ssh

    @staticmethod
    def _read_config(path=None):
        if path is None:
            path = os.path.join(ROOT_DIR, "resources/config", "settings.json")
        with open(path) as config_file:
            config = json.load(config_file)
            return config

    def session_close(self):
        self.session.get_bind().close()
        if "server" in dir(self):
            self.server.stop()

    def execute_raw_sql(self, *entities, **kwargs):
        return self.session.execute(*entities, **kwargs)

    def _compose_uri(self, config):
        host = config["SQL_HOST"]
        port = config["SQL_PORT"]
        user = config["SQL_USER"]
        password = config["SQL_PASSWORD"]
        schema = config["SQL_SCHEMA"]
        if password:
            user = f"{user}:{password}"
        return f"postgresql://{user}@{host}:{port}/{schema}"

    def _ssh_forwarder(self, config):
        self.server = SSHTunnelForwarder(
            (config["SSH"]["HOST"], config["SSH"]["PORT"]),
            ssh_password=config["SSH"].get("PASSWORD", None),
            ssh_username=config["SSH"]["USER"],
            remote_bind_address=(config["SQL_HOST"], config["SQL_PORT"]),
        )
        self.server.start()
        host = "127.0.0.1"
        port = self.server.local_bind_port
        if port:
            host = f"{host}:{port}"
        user = config["SQL_USER"]
        password = config["SQL_PASSWORD"]
        schema = config["SQL_SCHEMA"]
        if password:
            user = f"{user}:{password}"
        return f"postgresql://{user}@{host}/{schema}"


if __name__ == "__main__":
    x = DBHelper("pg-sql")
    query = text("SELECT * FROM order_info")
    data = x.execute_select(query)
