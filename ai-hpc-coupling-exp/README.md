# ROSE + SmartSim + RHAPSODY (Dragon V2) AI-HPC Coupling Exp.

Note: This exp. assumes that you have a redis image (if you run on HPC it should be redis-ai.sif) on your file system. 

### Steps to the complete experiment 

1-8 nodes for each datapoint we do X3 times run

`sbatch submit-exp.sbatch`

### Steps tp run single experiment

- ask for interactive node(s):
   
   `sinteractive -p wholenode -N 8 -A xxxx  -t 00:60:00`

- generate the dragon `slurm.yml`

   `dragon-network-config --output-to-yaml`

- run redis (in-mempry coupling) or file-system couploing mode

   ```
   dragon --w ssh --network-config slurm.yaml scripts/ai-hpc-coupling.py \
                --num_nodes 8 \
                --num_database_nodes 8 \
                --num_simulations 1600 \
                --mode redis \
                --run_id 1
                --output_dir 8nodes-results
    ```


### Plotting the results
`python plot.py`
