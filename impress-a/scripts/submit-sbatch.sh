#!/bin/sh -l
  
#SBATCH -A nairr240405-gpu
#SBATCH --partition=gpu
#SBATCH --ntasks-per-node=32
#SBATCH --nodes=4
#SBATCH --gpus-per-node 1
#SBATCH --time=00:60:00
#SBATCH --job-name impress-rhapsody-dragon
#SBATCH --mail-type=ALL # When to send emails (BEGIN, END, FAIL, ALL)

source /anvil/scratch/x-aymen/_dragon_vllm_env/bin/activate

#dragon-network-config --output-to-yaml

#dragon --w ssh --network-config slurm.yaml /anvil/scratch/x-aymen/radical.asyncflow/examples/dumm-agent-closer-to-impress-with-llm-call.py

dragon -m /anvil/scratch/x-aymen/radical.asyncflow/examples/dumm-agent-closer-to-impress-with-llm-call.py
