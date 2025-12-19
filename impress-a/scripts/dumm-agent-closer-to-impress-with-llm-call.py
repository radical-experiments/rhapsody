"""
Minimal Agent with LLM Router + Protein Design Tools + Flowgentic
"""
import os
import sys
import socket
import asyncio
import logging
import multiprocessing as mp
import sys
import json
import re
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from radical.asyncflow import DragonTelemetryCollector
from radical.asyncflow import DragonVllmInferenceBackend
from radical.asyncflow import DragonExecutionBackendV3
from flowgentic.langGraph.execution_wrappers import AsyncFlowType
from flowgentic.langGraph.main import LangraphIntegration
from langgraph.errors import GraphRecursionError
from radical.asyncflow.logging import init_default_logger


logger1 = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ============================================================================
# STATE
# ============================================================================
class AgentState(TypedDict):
    tool_results: List[str]
    endpoint: str
    pass_num: int
    top_sequence: str
    current_fold_score: float
    decision: str
    tools_call_count: int  # SIMPLE COUNTER instead of list
    pipeline_id: int  # Track which pipeline this is


# ============================================================================
# LLM ROUTER
# ============================================================================
def get_llm(endpoint: str) -> ChatOpenAI:
    """Create LLM client for VLLM endpoint."""
    api_endpoint = f"{endpoint}/v1" if not endpoint.endswith('/v1') else endpoint
    return ChatOpenAI(
        model="Qwen/Qwen2.5-0.5B-Instruct",
        openai_api_key="EMPTY",
        openai_api_base=api_endpoint,
        temperature=0.2,
        max_tokens=200,
    )


async def router_impl(state: AgentState) -> AgentState:
    """LLM-based router - uses simple counter."""
    endpoint = state["endpoint"]
    tools_call_count = state.get("tools_call_count", 0)
    pipeline_id = state.get("pipeline_id", 0)
    
    logger.info(f"=" * 70)
    logger.info(f"🤖 ROUTER - Pipeline {pipeline_id}")
    logger.info(f"   Tools called so far: {tools_call_count}/5")
    logger.info(f"=" * 70)
    
    # Define the FIXED sequence of tools
    all_tools = ["run_mpnn", "score_mpnn", "make_fasta", "run_alphafold", "score_alphafold"]
    
    # If we've called all 5 tools, we're done
    if tools_call_count >= 5:
        logger.info(f"🤖 Pipeline {pipeline_id}: All 5 tools called, DONE")
        return {**state, "decision": "done"}
    
    # Pick the next tool based on counter
    next_tool = all_tools[tools_call_count]
    
    logger.info(f"🤖 Pipeline {pipeline_id}: Next tool is #{tools_call_count + 1}: {next_tool}")
    
    # ALWAYS call LLM (for benchmarking) but IGNORE response
    llm = get_llm(endpoint)
    
    system_prompt = f"""You are a protein design workflow router.

Next tool to run: {next_tool}

Respond with ONLY the tool name."""

    user_prompt = f"What tool should we run next?"

    try:
        logger.info(f"🤖 Pipeline {pipeline_id}: Calling LLM...")
        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        logger.info(f"🤖 Pipeline {pipeline_id}: LLM called (response ignored)")
    except Exception as e:
        logger.warning(f"⚠️ Pipeline {pipeline_id}: LLM call failed: {e}")

    logger.info(f"🤖 Pipeline {pipeline_id}: Decision = {next_tool}")
    
    return {
        **state,
        "decision": next_tool
    }


