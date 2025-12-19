# **SPHERICAL Prototype Experiment (Dragon V3): AI–HPC Coupling**

**Note:** This experiment assumes you have a Redis image available on your filesystem.
On HPC systems, this should typically be `redis-ai.sif`.

---

## **Installation**

Follow the tutorial below to set up the environment:

**[https://github.com/radical-cybertools/aici-dragon-inference/tree/main](https://github.com/radical-cybertools/aici-dragon-inference/tree/main)**

1. **Set up your virtual environment**
   Follow the steps in the **Setup Virtual Environment** section.

2. **Configure vLLM**
   Follow steps 1–4 in the **Run Application** section.
   For Step 1, use the model repository: **`GreatCaptainNemo/ProLLaMA`**.

3. **Install required packages**

   ```bash
   pip install -e "..[rhapsody-spherical]"
   ```

---

## **Running a Single Experiment**

1. **Request interactive node(s):**

   ```bash
   sinteractive -p wholenode -N 8 -A xxxx -t 00:60:00
   ```

2. **Generate the Dragon `slurm.yml`:**

   ```bash
   cd spherical_exp/scripts
   dragon-network-config --output-to-yaml
   ```

3. **(Optional) Use a different LLM**
   Modify the `model_name` field in `run_me.py` if you wish to use your own model:

   ```python
   model_name = "/anvil/scratch/x-mgoliyad1/cache/transformers/cache/models--GreatCaptainNemo--ProLLaMA/snapshots/983b5d4ff8fa82948bc68c5f02c65d4f4c76d650"
   ```

4. **Run the experiment:**

   ```bash
   dragon -w ssh --network-config slurm.yaml -t hsta run_me.py --directory data/s2.p20/exp10 --num_services 2 --num_pipelines 20
   ```



## **Plotting the Results**

```bash
cd ../plots
```

To plot **average utilization and throughput**, run:

```bash
To plot three plots together - original version:
python3 rhapsody_combined_plots.py ../data --out spherical_combined.png

To plot utilization only:
python3 rhapsody_single_plot.py ../data --plot_type util --out spherical_util.png

To plot throughput only:
python3 rhapsody_single_plot.py ../data --plot_type htp --out spherical_htp.png


```

To plot **utilization across all nodes for a single run**, use:

```bash
python3 plot_new_telem_infer.py ../data/s1.p10/exp4/telemetry-results --out utilization_on_all_nodes.png
```

To plot **utilization for a single node**, use:

```bash
python3 plot_new_telem_infer.py ../data/s1.p10/exp4/telemetry-results --nodes 1 --out utilization_on_1_nodes.png
```


---

If you want, I can also prepare a **clean README-style version**, or add troubleshooting and environment notes.
