import json
import sys
from typing import Any, Dict
from pydantic import BaseModel


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: Any


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Any = None
    error: Any = None
    id: Any


class StdioSidecarServer:
    """
    Stdio JSON-RPC GUI Sidecar Protocol Server (Layer A/B).
    Enables desktop UIs (Tauri 2.x) to execute JoBot commands via stdio JSON-RPC 2.0 messages.
    """

    def process_request(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        req_id = request_dict.get("id")
        method = request_dict.get("method")
        params = request_dict.get("params", {})

        if method == "ping":
            return JsonRpcResponse(id=req_id, result={"status": "pong", "version": "1.0.0"}).model_dump()
        elif method == "status":
            from jobot.storage.db import DatabaseManager
            db = DatabaseManager()
            apps = db.list_applications(limit=10)
            return JsonRpcResponse(
                id=req_id,
                result={"total_tracked": len(apps), "recent": [a.model_dump() for a in apps[:5]]},
            ).model_dump()
        elif method == "profile_info":
            from pathlib import Path
            from jobot.storage.vault import CredentialVault
            vault = CredentialVault()
            profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
            if profile_path.exists():
                p = vault.load_encrypted_profile(profile_path)
                return JsonRpcResponse(id=req_id, result=p.model_dump()).model_dump()
            return JsonRpcResponse(id=req_id, error={"code": -32602, "message": "Profile not found"}).model_dump()
        else:
            return JsonRpcResponse(
                id=req_id,
                error={"code": -32601, "message": f"Method '{method}' not found"},
            ).model_dump()

    def run_loop(self) -> None:
        """Run continuous stdio loop processing JSON-RPC lines."""
        for line in sys.stdin:
            line = line.strip()
            if line:
                try:
                    req = json.loads(line)
                    res = self.process_request(req)
                    sys.stdout.write(json.dumps(res) + "\n")
                    sys.stdout.flush()
                except Exception as e:
                    err_res = JsonRpcResponse(id=None, error={"code": -32700, "message": f"Parse error: {e}"}).model_dump()
                    sys.stdout.write(json.dumps(err_res) + "\n")
                    sys.stdout.flush()
