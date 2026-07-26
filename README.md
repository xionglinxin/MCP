# MCP Servers

Huawei network automation MCP servers for AI agents.

## Projects

- **ensp-mcp** — Generate Huawei eNSP topology files (.topo) and device config scripts via MCP
- **visio-draw-mcp** — Generate Microsoft Visio network diagrams via COM automation + MCP

## Requirements

- Python >= 3.10
- `mcp >= 1.0.0`, `pydantic >= 2.0.0`
- visio-draw-mcp additionally requires: Windows + Microsoft Visio + `pywin32`

## Quick Start

```bash
cd ensp-mcp
python -m venv .venv && .venv/Scripts/pip install -e .
# or
cd visio-draw-mcp
python -m venv .venv && .venv/Scripts/pip install -e .
```

Configure in Claude Desktop / QoderWork MCP settings pointing to each server's `server.py`.
