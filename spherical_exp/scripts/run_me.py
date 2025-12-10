"""
Dragon V3 Workflow with Multiple VLLM Services (Node-Partitioned)
Each service uses different nodes via offset
"""
import json
import os
import asyncio
import logging
import multiprocessing as mp
import itertools
import shutil
import argparse


from radical.asyncflow import DragonVllmInferenceBackend
from radical.asyncflow import DragonTelemetryCollector
from radical.asyncflow import DragonExecutionBackendV3, WorkflowEngine
from radical.asyncflow.logging import init_default_logger
from spherical_manager import Spherical_manager

logger = logging.getLogger(__name__)

num_gpus_per_serv = 1       # GPUs per service
nodes_per_serv = 1          # Number of nodes per service - each service uses different nodes via offset

def post_process_output(infer_num, results, out_dir):

    logger.info("\n" + "=" * 60)
    logger.info("Inference Results")
    logger.info("=" * 60)

    out_file = os.path.join(out_dir, f"infer_{infer_num}.log")

    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    # Total number of prompts across all services
    total_prompts = sum(len(batch) for batch in results)

    # End-to-end total wall time = max latency across ALL requests
    total_time = max(
        r['end_to_end_latency']
        for batch in results
        for r in batch
    )

    # Prompts per second using real wall time
    prompts_per_second = total_prompts / total_time

    print("=" * 60)
    print("THROUGHPUT RESULTS")
    print("=" * 60)
    print(f"Total prompts processed: {total_prompts}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Prompts/second: {prompts_per_second:.2f}")


    # Number of service calls = number of top-level batches
    num_outputs = len(results)

    for i in range(num_outputs):
        # Collect per-service throughput (take first entry per service)
        service_total_tokens = []
        service_output_tokens = []

        for batch in results:
            # Each batch contains many requests from ONE service
            first = batch  #[i]
            service_total_tokens.append(first['total_tokens_per_second'])
            service_output_tokens.append(first['total_output_tokens_per_second'])

        # Sum throughput across services
        total_tokens_throughput = sum(service_total_tokens)
        total_output_tokens_throughput = sum(service_output_tokens)

        print(f"Total tokens/second for service {i}: {total_tokens_throughput:.2f}")
        print(f"Output tokens/second for service {i}: {total_output_tokens_throughput:.2f}")


    print(f"Services used: {num_services}")
    print("=" * 60)


async def run_Sph(out_dir, num_services, num_pipelines):
    """
    + Start Radical.Asyncflow with Dragon execution backend.
    + Start the VLLM inference engine as a service using Dragon
    + Distribuite the workflows across the services in RR fashion via Asyncflow 
    + Service endpoints are centralized on the head node for:
        - Easier endpoint management
        - Simpler load balancing
        - Centralized logging
        - Better control plane
    
    Note: Only send batch tasks. I.e, tasks that can send N requests.
    """
    mp.set_start_method("dragon")

    collector_dir = os.path.join(out_dir, 'telemetry-results')

    if os.path.isdir("path/to/directory"):
        shutil.rmtree(collector_dir)  # deletes dir and all contents
    else:
        os.makedirs(collector_dir, exist_ok=True)

    # Create Dragon backend
    backend = await DragonExecutionBackendV3(
        num_workers=15,
        disable_background_batching=False)

    #init_default_logger(logging.INFO)
    init_default_logger(logging.INFO, output_file=os.path.join(out_dir, f's{num_services}.p{num_pipelines}.log'))

    logger.info("=" * 60)
    logger.info("Dragon V3: Multi-Service VLLM Workflow (Node-Partitioned)")
    logger.info("=" * 60)

    
    services = []

    logger.info(f"Creating {num_services} VLLM services...")

    for i in range(num_services):
        port = 8000 + i
        offset = i * nodes_per_serv  # Each pipeline starts at different node

        logger.info(f"Service {i+1}: port={port}, offset={offset}, num_nodes={nodes_per_serv}")

        service = DragonVllmInferenceBackend(
            config_file="/anvil/scratch/x-mgoliyad1/aici-dragon-inference/config.yaml",
            #nferruz/ProtGPT2
            #model_name="/home/x-mgoliyad1/.cache/huggingface/hub/models--nferruz--ProtGPT2/snapshots/f71aa6cf063ad784ebd53881d11332fd098eaa58"
            #GreatCaptainNemo/ProLLaMA
            model_name="/anvil/scratch/x-mgoliyad1/cache/transformers/cache/models--GreatCaptainNemo--ProLLaMA/snapshots/983b5d4ff8fa82948bc68c5f02c65d4f4c76d650",
            num_nodes=nodes_per_serv,
            num_gpus=num_gpus_per_serv,
            tp_size=1,
            port=port,
            offset=offset  # Change this to control the number of nodes each inference pipeline takes
        )

        services.append(service)

    # Initialize ALL services concurrently
    logger.info(f"Initializing all {num_services} services concurrently...")
    await asyncio.gather(*[service.initialize() for service in services])

    # Get endpoints
    service_endpoints = [service.get_endpoint() for service in services]

    collector = DragonTelemetryCollector(
        collection_rate=1.0,              # Collect every second
        checkpoint_interval=30.0,         # Checkpoint every 30 seconds
        checkpoint_dir=os.path.join(os.getcwd(), collector_dir),  # Save checkpoints here
        checkpoint_count=10,              # Keep last 10 checkpoints
        enable_cpu=True,
        enable_gpu=True,
        enable_memory=True,
        metric_prefix="infer-asyncflow"   # Prefix all metrics
    )

    # Start collection (spawns processes on all nodes)
    collector.start()

    logger.info(f"All {num_services} services initialized")
    logger.info("Node allocation:")
    for i in range(num_services):
        offset = i * nodes_per_serv
        logger.info(f"Service {i+1}: nodes[{offset}:{offset+nodes_per_serv}] -> {service_endpoints[i]}")

    # Create round-robin load balancer
    endpoint_cycle = itertools.cycle(service_endpoints)

    # Create the async workflow engine and initialize the workflow
    asyncflow = await WorkflowEngine.create(backend)
    workflows = [Spherical_manager(asyncflow=asyncflow, 
                                   endpoint = next(endpoint_cycle),
                                   num_services=1) for _ in range(num_pipelines)]

    try:
        # Run the workflow
        #results = await workflow.teach()
        results = await asyncio.gather(*[workflow.teach() 
                                   for workflow in workflows])
        for i, res in enumerate(results):
            post_process_output(i, res, out_dir)
    except Exception as e:
        print(f"An error occurred during teaching: {e}")
    finally:
        # Ensure cleanup regardless of errors
        await asyncio.gather(*[service.shutdown() for service in services])
        for workflow in workflows:
            await workflow.shutdown()
        collector.stop()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Spherical experiment")
    parser.add_argument("--directory", type=str, help="Directory to store all data from experiment")
    parser.add_argument("--num_services", type=int, help="Total number of vLLM services")
    parser.add_argument("--num_pipelines", type=int, help="Total number of pipeline (each pipeline will use single vLLM service)")
    args = parser.parse_args()

    asyncio.run(run_Sph(out_dir=args.directory, num_services=int(args.num_services), num_pipelines=int(args.num_pipelines)))

    # dragon-network-config --output-to-yaml

    # dragon  -w ssh --network-config slurm.yaml -t hsta run_me.py
    
    # python3 plot_new_telem_infer.py  telemetry-results --out new_plot.png