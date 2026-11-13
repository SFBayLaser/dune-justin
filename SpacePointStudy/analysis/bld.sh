source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh > /dev/null 2>&1
cd /run/media/usher/Drive2/DUNE/FD/v10_24_00d00
source ./localProducts_larsoft_v10_24_00_e26_prof/setup > /dev/null 2>&1
cd build_slf7.x86_64
mrbsetenv > /dev/null 2>&1
echo "mrbsetenv rc=$?"
"$@"
