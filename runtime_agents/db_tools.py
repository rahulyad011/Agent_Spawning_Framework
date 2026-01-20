from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


@dataclass
class DatabaseConnectionTool:
    """Manage database connections."""

    name: str = "db_connect"
    description: str = "Connect to a database. Input: {connection_string: string, db_type: string}."

    connections: Dict[str, Engine] = None

    def __post_init__(self):
        if self.connections is None:
            self.connections = {}

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        connection_string = input.get("connection_string")
        db_type = input.get("db_type", "postgresql")

        if not connection_string:
            return {"error": "Missing 'connection_string'."}

        connection_id = input.get("connection_id", "default")

        try:
            # Create SQLAlchemy engine
            engine = create_engine(connection_string, echo=False)
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self.connections[connection_id] = engine

            return {
                "status": "connected",
                "connection_id": connection_id,
                "db_type": db_type,
            }
        except Exception as e:
            return {"error": f"Connection failed: {str(e)}"}

    def get_engine(self, connection_id: str = "default") -> Optional[Engine]:
        """Get engine for a connection ID."""
        return self.connections.get(connection_id)


@dataclass
class SchemaIntrospectionTool:
    """Fetch database schema and table metadata."""

    name: str = "db_schema"
    description: str = "Get schema information for tables. Input: {connection_id: string, tables: List[string] (optional)}."

    connection_tool: DatabaseConnectionTool = None

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        connection_id = input.get("connection_id", "default")
        tables = input.get("tables", [])

        if not self.connection_tool:
            return {"error": "DatabaseConnectionTool not provided."}

        engine = self.connection_tool.get_engine(connection_id)
        if not engine:
            return {"error": f"Connection '{connection_id}' not found."}

        try:
            inspector = inspect(engine)
            all_tables = inspector.get_table_names()

            if tables:
                # Get specific tables
                requested_tables = [t for t in tables if t in all_tables]
            else:
                # Get all tables
                requested_tables = all_tables

            schema_info = {}
            for table_name in requested_tables:
                columns = inspector.get_columns(table_name)
                primary_keys = inspector.get_primary_keys(table_name)
                foreign_keys = inspector.get_foreign_keys(table_name)

                schema_info[table_name] = {
                    "columns": [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col.get("nullable", True),
                            "default": str(col.get("default", "")),
                        }
                        for col in columns
                    ],
                    "primary_keys": primary_keys,
                    "foreign_keys": [
                        {
                            "name": fk["name"],
                            "constrained_columns": fk["constrained_columns"],
                            "referred_table": fk["referred_table"],
                            "referred_columns": fk["referred_columns"],
                        }
                        for fk in foreign_keys
                    ],
                }

            return {
                "connection_id": connection_id,
                "tables": schema_info,
                "available_tables": all_tables,
            }

        except Exception as e:
            return {"error": f"Schema introspection failed: {str(e)}"}


@dataclass
class DatabaseQueryTool:
    """Execute database queries with safety checks."""

    name: str = "db_query"
    description: str = "Execute a SELECT query on the database. Input: {connection_id: string, query: string, max_rows: int (optional, default 100)}."

    connection_tool: DatabaseConnectionTool = None
    read_only: bool = True
    max_rows: int = 100

    def _validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate query for safety. Returns (is_valid, error_message)."""
        query_upper = query.strip().upper()

        # Block dangerous operations in read-only mode
        if self.read_only:
            dangerous_keywords = [
                "DROP",
                "DELETE",
                "UPDATE",
                "INSERT",
                "ALTER",
                "CREATE",
                "TRUNCATE",
                "GRANT",
                "REVOKE",
            ]
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    return False, f"Read-only mode: '{keyword}' operations not allowed."

        # Only allow SELECT queries in read-only mode
        if self.read_only and not query_upper.startswith("SELECT"):
            return False, "Read-only mode: Only SELECT queries are allowed."

        return True, None

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        connection_id = input.get("connection_id", "default")
        query = input.get("query", "")
        max_rows = input.get("max_rows", self.max_rows)

        if not query:
            return {"error": "Missing 'query'."}

        if not self.connection_tool:
            return {"error": "DatabaseConnectionTool not provided."}

        engine = self.connection_tool.get_engine(connection_id)
        if not engine:
            return {"error": f"Connection '{connection_id}' not found."}

        # Validate query
        is_valid, error_msg = self._validate_query(query)
        if not is_valid:
            return {"error": error_msg}

        try:
            with engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchmany(max_rows)

                # Get column names
                columns = list(result.keys()) if hasattr(result, "keys") else []

                # Convert rows to list of dicts
                data = []
                for row in rows:
                    if columns:
                        data.append(dict(zip(columns, row)))
                    else:
                        data.append(list(row))

                return {
                    "connection_id": connection_id,
                    "query": query,
                    "rows": data,
                    "row_count": len(data),
                    "columns": columns,
                    "truncated": len(rows) >= max_rows,
                }

        except SQLAlchemyError as e:
            return {"error": f"Query execution failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
