P='physics.producers.cluster3d.Hit3DBuilderAlg'
./runtop.sh sym_noexcl_top3chi_drop "$P.NoExclusivity: true\n$P.SymmetricThirdWire: true\n$P.TopNPerHit: 3\n$P.TopNRank: \"chi2\"\n$P.DropOrphansSharingTriplet: true"
./runtop.sh sym_noexcl_drop "$P.NoExclusivity: true\n$P.SymmetricThirdWire: true\n$P.DropOrphansSharingTriplet: true"
