# RHAPSODY + DRAGON Runtime system Weak and Strong Scaling

### Steps to the complete experiment 

1-16 nodes for each datapoint we do X3 times run

`sbatch submit-exp.sbatch`

### Steps tp run single experiment

- ask for interactive node(s):
   
   `sinteractive -p wholenode -N 16 -A xxxx  -t 00:60:00`

- generate the dragon `slurm.yml`

   `dragon-network-config --output-to-yaml`

- run weak/strong or both providing nodes, mode, run_id and tasks

   `dragon --w ssh --network-config slurm.yaml dragon-example-batch.py --nodes 1 --mode both --run_id 1 --tasks 1024`



### Plotting the results
`python plot-data.py *.log`
