# HPPSS SC26 demo environment on Perlmutter (shared, read-only deployment).
#
# Source this from your own shell: `source /pscratch/sd/m/merzky/hppss-demo/env.sh`.
# It uses only absolute paths into the shared deployment; everything you run
# writes into your current directory.  Built from:
#   rhapsody       demo/hppss  (Dragon 0.15.0 pin + OrbitDataBackend + sid filter)
#   radical.orbit  devel a843434  (incl. session-scoped notifications #146/#147, #158, #159)
#   radical.prof   2bf1eb1, radex c4b4d1f, rhapsody-plugins-openfoam 306d3f4,
#   OpenFOAM ESI v2412, cray-python 3.12.12, dragonhpc 0.15.0
HPPSS_DEMO=/pscratch/sd/m/merzky/hppss-demo
HPPSS_BUILD=/pscratch/sd/m/merzky/hppss-d015          # radex + radexWrite build
HPPSS_OPENFOAM=/pscratch/sd/m/merzky/hppss/openfoam   # OpenFOAM v2412 build

module unload python conda 2>/dev/null
module load cray-python/3.12.12
source $HPPSS_DEMO/ve/bin/activate
export PATH=$HPPSS_DEMO/ve/bin:$PATH          # Dragon needs the venv bin on PATH
export SLURM_EXPORT_ENV=ALL
export PYTHONNOUSERSITE=1
export DRAGON_INCLUDE_DIR=$(dragon-config -o | sed 's/^-I *//')
export DRAGON_LIB_DIR=$(dragon-config -l | sed 's/^-L *//; s/ .*//')
export RADEX_INSTALL_DIR=$HPPSS_BUILD/radex/install
export RADEX_DIR=$RADEX_INSTALL_DIR
module load PrgEnv-gnu cray-mpich
source $HPPSS_OPENFOAM/OpenFOAM-v2412/etc/bashrc WM_PROJECT_USER_DIR=$HPPSS_BUILD/of-user
export OPENFOAM_CASE_DIR=$HPPSS_BUILD/runs/openfoam-cases
