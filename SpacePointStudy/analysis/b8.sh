source /run/media/usher/Drive2/DUNE/dune-justin/SpacePointStudy/gallery_env.sh; cd /run/media/usher/Drive2/DUNE/dune-justin/SpacePointStudy
for n in baseline new_default noexcl sym_noexcl; do
  python3 sp_truth_dep.py /run/media/usher/Drive2/DUNE/samples/FD_330003/hitscan_loose/${n}_b8 --sim-file /run/media/usher/Drive2/DUNE/samples/FD_330003/FD_330003_g4_detsim_supera.root --cache /run/media/usher/Drive2/DUNE/samples/FD_330003/hitscan_loose/truth_ide_cache.pkl --events 8 --dump --ball --ball-recall --ball-recall-r 1 --ball-recall-f 0.05 0.2 > /run/media/usher/Drive2/DUNE/samples/FD_330003/hitscan_loose/${n}_b8/run.log 2>&1; echo $n $?
done
