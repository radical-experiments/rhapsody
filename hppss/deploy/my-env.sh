# HPPSS demo: shared deployment + my own TLS pair and token
source /pscratch/sd/m/merzky/hppss-demo/env.sh
export HPPSS_WORK=/pscratch/sd/m/merzky/hppss-rehearsal-2026-11-05
export ORBIT_DEMO_VE=/pscratch/sd/m/merzky/hppss-demo/ve
export ORBIT_DEMO_ENV=$HPPSS_WORK/my-env.sh
export RADICAL_ORBIT_BROKER_CERT=$HPPSS_WORK/tls/broker_cert.pem
export RADICAL_ORBIT_BROKER_KEY=$HPPSS_WORK/tls/broker_key.pem
export RADICAL_ORBIT_BROKER_TOKEN=$(cat $HPPSS_WORK/tls/broker.token)
export RADICAL_ORBIT_PSIJ_DIR=$HPPSS_WORK/psij
