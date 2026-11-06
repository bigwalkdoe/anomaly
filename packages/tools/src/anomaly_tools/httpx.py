from __future__ import annotations

from anomaly_tools.recon import ReconTool, parse_recon_output, run_recon


class HttpxTool(ReconTool):
    name = "httpx"


__all__ = ["HttpxTool", "ReconTool", "parse_recon_output", "run_recon"]