async def router_impl_2(state: AgentState) -> AgentState:
    """LLM-based router that decides which tool to run next."""
    endpoint = state["endpoint"]
    tools_completed = state.get("tools_completed", [])
    
    logger.info(f"🤖 Router: Deciding next tool (completed: {tools_completed})")
    
    # Define the sequence of tools
    all_tools = ["run_mpnn", "score_mpnn", "make_fasta", "run_alphafold", "score_alphafold"]
    
    # Deterministic fallback based on what's completed
    remaining_tools = [t for t in all_tools if t not in tools_completed]

    if not remaining_tools:
        decision = "done"
        reasoning = "All tools completed"
        logger.info(f"🤖 Router decision: {decision} ({reasoning})")
    else:
        # Try LLM to pick next tool
        llm = get_llm(endpoint)
        
        system_prompt = f"""You are a protein design workflow router.

Available tools: {', '.join(remaining_tools)}

Tools already completed: {', '.join(tools_completed) if tools_completed else 'none'}

Respond with ONLY the name of the next tool to run, or 'done' if all tools are complete.
Valid responses: {', '.join(remaining_tools + ['done'])}"""

        user_prompt = "What tool should we run next?"
        
        try:
            response = await llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            # Parse response
            content = response.content if hasattr(response, "content") else str(response)
            if isinstance(content, dict):
                content = content.get("text", str(content))
            
            llm_decision = content.strip().lower()
            logger.info(f"🤖 LLM suggested: {llm_decision}")
            
            # Validate LLM decision
            if llm_decision in remaining_tools:
                decision = llm_decision
                reasoning = "LLM choice"
            elif llm_decision == "done" and not remaining_tools:
                decision = "done"
                reasoning = "LLM confirmed completion"
            else:
                # Fallback: take first remaining tool
                decision = remaining_tools[0]
                reasoning = f"LLM invalid ({llm_decision}), using fallback"
                
        except Exception as e:
            logger.warning(f"⚠️ LLM call failed ({e}), using fallback")
            decision = remaining_tools[0]
            reasoning = "LLM failed, using fallback"

        logger.info(f"🤖 Router decision: {decision} ({reasoning})")

    return {
        **state,
        "decision": decision
    }

async def router_impl_1(state: AgentState) -> AgentState:
    """LLM-based router that decides which tool to run next."""
    endpoint = state["endpoint"]
    tools_completed = state.get("tools_completed", [])
    
    logger.info(f"🤖 Router: Deciding next tool (completed: {tools_completed})")
    
    # Define the sequence of tools
    all_tools = ["run_mpnn", "score_mpnn", "make_fasta", "run_alphafold", "score_alphafold"]
    
    # Deterministic fallback based on what's completed
    remaining_tools = [t for t in all_tools if t not in tools_completed]

    if not remaining_tools:
        decision = "done"
        reasoning = "All tools completed"
        logger.info(f"🤖 Router decision: {decision} ({reasoning})")
    else:
        # Try LLM to pick next tool
        llm = get_llm(endpoint)
        
        system_prompt = f"""You are a protein design workflow router.

Available tools: {', '.join(remaining_tools)}

Tools already completed: {', '.join(tools_completed) if tools_completed else 'none'}

Respond with ONLY the name of the next tool to run, or 'done' if all tools are complete.
Valid responses: {', '.join(remaining_tools + ['done'])}"""

        user_prompt = "What tool should we run next?"
        
        try:
            response = await llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            # Parse response
            content = response.content if hasattr(response, "content") else str(response)
            if isinstance(content, dict):
                content = content.get("text", str(content))
            
            llm_decision = content.strip().lower()
            logger.info(f"🤖 LLM suggested: {llm_decision}")
            
            # Validate LLM decision
            if llm_decision in remaining_tools:
                decision = llm_decision
                reasoning = "LLM choice"
            elif llm_decision == "done" and not remaining_tools:
                decision = "done"
                reasoning = "LLM confirmed completion"
            else:
                # Fallback: take first remaining tool
                decision = remaining_tools[0]
                reasoning = f"LLM invalid ({llm_decision}), using fallback"
                
        except Exception as e:
            logger.warning(f"⚠️ LLM call failed ({e}), using fallback")
            decision = remaining_tools[0]
            reasoning = "LLM failed, using fallback"
        
        logger.info(f"🤖 Router decision: {decision} ({reasoning})")
    
    return {
        **state,
        "decision": decision
    }

def route_to_tool(state: AgentState) -> str:
    """Route based on router's decision."""
    decision = state.get("decision", "done")
    logger.info(f"🔀 Routing to: {decision}")
    
    if decision == "done":
        return "done"
    return decision

