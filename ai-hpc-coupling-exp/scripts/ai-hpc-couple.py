#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Coupling Benchmark: ROSE+SmartRedis vs ROSE+Filesystem
"""

import asyncio
import numpy as np
import logging
import argparse
import time
import json
from pathlib import Path

from dragon.infrastructure.policy import Policy
from rose import Learner
from radical.asyncflow import WorkflowEngine, DragonExecutionBackendV2
from radical.asyncflow.logging import init_default_logger
from radical.asyncflow.backends.execution.dragon import WorkerGroupConfigV2, WorkerTypeV2, PolicyConfigV2
from smartredis import Client

logger = logging.getLogger(__name__)

def get_hostnames():
    import yaml
    with open('slurm.yaml', "r") as f:
        data = yaml.safe_load(f)
    return [node_info.get("host_name") for node_info in data.values()
            if node_info.get("host_name")]

def get_worker_configs(num_nodes: int, num_workers: int, nprocs: int = 128):
    if num_nodes % num_workers != 0:
        raise ValueError(f"Cannot evenly distribute {num_nodes} nodes among {num_workers} workers")

    nodes_per_worker = num_nodes // num_workers
    hostnames = get_hostnames()
    policies = [Policy(host_name=name, placement=Policy.Placement.HOST_NAME) for name in hostnames]

    workers = []
    for worker_idx in range(num_workers):
        start_node = worker_idx * nodes_per_worker
        end_node = start_node + nodes_per_worker
        worker_policies = [PolicyConfigV2(policy=policies[node_idx], nprocs=nprocs)
                           for node_idx in range(start_node, end_node)]
        worker = WorkerGroupConfigV2(name=f"worker{worker_idx}", worker_type=WorkerTypeV2.COMPUTE, policies=worker_policies)
        workers.append(worker)
    return workers

def parse_redis_endpoint(output):
    if isinstance(output, bytes):
        output = output.decode('utf-8', errors='ignore')
    return output.strip().split('\n')[-1].strip()

def parse_args():
    parser = argparse.ArgumentParser(description='Coupling Benchmark')
    parser.add_argument('--num_nodes', type=int, required=True)
    parser.add_argument('--num_database_nodes', type=int, required=True)
    parser.add_argument('--num_simulations', type=int, required=True)
    parser.add_argument('--num_training_steps', type=int, default=100)
    parser.add_argument('--payload_size', type=int, default=4000)
    parser.add_argument('--mode', type=str, choices=['redis', 'filesystem'], required=True)
    parser.add_argument('--output_dir', type=str, default='results')
    parser.add_argument('--run_id', type=int, required=True)
    return parser.parse_args()

async def run_benchmark():
    import dragon
    import multiprocessing as mp

    args = parse_args()
    mp.set_start_method("dragon")

    # NOTE: num_nodes and num_workers are the same, this is not a mistake (1 worker per 1 node)
    workers = get_worker_configs(num_nodes=args.num_nodes, num_workers=args.num_nodes)

    engine = await DragonExecutionBackendV2({"workers": workers})
    asyncflow = await WorkflowEngine.create(engine)
    learner = Learner(asyncflow)

    logger_file_name = f"rose.dragon.{args.mode}.n{args.num_nodes}.w{args.num_nodes}.sim{args.num_simulations}.train{args.num_training_steps}.r{args.run_id}.log"

    init_default_logger(logging.INFO, output_file=logger_file_name)

    @learner.utility_task()
    async def setup_redis_on_worker(task_description={}):
        import os

        socket_file = Path("/tmp/redis.sock")
        socket_file.unlink(missing_ok=True)
        socket_file.touch(mode=0o777)

        redis_server= "/home/users/shao/dev/SmartSim/smartsim/_core/bin/redis-server"
        redisai_lib = "/home/users/shao/dev/SmartSim/smartsim/_core/lib/redisai.so"
        redisai_opt = f"--loadmodule {redisai_lib}"
        uds_opt =f"--unixsocket {str(socket_file)} --unixsocketperm 777"
        misc_opts = "--daemonize yes --protected-mode no --logfile uds.log --port 0 --save ''"

        executable = " ".join([redis_server, redisai_opt, uds_opt, misc_opts])

        return executable

    @learner.utility_task()
    async def shutdown_redis_on_worker(task_description={}):
        redis_cli = "/home/users/shao/dev/SmartSim/smartsim/_core/bin/redis-cli"
        executable = " ".join([redis_cli, "-s /tmp/redis.sock", "STOP"])
        return executable

    @learner.utility_task(as_executable=False)
    async def simulation_redis(sim_id: int, redis_address: str, num_steps: int,
                            payload_size: int, task_description={}):
        import time
        client = Client(address=redis_address, cluster=False)

        total_start = time.perf_counter()
        data_transfer_time = 0
        put_latencies = []  # NEW: Per-operation latencies

        for step in range(num_steps):
            # Simulation work
            data = np.random.rand(payload_size).astype(np.float32)
            result = data * 2.0 + np.random.rand(*data.shape)

            # Data transfer to training
            transfer_start = time.perf_counter()
            client.put_tensor(f"sim{sim_id}_step{step}", result)
            latency = time.perf_counter() - transfer_start
            put_latencies.append(latency)
            data_transfer_time += latency

        total_time = time.perf_counter() - total_start

        return {
            'sim_id': sim_id,
            'total_time': total_time,
            'data_transfer_time': data_transfer_time,
            'computation_time': total_time - data_transfer_time,
            'put_latencies': put_latencies  # NEW
        }

    @learner.utility_task(as_executable=False)
    async def training_redis(sim_id: int, redis_address: str, num_steps: int,
                            task_description={}):
        import time
        client = Client(address=redis_address, cluster=False)

        total_start = time.perf_counter()
        data_transfer_time = 0
        get_latencies = []  # NEW: Per-operation latencies

        for step in range(num_steps):
            # Data transfer from simulation
            transfer_start = time.perf_counter()
            data = client.get_tensor(f"sim{sim_id}_step{step}")
            latency = time.perf_counter() - transfer_start
            get_latencies.append(latency)
            data_transfer_time += latency

            # Training work
            trained = data * 1.5

        total_time = time.perf_counter() - total_start

        return {
            'sim_id': sim_id,
            'total_time': total_time,
            'data_transfer_time': data_transfer_time,
            'computation_time': total_time - data_transfer_time,
            'get_latencies': get_latencies  # NEW
        }

    @learner.utility_task(as_executable=False)
    async def simulation_filesystem(sim_id: int, shared_dir: str, num_steps: int,
                                    payload_size: int, task_description={}):
        import time
        import os

        total_start = time.perf_counter()
        data_transfer_time = 0
        write_latencies = []  # NEW

        for step in range(num_steps):
            # Simulation work
            data = np.random.rand(payload_size).astype(np.float32)
            result = data * 2.0 + np.random.rand(*data.shape)

            # Data transfer to training (write file)
            transfer_start = time.perf_counter()
            filepath = f"{shared_dir}/sim{sim_id}_step{step}.npy"
            np.save(filepath, result)
            os.sync()  # Force write
            latency = time.perf_counter() - transfer_start
            write_latencies.append(latency)
            data_transfer_time += latency

        total_time = time.perf_counter() - total_start

        return {
            'sim_id': sim_id,
            'total_time': total_time,
            'data_transfer_time': data_transfer_time,
            'computation_time': total_time - data_transfer_time,
            'write_latencies': write_latencies  # NEW
        }

    @learner.utility_task(as_executable=False)
    async def training_filesystem(sim_id: int, shared_dir: str, num_steps: int,
                                task_description={}):
        import time
        import os

        total_start = time.perf_counter()
        data_transfer_time = 0
        read_latencies = []  # NEW

        for step in range(num_steps):
            # Data transfer from simulation (read file)
            transfer_start = time.perf_counter()
            filepath = f"{shared_dir}/sim{sim_id}_step{step}.npy"

            # Wait for file to exist
            while not os.path.exists(filepath):
                time.sleep(0.001)

            data = np.load(filepath)
            latency = time.perf_counter() - transfer_start
            read_latencies.append(latency)
            data_transfer_time += latency

            # Training work
            trained = data * 1.5

        total_time = time.perf_counter() - total_start

        return {
            'sim_id': sim_id,
            'total_time': total_time,
            'data_transfer_time': data_transfer_time,
            'computation_time': total_time - data_transfer_time,
            'read_latencies': read_latencies  # NEW
        }

    async def main():
        db_redis_map = {}
        shared_dir = "/tmp/coupling_benchmark_data"

        try:
            logger.info(f"="*70)
            logger.info(f"COUPLING BENCHMARK: {args.mode.upper()}")
            logger.info(f"  Nodes: {args.num_nodes}")
            logger.info(f"  Simulations: {args.num_simulations}")
            logger.info(f"  Training steps: {args.num_training_steps}")
            logger.info(f"  Payload size: {args.payload_size}")
            logger.info(f"="*70)

            if args.mode == 'redis':
                # Setup Redis
                redis_tasks = [setup_redis_on_worker(task_description={
                    "ranks": 1, "worker_hint": f"worker{i}", "pinning_policy": "strict"
                }) for i in range(args.num_database_nodes)]

                redis_endpoints_raw = await asyncio.gather(*redis_tasks)

                for i, endpoint in enumerate(redis_endpoints_raw):
                    db_redis_map[i] = parse_redis_endpoint(endpoint)
                    db_redis_map[i] = "unix:///tmp/redis.sock"
                    logger.info(f"  Database {i} -> {db_redis_map[i]}")
            else:
                # Create shared directory
                Path(shared_dir).mkdir(parents=True, exist_ok=True)
                logger.info(f"  Shared dir: {shared_dir}")

            # Launch simulations and training
            logger.info("\nLaunching tasks...")

            wall_clock_start = time.perf_counter()

            # Process each simulation sequentially to ensure sim+train go to same worker
            all_results = []

            for sim_id in range(args.num_simulations):
                worker_id = sim_id % args.num_nodes
                task_desc = {"ranks": 1, "worker_hint": f"worker{worker_id}", "pinning_policy": "strict"}

                if args.mode == 'redis':
                    db_id = sim_id % args.num_database_nodes
                    redis_addr = db_redis_map[db_id]

                    # Run simulation first
                    sim_result = await simulation_redis(sim_id, redis_addr, args.num_training_steps,
                                                    args.payload_size, task_desc)

                    # Then run training (same worker, same Redis)
                    train_result = await training_redis(sim_id, redis_addr, args.num_training_steps, task_desc)

                else:
                    # Run simulation first
                    sim_result = await simulation_filesystem(sim_id, shared_dir, args.num_training_steps,
                                                            args.payload_size, task_desc)

                    # Then run training (same worker)
                    train_result = await training_filesystem(sim_id, shared_dir, args.num_training_steps, task_desc)

                all_results.append((sim_result, train_result))

            wall_clock_time = time.perf_counter() - wall_clock_start

            logger.info(f"✅ Completed in {wall_clock_time:.2f}s")

            # Aggregate results
            sim_results = [r[0] for r in all_results]
            train_results = [r[1] for r in all_results]

            total_sim_time = sum(r['total_time'] for r in sim_results)
            total_train_time = sum(r['total_time'] for r in train_results)
            total_sim_transfer = sum(r['data_transfer_time'] for r in sim_results)
            total_train_transfer = sum(r['data_transfer_time'] for r in train_results)
            total_sim_compute = sum(r['computation_time'] for r in sim_results)
            total_train_compute = sum(r['computation_time'] for r in train_results)

            # Collect all latencies
            if args.mode == 'redis':
                all_put_latencies = []
                all_get_latencies = []
                for r in sim_results:
                    all_put_latencies.extend(r['put_latencies'])
                for r in train_results:
                    all_get_latencies.extend(r['get_latencies'])

                put_latencies_ms = np.array(all_put_latencies) * 1000
                get_latencies_ms = np.array(all_get_latencies) * 1000
            else:
                all_write_latencies = []
                all_read_latencies = []
                for r in sim_results:
                    all_write_latencies.extend(r['write_latencies'])
                for r in train_results:
                    all_read_latencies.extend(r['read_latencies'])

                write_latencies_ms = np.array(all_write_latencies) * 1000
                read_latencies_ms = np.array(all_read_latencies) * 1000

            stats = {
                'config': {
                    'mode': args.mode,
                    'num_nodes': args.num_nodes,
                    'num_database_nodes': args.num_database_nodes,
                    'num_simulations': args.num_simulations,
                    'num_training_steps': args.num_training_steps,
                    'payload_size': args.payload_size
                },
                'timing': {
                    'wall_clock_time': wall_clock_time,
                    'total_simulation_time': total_sim_time,
                    'total_training_time': total_train_time,
                    'avg_sim_time': total_sim_time / len(sim_results),
                    'avg_train_time': total_train_time / len(train_results)
                },
                'breakdown': {
                    'total_data_transfer_time': total_sim_transfer + total_train_transfer,
                    'total_computation_time': total_sim_compute + total_train_compute,
                    'data_transfer_pct': (total_sim_transfer + total_train_transfer) / wall_clock_time * 100,
                    'computation_pct': (total_sim_compute + total_train_compute) / wall_clock_time * 100
                }
            }

            # Add latency statistics
            if args.mode == 'redis':
                stats['coupling_latencies'] = {
                    'put_ms': {
                        'mean': float(np.mean(put_latencies_ms)),
                        'std': float(np.std(put_latencies_ms)),
                        'median': float(np.median(put_latencies_ms)),
                        'p95': float(np.percentile(put_latencies_ms, 95)),
                        'p99': float(np.percentile(put_latencies_ms, 99)),
                        'min': float(np.min(put_latencies_ms)),
                        'max': float(np.max(put_latencies_ms)),
                        'all_values': put_latencies_ms.tolist()
                    },
                    'get_ms': {
                        'mean': float(np.mean(get_latencies_ms)),
                        'std': float(np.std(get_latencies_ms)),
                        'median': float(np.median(get_latencies_ms)),
                        'p95': float(np.percentile(get_latencies_ms, 95)),
                        'p99': float(np.percentile(get_latencies_ms, 99)),
                        'min': float(np.min(get_latencies_ms)),
                        'max': float(np.max(get_latencies_ms)),
                        'all_values': get_latencies_ms.tolist()
                    }
                }
            else:
                stats['coupling_latencies'] = {
                    'write_ms': {
                        'mean': float(np.mean(write_latencies_ms)),
                        'std': float(np.std(write_latencies_ms)),
                        'median': float(np.median(write_latencies_ms)),
                        'p95': float(np.percentile(write_latencies_ms, 95)),
                        'p99': float(np.percentile(write_latencies_ms, 99)),
                        'min': float(np.min(write_latencies_ms)),
                        'max': float(np.max(write_latencies_ms)),
                        'all_values': write_latencies_ms.tolist()
                    },
                    'read_ms': {
                        'mean': float(np.mean(read_latencies_ms)),
                        'std': float(np.std(read_latencies_ms)),
                        'median': float(np.median(read_latencies_ms)),
                        'p95': float(np.percentile(read_latencies_ms, 95)),
                        'p99': float(np.percentile(read_latencies_ms, 99)),
                        'min': float(np.min(read_latencies_ms)),
                        'max': float(np.max(read_latencies_ms)),
                        'all_values': read_latencies_ms.tolist()
                    }
                }

            # Save
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{args.mode}_nodes{args.num_nodes}_run{args.run_id}.json"

            with open(output_file, 'w') as f:
                json.dump(stats, f, indent=2)

            logger.info(f"\nResults saved to {output_file}")
            logger.info(f"  Wall-clock: {wall_clock_time:.3f}s")
            logger.info(f"  Data transfer: {stats['breakdown']['data_transfer_pct']:.1f}%")
            logger.info(f"  Computation: {stats['breakdown']['computation_pct']:.1f}%")

            if args.mode == 'redis':
                logger.info(f"  PUT latency: {stats['coupling_latencies']['put_ms']['mean']:.3f}ms ± {stats['coupling_latencies']['put_ms']['std']:.3f}ms")
                logger.info(f"  GET latency: {stats['coupling_latencies']['get_ms']['mean']:.3f}ms ± {stats['coupling_latencies']['get_ms']['std']:.3f}ms")
            else:
                logger.info(f"  WRITE latency: {stats['coupling_latencies']['write_ms']['mean']:.3f}ms ± {stats['coupling_latencies']['write_ms']['std']:.3f}ms")
                logger.info(f"  READ latency: {stats['coupling_latencies']['read_ms']['mean']:.3f}ms ± {stats['coupling_latencies']['read_ms']['std']:.3f}ms")

        finally:
            if args.mode == 'redis':
                logger.info("Shutting down Redis...")
                shutdowns = [shutdown_redis_on_worker(task_description={
                    "ranks": 1, "worker_hint": f"worker{i}", "pinning_policy": "strict"
                }) for i in range(args.num_database_nodes)]
                await asyncio.gather(*shutdowns)
            else:
                # Cleanup filesystem
                import shutil
                if Path(shared_dir).exists():
                    shutil.rmtree(shared_dir)

    try:
        return await main()
    finally:
        await learner.shutdown()

if __name__ == "__main__":
    asyncio.run(run_benchmark())
