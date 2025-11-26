#!/bin/sh -l
  
#SBATCH -A dmr140125
#SBATCH --partition=wholenode
#SBATCH --ntasks-per-node=128
#SBATCH --nodes=8
#SBATCH --time=1:00:00
#SBATCH --job-name rhapsody-ai-hpc-dragon
#SBATCH --mail-user=aymen.alsaadi@rutgers.edu
#SBATCH --mail-type=ALL

source $HOME/ve/dragon/bin/activate

dragon-network-config --output-to-yaml

# Node counts to test
NODE_LIST="1 2 4 8"

# Modes to test
MODES="redis filesystem"

for MODE in $MODES; do
    echo "=== Running mode: $MODE ==="

    for N in $NODE_LIST; do
        SIM=$((N * 100))   # Generates 100, 200, 400, 800 automatically

        echo "-- ${N} nodes, ${MODE}, ${SIM} simulations --"

        # Run each configuration 3 times
        for RUN in 1 2 3; do
            echo "   Run $RUN..."

            dragon --w ssh \
                --network-config slurm.yaml \
                ai-hpc-coupling.py \
                --num_nodes $N \
                --num_database_nodes $N \
                --num_simulations $SIM \
                --mode $MODE \
                --run_id $RUN
                --output_dir 1-8nodes-results
        done

    done
done