# ============================================================================
# TOOL IMPLEMENTATIONS (DUMMY)
# ============================================================================
async def run_mpnn_impl(**state) -> AgentState:
    """DUMMY: Simulate MPNN sequence generation."""
    pass_num = state.get("pass_num", 1)
    tools_call_count = state.get("tools_call_count", 0)
    pipeline_id = state.get("pipeline_id", 0)
    
    logger.info(f"🔧 Pipeline {pipeline_id}: MPNN running (tool {tools_call_count + 1}/5)")
    await asyncio.sleep(3)
    logger.info(f"✅ Pipeline {pipeline_id}: MPNN complete")
    
    return {
        **state,
        "tool_results": state.get("tool_results", []) + [f"mpnn_pass_{pass_num}"],
        "tools_call_count": tools_call_count + 1  # INCREMENT COUNTER
    }

async def score_mpnn_impl(**state) -> AgentState:
    """DUMMY: Simulate scoring MPNN sequences."""
    import random
    pass_num = state.get("pass_num", 1)
    tools_call_count = state.get("tools_call_count", 0)
    pipeline_id = state.get("pipeline_id", 0)
    
    logger.info(f"🔧 Pipeline {pipeline_id}: Score MPNN running (tool {tools_call_count + 1}/5)")
    await asyncio.sleep(2)
    
    dummy_sequence = "ACDEFGHIKLMNPQRSTVWY" * 10
    dummy_score = random.uniform(-5.0, -2.0)
    
    logger.info(f"✅ Pipeline {pipeline_id}: Score MPNN complete: {dummy_score:.4f}")
    
    return {
        **state,
        "top_sequence": dummy_sequence,
        "tool_results": state.get("tool_results", []) + [f"score_mpnn: {dummy_score:.4f}"],
        "tools_call_count": tools_call_count + 1  # INCREMENT COUNTER
    }

async def make_fasta_impl(**state) -> AgentState:
    """DUMMY: Simulate creating FASTA file."""
    pass_num = state.get("pass_num", 1)
    tools_call_count = state.get("tools_call_count", 0)
    pipeline_id = state.get("pipeline_id", 0)
    
    logger.info(f"🔧 Pipeline {pipeline_id}: Make FASTA running (tool {tools_call_count + 1}/5)")
    await asyncio.sleep(1)
    logger.info(f"✅ Pipeline {pipeline_id}: Make FASTA complete")

    return {
        **state,
        "tool_results": state.get("tool_results", []) + [f"fasta_pass_{pass_num}"],
        "tools_call_count": tools_call_count + 1  # INCREMENT COUNTER
    }

async def run_alphafold_impl(**state) -> AgentState:
    """DUMMY: Simulate AlphaFold structure prediction."""
    pass_num = state.get("pass_num", 1)
    tools_call_count = state.get("tools_call_count", 0)
    pipeline_id = state.get("pipeline_id", 0)
    
    logger.info(f"🔧 Pipeline {pipeline_id}: AlphaFold running (tool {tools_call_count + 1}/5)")
    await asyncio.sleep(5)
    logger.info(f"✅ Pipeline {pipeline_id}: AlphaFold complete")
    
    return {
        **state,
        "tool_results": state.get("tool_results", []) + [f"alphafold_pass_{pass_num}"],
        "tools_call_count": tools_call_count + 1  # INCREMENT COUNTER
    }

async def score_alphafold_impl(**state) -> AgentState:
    """DUMMY: Simulate scoring AlphaFold predictions."""
    import random
    pass_num = state.get("pass_num", 1)
    tools_call_count = state.get("tools_call_count", 0)
    pipeline_id = state.get("pipeline_id", 0)
    
    logger.info(f"🔧 Pipeline {pipeline_id}: Score AlphaFold running (tool {tools_call_count + 1}/5)")
    await asyncio.sleep(2)
    
    current_fold_score = random.uniform(0.6, 0.95)
    logger.info(f"✅ Pipeline {pipeline_id}: Score AlphaFold complete: {current_fold_score:.4f}")
    
    return {
        **state,
        "current_fold_score": current_fold_score,
        "pass_num": pass_num + 1,
        "tool_results": state.get("tool_results", []) + [f"score_alphafold: {current_fold_score:.4f}"],
        "tools_call_count": tools_call_count + 1  # INCREMENT COUNTER
    }

