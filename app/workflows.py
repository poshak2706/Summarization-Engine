from .models import WorkflowState
from .tools import TOOL_REGISTRY
from .engine import Graph
from datetime import datetime

def _log(state: WorkflowState, node: str, msg: str, level: str = "info", preview: str = ""):
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "node": node,
        "level": level,
        "msg": msg,
        "preview": preview,
    }
    state.log.append(entry)
    return entry

# NODE 1 — Split text into chunks
async def node_split_text(state: WorkflowState) -> WorkflowState:
    text = state.input_text.strip()

    # --- 1) Split into chunks ---
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    state.chunks = paragraphs

    # --- 2) Respect user-supplied max_length ---
    # If user did NOT provide one (0, None), compute default = total_words//3 or min 20
    if not state.max_length or state.max_length <= 0:
        total_words = len(text.split())
        computed = max(total_words // 3, 20)
        state.max_length = computed  # user had no preference → use default

    # Log single clean structured entry
    state.log.append({
        "ts": datetime.utcnow().isoformat() + "Z",
        "node": "split_text",
        "level": "info",
        "msg": "Splitting text into chunks...",
        "preview": ""
    })

    return state


# NODE 2 — Summaries for each chunk
def node_generate_summaries(state: WorkflowState) -> WorkflowState:
    _log(state, "generate_summaries", "Generating summaries for each chunk...")
    summarizer = TOOL_REGISTRY["summarize_chunk"]
    state.chunk_summaries = [
        summarizer(chunk, max_words=50)
        for chunk in state.chunks
    ]
    return state

# NODE 3 — Merge summaries
def node_merge_summaries(state: WorkflowState) -> WorkflowState:
    _log(state, "merge_summaries", "Merging chunk summaries...", preview="; ".join(s[:100] for s in state.chunk_summaries))
    merger = TOOL_REGISTRY["merge_summaries"]
    state.merged_summary = merger(state.chunk_summaries)
    state.refined_summary = state.merged_summary
    return state

# NODE 4 — Refine final summary
def node_refine_summary(state: WorkflowState) -> WorkflowState:
    _log(state, "refine_summary", "Refining summary...", preview=state.refined_summary[:200])
    refiner = TOOL_REGISTRY["refine_summary"]
    state.refined_summary = refiner(state.refined_summary, state.max_length)
    return state

# NODE 5 — Check length
def node_check_length(state: WorkflowState) -> WorkflowState:
    word_count = len(state.refined_summary.split())
    if word_count <= state.max_length:
        _log(state, "check_length", f"Summary within limit ({word_count} words). Finishing workflow.", preview=state.refined_summary[:200])
        state.done = True
    else:
        _log(state, "check_length", f"Summary too long ({word_count} words). Will refine again.", preview=state.refined_summary[:200])
    return state

# Build Graph
def create_option_b_graph() -> Graph:
    nodes = {
        "split_text": node_split_text,
        "generate_summaries": node_generate_summaries,
        "merge_summaries": node_merge_summaries,
        "refine_summary": node_refine_summary,
        "check_length": node_check_length,
    }

    edges = {
        "split_text": "generate_summaries",
        "generate_summaries": "merge_summaries",
        "merge_summaries": "refine_summary",
        "refine_summary": "check_length",
        "check_length": "refine_summary",
    }

    return Graph(nodes=nodes, edges=edges, start_node="split_text")
