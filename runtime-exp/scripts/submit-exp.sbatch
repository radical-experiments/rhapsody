#!/bin/sh -l
  
#SBATCH -A dmr140125
#SBATCH --partition=wholenode
#SBATCH --ntasks-per-node=128
#SBATCH --nodes=16
#SBATCH --time=1:00:00
#SBATCH --job-name rhapsody-dragon
#SBATCH --mail-user=aymen.alsaadi@rutgers.edu
#SBATCH --mail-type=ALL # When to send emails (BEGIN, END, FAIL, ALL)

source $HOME/ve/dragon/bin/activate

dragon-network-config --output-to-yaml

./run-exp-batch.sh both
