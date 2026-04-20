# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""MCP server exposing ACAP Core validators and extension primitives.

Run with ``python -m acap.mcp_server`` or via the ``acap-mcp`` entry
point after installing the package. Uses stdio transport; any
MCP-compatible client (for example a VSCode MCP config at
``.vscode/mcp.json``) can drive the server by pointing at the
entry-point command.
"""

from acap.mcp_server.server import build_server, main

__all__ = ["build_server", "main"]
