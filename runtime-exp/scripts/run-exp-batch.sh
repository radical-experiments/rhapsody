#!/bin/bash

# ============================================================
# Dragon AsyncFlow Benchmark Script
# Strong & Weak Scaling Experiments
# ============================================================

SCRIPT="dragon --w ssh --network-config slurm.yaml dragon-example-batch.py"
CONFIGS=(1 2 4 8 16)
REPEATS=3

# Strong scaling: fixed 100K tasks
run_strong_scaling() {
    BASE_TASKS=50000
    echo "============================================================"
    echo " Running STRONG SCALING: Fixed ${BASE_TASKS} tasks"
    echo "============================================================"
    echo ""

    for NUM_NODES in "${CONFIGS[@]}"; do
        for RUN_ID in $(seq 1 $REPEATS); do
            echo "Run #${RUN_ID} - ${NUM_NODES} nodes, ${BASE_TASKS} tasks"
            echo "------------------------------------------------------------"

            ${SCRIPT} \
                --nodes ${NUM_NODES} \
                --tasks ${BASE_TASKS} \
                --run_id ${RUN_ID} \
                --mode strong

            echo ""
            echo "Completed: Run #${RUN_ID} - ${NUM_NODES} nodes"
            echo "============================================================"
            echo ""
            sleep 10
        done
    done
}

# Weak scaling: tasks per node doubles, total = nodes * tasks_per_node
run_weak_scaling() {
    echo "============================================================"
    echo " Running WEAK SCALING: tasks per node doubling"
    echo "============================================================"
    echo ""

    declare -A TASK_MAP=(
        [1]=2048
        [2]=4096
        [4]=8192
        [8]=16384
        [16]=32768
    )

    for NUM_NODES in "${CONFIGS[@]}"; do
        NUM_WORKERS=$NUM_NODES
        NUM_TASKS=${TASK_MAP[$NUM_NODES]}

        for RUN_ID in $(seq 1 $REPEATS); do
            echo "Run #${RUN_ID} - ${NUM_NODES} nodes, ${NUM_TASKS} tasks"
            echo "------------------------------------------------------------"

            ${SCRIPT} \
                --nodes ${NUM_NODES} \
                --tasks ${NUM_TASKS} \
                --run_id ${RUN_ID} \
                --mode weak

            echo ""
            echo "Completed: Run #${RUN_ID} - ${NUM_NODES} nodes"
            echo "============================================================"
            echo ""
            sleep 10
        done
    done
}

# ============================================================
# Main Execution Control
# ============================================================

echo "Dragon AsyncFlow Benchmark Suite"
echo "============================================================"
echo "Available experiments: strong | weak | both"
echo ""

MODE=${1:-both}

case $MODE in
    strong)
        run_strong_scaling
        ;;
    weak)
        run_weak_scaling
        ;;
    both)
        run_strong_scaling
        run_weak_scaling
        ;;
    *)
        echo "Usage: $0 [strong|weak|both]"
        exit 1
        ;;
esac

echo "All benchmark runs completed!"
