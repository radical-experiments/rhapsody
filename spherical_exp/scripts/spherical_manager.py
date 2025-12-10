#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# Async-friendly Spherical manager for orchestrating simulations
# ------------------------------------------------------------------------------

import asyncio
import queue
import os
from collections import OrderedDict
from logger import Logger
from rose import Learner
from typing import List
import sys

SEQ = "MGEAMGLTQPAVSRAVARLEERVGIRIFNRTARAITLTDEGRRFYEAVAPLLAGIEMHGY"


class Spherical_manager():
    """
    Orchestrates the scheduling, monitoring, and cancellation of simulations
    in an AI-steered ensemble simulation workflow.
    """

    def __init__(self, asyncflow, **kwargs):
        self.learner = Learner(asyncflow)
        self.logger = Logger(use_colors=True)
        self.endpoint = kwargs.get('endpoint', None)
        if self.endpoint is None:
            raise ValueError("endpoint must be provided")
        self.src_dir = kwargs.get('src_dir', os.getcwd())
        self.code_path = kwargs.get('code_path', f'{sys.executable} {self.src_dir}')

        self.registered_sims = OrderedDict()   # Active simulations: {tag: asyncio.Task}
        self.inf_results = []                   # Inference results
        self.sim_task_queue = asyncio.Queue()  # Queue of pending simulation inputs
        self.prompt_queue = asyncio.Queue()

        self.debug = False

        # Training parameters
        self.iteration = 0
        self.training_epochs = kwargs.get('training_epochs', 2)
        self.retrain_model = kwargs.get('retrain_model', True)
        self.model_filename = 'model.pkl'
        # Tuning parameters (should be configurable)
        self.time_between_predictions = 0.20     # Delay between prediction checks

        # Inference parameters
        self.total_num_prompts = kwargs.get('total_num_prompts', 1000)
        self.prompt_batch_size = kwargs.get('prompt_batch_size', 1000)
        self.num_services = kwargs.get('num_services', 2)
        self.inf_batches = self.total_num_prompts // self.prompt_batch_size

        # Simulation parameters
        self.num_sim = kwargs.get('num_sim', 300)  
        self.sim_batch_size = kwargs.get('sim_batch_size', 4)
        #self.inf_batch_size = kwargs.get('inf_batch_size', 5)

        self._register_learner_tasks()

        self.logger.info(f"Spherical Manager initialized...")

        """These attributes should be defined in pipeline subclass:
        Make sure they are set correctly!
            - self.sim_batch_size
            - self.retrain_model
        _register_learner_tasks must be defined in subclass to register all learner tasks: simulation, training, active learning, prediction.
        """



    async def clear_queue(self, q: asyncio.Queue):
        while True:
            try:
                q.get_nowait()
                q.task_done()
            except queue.Empty:
                break

    # --------------------------------------------------------------------------
    async def init_prompt_queue(self):
        """Collect all simulation input files into task queue."""
        for _ in range(self.inf_batches):
            batch = [SEQ] * self.prompt_batch_size
            await self.prompt_queue.put(batch)

    # --------------------------------------------------------------------------
    async def init_sim_queue(self):
        """Collect all simulation input files into task queue."""
        for s in range(self.num_sim):
            sim_name = f'simulation_{s}'
            sim_tag = f'{sim_name}'
            await self.sim_task_queue.put({'sim_tag': sim_tag})

    # --------------------------------------------------------------------------
    async def train_model(self):
        """
        Define all step required for model training.
        Override this with actual logic in pipeline subclass.
        """
        raise NotImplementedError("train_model must be implemented")
    
    # --------------------------------------------------------------------------
    async def shutdown(self):
        """Gracefully shutdown learner."""
        try:
            await self.learner.shutdown()
        except Exception:
            print("Error during learner shutdown")

    async def stop(self):
        """Alias for close(), can be used for external termination."""
        try:
            await self.learner.shutdown()
        except Exception:
            print("Error during learner shutdown")

    # --------------------------------------------------------------------------
    def _register_learner_tasks(self):
        """Register learner tasks: simulation, training, active learning, prediction."""

        @self.learner.simulation_task()
        async def simulation(*args, **kwargs):
            sim_tag = kwargs["sim_tag"]
            args = f'--sim_tag {sim_tag}'
            return f'{self.code_path}/simulation.py {args}'
        self.simulation = simulation

        @self.learner.training_task()
        async def training(*args, **kwargs):
            args = (
                f'--model_filename {self.model_filename} '
            )
            return f'{self.code_path}/train.py {args}'
        self.training = training

        @self.learner.active_learn_task()
        async def active_learn(*args, **kwargs):
            args = (
                f'--model_filename {self.model_filename} '
            )
            return f'{self.code_path}/active_learn.py {args}'
        self.active_learn = active_learn

    async def inference(self, prompts: List[str]):
        """Task that runs inference using HTTP requests (async)"""

        import time
        start = time.time()
        self.logger.info(f"START {self.endpoint} at {start}")
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.endpoint}/generate",
                json={"prompts": prompts, "timeout": 300},
                timeout=aiohttp.ClientTimeout(total=300)
            ) as resp:
                data = await resp.json()

        end = time.time()
        self.logger.info(f"END {self.endpoint} at {end}, duration={end-start:.2f}s")

        if data['status'] == 'success':
            self.logger.info(f'Batch of {len(prompts)} inference requests is completed on {self.endpoint}')
            return data['results']
        else:
            raise Exception(f"Service error: {data.get('message', 'Unknown error')}")

    # --------------------------------------------------------------------------
    async def run_inference(self):
        """Submit simulations from the queue and register them."""
        batch_bum = 1
        while True:
            batchs = []
            for _ in range(self.num_services):
                try:
                    batch = self.prompt_queue.get_nowait()
                    self.logger.info(f'vLLM batch has {len(batch)} prompts')
                    batchs.append(batch)
                except asyncio.QueueEmpty:
                    self.logger.info(f"No more inputs in prompt queue. {self.prompt_queue.empty()}")
                    break

            self.logger.task_started(f"Inference batch# {batch_bum}", component="inference")
            results = await asyncio.gather(*[self.inference(batch) 
                                   for batch in batchs])
            self.logger.task_completed(f"Inference batch# {batch_bum} to endpoint {self.endpoint}", component="inference")
            batch_bum += 1

            for result in results:
                self.inf_results.append(result)

            if self.prompt_queue.empty():
                self.logger.info("No more prompts in queue.")
                break

            await asyncio.sleep(0.1)

    # --------------------------------------------------------------------------
    async def submit_sims(self):
        """Submit simulations from the queue and register them."""
        while True:
            await self.monitor_sims()  # Clean up completed/failed tasks

            if self.sim_task_queue.empty() or self.prompt_queue.empty():
                self.logger.info("No more simulation inputs in queue.")
                self.sim_task_queue = asyncio.Queue()
                self.prompt_queue = asyncio.Queue()
                break

            if self.sim_batch_size <= 0:
                await asyncio.sleep(1)
                continue

            # Don't submit more than sim_batch_size simulation 
            # to have enough resources for training task
            num_to_submit = min(self.sim_batch_size, self.sim_task_queue.qsize())
            for _ in range(num_to_submit):
                try:
                    sim_inputs = self.sim_task_queue.get_nowait()
                except asyncio.QueueEmpty:
                    self.logger.info("No more simulation inputs in queue.")
                    break

                sim_tag = sim_inputs["sim_tag"]
                simul = self.simulation(sim_tag=sim_tag)
                
                self.logger.task_started(f"Sim {sim_tag}", component="simulation")
                self.registered_sims[sim_tag] = simul

            if num_to_submit > 0:
                self.logger.info(
                    f"Submitted {num_to_submit} new simulation(s)"
                )
            # Update sim_batch_size (subtract submitted items)
            self.sim_batch_size -= num_to_submit
            #await asyncio.sleep(0.1)

    # --------------------------------------------------------------------------
    async def monitor_sims(self):
        """Unregister completed/failed simulations and prepare next batch."""
        unregistered_sims = []

        for sim_tag, task in self.registered_sims.items():   
            if task.done():
                unregistered_sims.append(sim_tag)
                self.logger.task_completed(f"Sim {sim_tag}", component="simulation")
                self.sim_batch_size += 1

                if task.exception():
                    self.logger.error(
                        f"Sim {sim_tag} failed: {task.exception()}", component="simulation"
                    )                   
        await self._unregister_sims(unregistered_sims)

    # --------------------------------------------------------------------------
    async def _unregister_sims(self, unregistered_sims):
        """
            Remove completed or canceled simulations from the registry, 
            and optionally clean up files from canceled simulations 
            to exclude them from the training batch.
        """
        for tag in unregistered_sims:
            self.registered_sims.pop(tag, None)

        if unregistered_sims and not self.sim_task_queue.empty():
            # Adjust next batch size
            num_to_submit = min(self.sim_batch_size, self.sim_task_queue.qsize())
            if num_to_submit > 0:
                self.logger.info(
                f"{num_to_submit} simulations will start at next iteration"
            )
                
    # --------------------------------------------------------------------------
    async def train_model(self):
        """Train until accuracy threshold is met or epochs are exhausted."""
        self.iteration += 1
        for epoch in range(self.training_epochs):
            self.logger.info(f'Iteration {self.iteration} / Epoch {epoch + 1}', component="training")

            train_task = await self.training()
            al = await self.active_learn(train_task)

    # --------------------------------------------------------------------------
    async def teach(self):
        """
        Main event loop:
        - Collects input simulations
        - Submits and monitors tasks
        - Cancels based on predictions
        - Waits until all sims finish or queue empties
        """

        self.logger.separator("Spherical MANAGER STARTING")
        await self.init_sim_queue()
        await self.init_prompt_queue()

        submit_task = asyncio.create_task(self.submit_sims())
        run_inference = asyncio.create_task(self.run_inference())
        
        while True:
            
            self.logger.info(f"{len(self.registered_sims)} simulation(s) running...")

            # Train model if flag is set
            if self.retrain_model:
                train = await self.train_model()
            else:
                await asyncio.sleep(self.time_between_predictions) 


            if self.sim_task_queue.empty() or self.prompt_queue.empty():
                await self.monitor_sims()

            # Exit if no sims left
            if self.sim_task_queue.empty() and len(self.registered_sims) == 0:
                break
            else:
                if self.debug:
                    self.logger.info(
                        f"Simulations in queue: {self.sim_task_queue.qsize()}; registered sims {len(self.registered_sims)}"
                    )

        await asyncio.sleep(1) 


        await submit_task
        await run_inference
        self.logger.manager_exiting()
        self.logger.separator("Spherical MANAGER FINISHED")
        return self.inf_results
