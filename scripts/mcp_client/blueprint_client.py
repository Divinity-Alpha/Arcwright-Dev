"""
BlueprintLLM TCP Client Library.

Connects to the BlueprintLLM Command Server running inside UE5 Editor
on localhost:13377. Sends JSON commands and receives JSON responses.

Usage:
    from blueprint_client import BlueprintLLMClient

    client = BlueprintLLMClient()
    result = client.health_check()
    print(result)

    result = client.import_from_ir("C:/BlueprintLLM/test_ir/T1_01_HelloWorld.blueprint.json")
    print(result)

    client.close()
"""

import socket
import json
import time
from typing import Optional


class BlueprintLLMError(Exception):
    """Raised when the server returns an error response."""
    pass


class BlueprintLLMClient:
    def __init__(self, host: str = "localhost", port: int = 13377, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        self._buffer = b""

    def send_command(self, command: str, params: Optional[dict] = None) -> dict:
        """Send a command and return the parsed response dict."""
        msg = json.dumps({"command": command, "params": params or {}})
        self.sock.sendall((msg + "\n").encode("utf-8"))
        response = self._read_response()
        parsed = json.loads(response)
        if parsed.get("status") == "error":
            raise BlueprintLLMError(parsed.get("message", "Unknown error"))
        return parsed

    def _read_response(self) -> str:
        """Read a newline-terminated JSON response."""
        while b"\n" not in self._buffer:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("Server closed connection")
            self._buffer += chunk

        line, self._buffer = self._buffer.split(b"\n", 1)
        return line.decode("utf-8").strip()

    # ---- High-level commands ----

    def health_check(self) -> dict:
        """Check server health. Returns server info."""
        return self.send_command("health_check")

    def import_from_ir(self, ir_path: str) -> dict:
        """Import a .blueprint.json IR file into UE5.

        Args:
            ir_path: Absolute path to the IR file.

        Returns:
            dict with status, data containing blueprint_name, nodes_created,
            connections_wired, compiled, etc.
        """
        return self.send_command("import_from_ir", {"path": ir_path})

    def get_blueprint_info(self, name: str) -> dict:
        """Query an existing Blueprint's full structure.

        Args:
            name: Blueprint asset name (e.g. "BP_HelloWorld").

        Returns:
            dict with nodes, connections, variables, compiled status.
        """
        return self.send_command("get_blueprint_info", {"name": name})

    def compile_blueprint(self, name: str) -> dict:
        """Recompile a Blueprint.

        Args:
            name: Blueprint asset name.

        Returns:
            dict with compiled status.
        """
        return self.send_command("compile_blueprint", {"name": name})

    def delete_blueprint(self, name: str) -> dict:
        """Delete a Blueprint asset.

        Args:
            name: Blueprint asset name.

        Returns:
            dict with deleted status.
        """
        return self.send_command("delete_blueprint", {"name": name})

    def close(self):
        """Close the connection."""
        try:
            self.sock.close()
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()


if __name__ == "__main__":
    # Quick test
    with BlueprintLLMClient() as client:
        result = client.health_check()
        print(json.dumps(result, indent=2))
