from typing import Callable, Dict, Optional, Awaitable
from .models import WorkflowState
import uuid
import inspect
from datetime import datetime

# Node function type
NodeFn = Callable[[WorkflowState], WorkflowState | Awaitable[WorkflowState]]

# Callback used for WebSocket live updates
StepCallback = Callable[[str, WorkflowState], Awaitable[None]]

# In-memory storage
GRAPHS: Dict[str, "Graph"] = {}
RUNS: Dict[str, WorkflowState] = {}
RUN_LOGS: Dict[str, list[str]] = {}


class Graph:
    def __init__(self, nodes: Dict[str, NodeFn], edges: Dict[str, Optional[str]], start_node: str):
        """
        nodes: mapping of node_name -> function
        edges: mapping of node_name -> next_node_name (or None)
        """
        self.nodes = nodes
        self.edges = edges
        self.start_node = start_node


async def _execute_node(node_fn: NodeFn, state: WorkflowState) -> WorkflowState:
    """Run a node (supports both sync and async functions)."""
    if inspect.iscoroutinefunction(node_fn):
        # async node
        return await node_fn(state)
    else:
        # sync node
        return node_fn(state)


async def run_graph_async(
    graph_id: str,
    initial_state: WorkflowState,
    on_step: Optional[StepCallback] = None,
):
    """
    Runs a graph node-by-node.
    Calls on_step(node_name, state) after each node if provided (for WebSockets).
    NOTE: this version intentionally does NOT append a separate "Running node: X"
    log — nodes themselves should emit their _own_ structured logs. This avoids
    duplicate messages. Also we call `on_step` after the node completes so the
    node's log entries are included in the streamed update.
    """

    graph = GRAPHS[graph_id]
    state = initial_state
    run_id = str(uuid.uuid4())

    RUNS[run_id] = state
    RUN_LOGS[run_id] = []

    current = graph.start_node

    while current is not None and not state.done:
        node_fn = graph.nodes[current]

        # Execute node first (so node can append its structured logs)
        state = await _execute_node(node_fn, state)

        # Save state snapshot
        RUNS[run_id] = state

        # WebSocket live update AFTER node has run so the node's own logs are included
        if on_step:
            await on_step(current, state)

        # Also keep a compact copy of latest logs for retrieval (optional)
        # We append the node's newest log(s) into RUN_LOGS for this run_id
        # (store the last few entries to avoid huge memory use).
        if state.log:
            # append the last log entry (structured)
            RUN_LOGS[run_id].append(state.log[-1])

        # Get next node
        current = graph.edges.get(current)

    # Final callback if WebSocket is connected (send final snapshot; nodes will have logged before)
    if on_step:
        await on_step("END", state)

    return state, run_id
