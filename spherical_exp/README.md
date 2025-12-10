
# SPHERICAL PROTOTYPE EXPERIMENT (Dragon V3) AI-HPC Coupling.

Note: This exp. assumes that you have a redis image (if you run on HPC it should be redis-ai.sif) on your file system. 

### Installation:

Use the following tutorial to setup the enviromet:

`https://github.com/radical-cybertools/aici-dragon-inference/tree/main`

1-Setup your virtual env: Follow steps from section *Setup Virtual Environment*

2-Configure vLLM: Follow step 1 - 4 from section *Run Application*.
Fot the step 1 use *GreatCaptainNemo/ProLLaMA*

3-Install the required packages: `pip install -e "..[rhapsody-spherical]"`


### Steps tp run single experiment

- ask for interactive node(s):
   
   `sinteractive -p wholenode -N 8 -A xxxx  -t 00:60:00`

- generate the dragon `slurm.yml`

   `dragon-network-config --output-to-yaml`

- modify the following line in *run_me.py* if you prefer to use your owm LLM

`model_name="/anvil/scratch/x-mgoliyad1/cache/transformers/cache/models--GreatCaptainNemo--ProLLaMA/snapshots/983b5d4ff8fa82948bc68c5f02c65d4f4c76d650"`
- run experiment

   ```
   dragon --w ssh --network-config slurm.yaml scripts/run_me.py \
    ```


### Plotting the results
`python plot.py`