# ============================================================================
# PIPELINE
# ============================================================================
async def run_pipeline(endpoint: str, agents_manager, pipeline_id: int = 0):
    """Execute the protein design pipeline with Flowgentic."""
    logger.info("=" * 70)
    logger.info(f"🚀 Starting Pipeline {pipeline_id}...")
    logger.info("=" * 70)

    # Wrap router with Flowgentic
    router = agents_manager.execution_wrappers.asyncflow(
        flow_type=AsyncFlowType.EXECUTION_BLOCK
    )(router_impl)
    logger.info("  ✓ Wrapped router")
    
    # Wrap tools with Flowgentic
    run_mpnn = agents_manager.execution_wrappers.asyncflow(
        flow_type=AsyncFlowType.AGENT_TOOL_AS_FUNCTION
    )(run_mpnn_impl)
    logger.info("  ✓ Wrapped run_mpnn")
    
    score_mpnn = agents_manager.execution_wrappers.asyncflow(
        flow_type=AsyncFlowType.AGENT_TOOL_AS_FUNCTION
    )(score_mpnn_impl)
    logger.info("  ✓ Wrapped score_mpnn")
    
    make_fasta = agents_manager.execution_wrappers.asyncflow(
        flow_type=AsyncFlowType.AGENT_TOOL_AS_FUNCTION
    )(make_fasta_impl)
    logger.info("  ✓ Wrapped make_fasta")
    
    run_alphafold = agents_manager.execution_wrappers.asyncflow(
        flow_type=AsyncFlowType.AGENT_TOOL_AS_FUNCTION
    )(run_alphafold_impl)
    logger.info("  ✓ Wrapped run_alphafold")
    
    score_alphafold = agents_manager.execution_wrappers.asyncflow(
        flow_type=AsyncFlowType.AGENT_TOOL_AS_FUNCTION
    )(score_alphafold_impl)
    logger.info("  ✓ Wrapped score_alphafold")
    
    logger.info("🔧 Building LangGraph with LLM router...")
    
    workflow = StateGraph(AgentState)
    
    # Add router node
    workflow.add_node("router", router)
    
    # Add tool nodes
    workflow.add_node("run_mpnn", run_mpnn)
    workflow.add_node("score_mpnn", score_mpnn)
    workflow.add_node("make_fasta", make_fasta)
    workflow.add_node("run_alphafold", run_alphafold)
    workflow.add_node("score_alphafold", score_alphafold)
    
    # Start with router
    workflow.set_entry_point("router")
    
    # Conditional edges from router to tools
    workflow.add_conditional_edges(
        "router",
        route_to_tool,
        {
            "run_mpnn": "run_mpnn",
            "score_mpnn": "score_mpnn",
            "make_fasta": "make_fasta",
            "run_alphafold": "run_alphafold",
            "score_alphafold": "score_alphafold",
            "done": END
        }
    )

    # After each tool, go back to router
    workflow.add_edge("run_mpnn", "router")
    workflow.add_edge("score_mpnn", "router")
    workflow.add_edge("make_fasta", "router")
    workflow.add_edge("run_alphafold", "router")
    workflow.add_edge("score_alphafold", "router")

    pipeline = workflow.compile()
    logger.info("✅ LangGraph compiled")

    # Initialize - USE COUNTER, NOT LIST!
    initial_state: AgentState = {
        "tool_results": [],
        "endpoint": endpoint,
        "pass_num": 1,
        "top_sequence": "",
        "current_fold_score": 0.0,
        "decision": "",
        "tools_call_count": 0,  # USE COUNTER
        "pipeline_id": pipeline_id  # UNIQUE ID
    }
    
    logger.info("🎯 Executing pipeline with LLM routing...")

    # Run with recursion limit
    config = {"recursion_limit": 1000}

    final_state = None
    try:
        async for chunk in pipeline.astream(initial_state, config=config):
            for node_name, node_state in chunk.items():
                tools_count = node_state.get('tools_call_count', 0)  # USE COUNTER
                logger.info(f"📦 Node '{node_name}' completed")
                logger.info(f"   Tools count: {tools_count}/5")  # LOG COUNTER
                final_state = node_state
    except GraphRecursionError as e:
        logger.info("🚨 LangGraph recursion limit hit! Exiting")

    logger.info("=" * 70)
    logger.info(f"✅ Pipeline {pipeline_id} complete!")
    logger.info(f"📊 Tools called: {final_state.get('tools_call_count', 0)}/5")
    logger.info(f"📊 Final fold score: {final_state.get('current_fold_score', 'N/A')}")
    logger.info("=" * 70)

    return final_state

