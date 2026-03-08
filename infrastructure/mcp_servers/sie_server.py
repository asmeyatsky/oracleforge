import logging
import json
from mcp.server import Server
from mcp.types import Tool
from domain.ports.oracle_ports import OracleSourcePort

logger = logging.getLogger(__name__)

class OracleForgeSIEServer:
    """
    MCP Server for the OracleForge Schema Intelligence Engine (SIE).
    Exposes Oracle-specific schema analysis capabilities as tools.
    """

    def __init__(self, oracle_port: OracleSourcePort):
        self.oracle_port = oracle_port
        self.server = Server("oracle-forge-sie")
        self._register_tools()

    def _register_tools(self):
        @self.server.tool()
        async def classify_tables(pattern: str = "%") -> str:
            """Classifies Oracle tables into modules and types based on name patterns."""
            logger.info(f"Classifying tables with pattern: {pattern}")
            metadata = await self.oracle_port.get_schema_metadata()
            # Simple heuristic for classification
            tables = metadata.get("tables", [])
            classified = []
            for t in tables:
                name = t["name"]
                if name.startswith("GL_"): module = "GL"
                elif name.startswith("AP_"): module = "AP"
                elif name.startswith("PER_") or name.startswith("PAY_"): module = "HCM"
                else: module = "UNKNOWN"
                classified.append({"table": name, "module": module})
            
            return json.dumps(classified, indent=2)

        @self.server.tool()
        async def map_relationships(table_name: str) -> str:
            """Discovers FK and implicit relationships for a specific table."""
            logger.info(f"Mapping relationships for table: {table_name}")
            # Mock relationship mapping for now
            relationships = [
                {"source": table_name, "target": "FND_CURRENCIES", "type": "implicit", "column": "CURRENCY_CODE"}
            ]
            return json.dumps(relationships, indent=2)

        @self.server.tool()
        async def analyze_flexfields(table_name: str) -> str:
            """Enumerates Key Flexfields (KFF) and Descriptive Flexfields (DFF) for a table."""
            logger.info(f"Analyzing flexfields for table: {table_name}")
            # Identify columns starting with SEGMENT or ATTRIBUTE
            query = f"SELECT column_name FROM all_tab_columns WHERE table_name = '{table_name.upper()}'"
            columns = await self.oracle_port.execute_query(query)
            flexfields = [c["column_name"] for c in columns if "SEGMENT" in c["column_name"] or "ATTRIBUTE" in c["column_name"]]
            
            return json.dumps(flexfields, indent=2)

    async def run(self):
        """Run the MCP server."""
        async with self.server.run_stdio_async() as session:
            await session.wait()
