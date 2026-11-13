source /run/media/usher/Drive2/DUNE/dune-justin/SpacePointStudy/gallery_env.sh; cd /run/media/usher/Drive2/DUNE/dune-justin/SpacePointStudy
H=/run/media/usher/Drive2/DUNE/samples/FD_330003/hitscan_loose; SIM=/run/media/usher/Drive2/DUNE/samples/FD_330003/FD_330003_g4_detsim_supera.root
python3 sp_display.py $H/sym_noexcl_top3chi --sim-file $SIM --events 0 1 2 --out display_sym_noexcl_top3.html --title "Fast: symmetric window, no exclusivity, top-3 per hit (chi2)"; echo top3 $?
python3 sp_display.py $H/sym_noexcl_b8 --sim-file $SIM --events 0 1 2 --out display_sym_noexcl.html --title "Fast: symmetric window, no exclusivity (no top-n)"; echo symnoexcl $?
python3 sp_display.py $H/baseline_b8 --sim-file $SIM --events 0 1 2 --out display_baseline.html --title "Baseline builder (SnippetHit3DBuilderDUNE)"; echo baseline $?
