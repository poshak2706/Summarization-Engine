# Summarization-Engine
A modular FastAPI‑based workflow engine that performs multi‑step text summarization with real‑time WebSocket log streaming and a simple HTML testing UI.

**Overview:**

This project implements a node‑based workflow engine designed to summarize long text inputs through multiple processing steps:

	- Text chunking
	- Per‑chunk summarization
	- Summary merging
	- Refinement
	- Length enforcement
	- WebSocket streaming for real‑time logs
	
It also includes a lightweight HTML WebSocket tester UI to observe logs and workflow results.

**Features:**

	>Smart text splitting (paragraph-based)
	>Chunk‑wise summarization
	>Merged summary generation
	>Final summary refinement
	>Max‑length enforcement
	>User-defined length
	>Automatic fallback (len(text) // 3, min=20)
	>Live WebSocket logs (step-by-step workflow execution)
	>Pluggable workflow nodes
	>FastAPI + WebSocket API
	>Included WebSocket testing UI (test_ws.html)
