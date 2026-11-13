P='physics.producers.cluster3d.Hit3DBuilderAlg'
./runtop.sh sym_noexcl_top3chi "$P.NoExclusivity: true\n$P.SymmetricThirdWire: true\n$P.TopNPerHit: 3\n$P.TopNRank: \"chi2\""
./runtop.sh sym_noexcl_top3time "$P.NoExclusivity: true\n$P.SymmetricThirdWire: true\n$P.TopNPerHit: 3\n$P.TopNRank: \"time\""
./runtop.sh noexcl_top3chi "$P.NoExclusivity: true\n$P.TopNPerHit: 3\n$P.TopNRank: \"chi2\""
./runtop.sh sym_noexcl_top5chi "$P.NoExclusivity: true\n$P.SymmetricThirdWire: true\n$P.TopNPerHit: 5\n$P.TopNRank: \"chi2\""
