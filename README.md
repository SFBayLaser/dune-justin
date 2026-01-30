# dune-justin

This repository contains job scripts, workflow configuration, and submission utilities
for running DUNE Monte Carlo production workflows using **justIN**.  
It is primarily intended for **multi-stage LArSoft workflows** (GEN → G4 → DETSIM → RECO),
with optional LArCV outputs, and is designed to scale from small tests to large production
campaigns.

The repository is actively used for development, testing, and production runs on the
DUNE distributed computing infrastructure.

---

## Repository Structure (high level)

```
.
├── DUNESpineWorkshop2026/
│   ├── gen.jobscript
│   ├── g4.jobscript
│   ├── detsim.jobscript
│   ├── reco.jobscript
│   ├── workflow.sh
│   ├── mcJobSubmission.py
│   └── *.json                # workflow configuration files
├── bundles/
│   └── fhicl_bundle.tgz       # packaged FHiCL files
└── README.md
```

---

## Creating a New Workflow

Workflows are typically created programmatically (recommended) using a configuration
file rather than manually assembling command-line calls.

### Basic steps

1. **Decide the workflow structure**
   - Number of stages (e.g. GEN → G4 → DETSIM → RECO)
   - Output products to keep (usually RECO and optional LArCV)
   - Events per job and total event count

2. **Create a workflow configuration file**
   - JSON format is used (YAML also supported if available)
   - Example fields include:
     - number of Monte Carlo jobs
     - job scripts per stage
     - FHiCL files
     - resource requests (walltime, memory)
     - output patterns and RSEs

3. **Run the submission script**
   ```bash
   python mcJobSubmission.py --config my_workflow_config.json
   ```

This will:
- create the workflow,
- define all stages,
- and submit the workflow to justIN.

---

## Running and Monitoring Workflows

### Submission
Once a workflow is created and submitted, justIN manages job execution automatically.

You can monitor progress via:

- **Web dashboard**  
  https://dunejustin.fnal.gov/dashboard

- **Command line**
  ```bash
  justin show-stages --workflow-id <WFID>
  justin show-jobs   --workflow-id <WFID>
  ```

For Condor-level debugging:
```bash
export GROUP=dune
condor_q -pool dunegpcoll01.fnal.gov -name dunegpschedd01.fnal.gov <cluster.proc>
```

---

## Job Outputs

- Intermediate stage outputs (GEN, G4, DETSIM) are typically short-lived
  and exist only to feed the next stage.
- Final outputs (RECO and optional LArCV ROOT files) are preserved and
  registered in Rucio/MetaCat.

Output locations can be queried with:
```bash
justin show-files --workflow-id <WFID>
justin show-replicas --file-did <DID>
```

---

## Generating Job Statistics

Job-level and workflow-level statistics can be extracted using:

- `justin show-jobs`
- Condor history (`condor_history`)
- Log parsing (CPU time, memory usage, wall time)

Typical statistics of interest:
- Success / failure rates per stage
- CPU and wall time distributions
- Memory usage
- Throughput (events/day)

Dedicated scripts for aggregating and plotting statistics are expected to evolve
as production usage grows.

---

## Best Practices

- Use **moderate workflow sizes** rather than extremely large single workflows.
- Prefer **fewer stages** when intermediate outputs do not need to be preserved.
- Use short Rucio lifetimes for intermediate products.
- Test new job scripts with small MC counts before scaling up.

---

## To Do

- [ ] Add automated job statistics collection scripts
- [ ] Document recommended site/RSE selections
- [ ] Add example multi-step (combined) job scripts
- [ ] Improve error handling and restart guidance
- [ ] Provide example campaign-based production layouts
- [ ] Add CI checks for jobscript syntax
- [ ] Expand documentation for new users

---

## Notes

This repository reflects active development and real production usage.
Interfaces, scripts, and conventions may evolve as justIN and DUNE computing
infrastructure change.

Feedback and contributions are welcome.

