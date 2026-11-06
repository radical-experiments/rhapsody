# HPPSS W1 env — source in every shell / inside salloc
module unload python conda 2>/dev/null
module load cray-python/3.12.12
export HPPSS=$PSCRATCH/hppss
source $HPPSS/ve/bin/activate
export PATH=$HPPSS/ve/bin:$PATH
export SLURM_EXPORT_ENV=ALL
export PYTHONNOUSERSITE=1
export DRAGON_INCLUDE_DIR=$(dragon-config -o | sed 's/^-I *//')
export DRAGON_LIB_DIR=$(dragon-config -l | sed 's/^-L *//; s/ .*//')
export RADEX_INSTALL_DIR=$HPPSS/radex/install
export RADEX_DIR=$RADEX_INSTALL_DIR
module load PrgEnv-gnu cray-mpich
[ -f $HPPSS/openfoam/OpenFOAM-v2412/etc/bashrc ] && source $HPPSS/openfoam/OpenFOAM-v2412/etc/bashrc