# ============================================================================
# MAIN
# ============================================================================
async def main(num_pipelines: int=50, num_services:int=4):

    logger.info("=" * 70)
    logger.info("🐉 Initializing Dragon backend...")
    logger.info("=" * 70)

    mp.set_start_method("dragon", force=True)

    backend = await DragonExecutionBackendV3(
        num_workers=15,  # More workers for protein design tasks
        disable_background_batching=False
    )

    init_default_logger(logging.DEBUG, output_file='4-nodes-impress-a.log')

    logger.info(f"✅ Backend ready: {type(backend)}")

    logger.info("=" * 70)
    logger.info("📦 Initializing LangraphIntegration (once)...")
    logger.info("=" * 70)

    logger.info(f"Creating {num_services} VLLM services...")

    ports = []
    services = []
    nodes_per_service = 1
    # Step-2 make multiple VLLM services
    for i in range(num_services):
        port = 8000 + i
        offset = i * nodes_per_service

        logger.info(f"Service {i+1}: port={port}, offset={offset}, num_nodes={nodes_per_service}")

        service = DragonVllmInferenceBackend(
            config_file="/anvil/scratch/x-aymen/aici-dragon-inference/config.yaml",
            model_name="/anvil/scratch/x-aymen/_dragon_vllm_env/hf_cache/Qwen2.5-0.5B-Instruct",
            num_nodes=nodes_per_service,
            num_gpus=1,
            tp_size=1,
            port=port,
            offset=offset
        )
        ports.append(port)
        services.append(service)

    # Step-3 Initialize ALL services concurrently
    logger.info(f"Initializing all {num_services} services concurrently...")
    await asyncio.gather(*[service.initialize() for service in services])

    hostname = socket.getfqdn()
    service_endpoints = [f'http://{hostname}:{p}' for p in ports]
    logger.info(f"Service endpoints: {service_endpoints}")

    collector = DragonTelemetryCollector(
        collection_rate=1.0,
        checkpoint_interval=30.0,
        checkpoint_dir=os.path.join(os.getcwd(), 'telemetry-results'),
        checkpoint_count=10,
        enable_cpu=True,
        enable_gpu=True,
        enable_memory=True,
        metric_prefix="infer-asyncflow"
    )

    # Start collection
    collector.start()

    logger.info(f"All {num_services} services initialized")

    async with LangraphIntegration(backend=backend) as agents_manager:
        logger.info("✅ LangraphIntegration ready")
        logger.info(f"Round-robin: {num_pipelines} pipelines across {len(service_endpoints)} endpoints")

        tasks = []
        for i in range(num_pipelines):
            endpoint_idx = i % len(service_endpoints)
            endpoint = service_endpoints[endpoint_idx]
            logger.info(f"  Pipeline {i} → Endpoint[{endpoint_idx}]: {endpoint}")
            tasks.append(run_pipeline(endpoint, agents_manager, pipeline_id=i))  # PASS ID

        await asyncio.gather(*tasks)

    await backend.shutdown()
    collector.stop()
    os._exit(0)

    logger.info("🎉 Done!")

if __name__ == "__main__":
    logger.info("🚀 Starting main program...")
    asyncio.run(main())
