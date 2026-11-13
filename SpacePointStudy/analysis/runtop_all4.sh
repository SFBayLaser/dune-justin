P='physics.producers.cluster3d.Hit3DBuilderAlg'
B="$P.NoExclusivity: true\n$P.SymmetricThirdWire: true\n$P.TopNPerHit: 3\n$P.TopNRank: \"chi2\""
./runtop.sh sym_noexcl_top3_third "$B\n$P.OrphanNeedsEmptyThirdPlane: true"
./runtop.sh sym_noexcl_top3_third_both "$B\n$P.OrphanNeedsEmptyThirdPlane: true\n$P.DropOrphansSharingTriplet: true\n$P.DropOrphansNeedBothHits: true"
