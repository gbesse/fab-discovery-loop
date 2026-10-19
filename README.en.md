# Fab Discovery Loop

[Français](README.md) · [Español](README.es.md)

**Which manufacturing experiment is actually worth running next?**

A local lab selects the experiment that best distinguishes explicit process hypotheses per unit of cost. After an observation, it updates their probabilities and recomputes the next trial. Machine limits, missing capabilities, pending trials, budget and conditional risk remain visible.

![Synthetic demonstration: choosing the next experiment](docs/preview-fr.png)

## Try it

Python 3.11 or newer, standard library only. No key or connected hardware.

```sh
python3 -m fab_discovery serve --lang en
```

Open `http://127.0.0.1:8765/?lang=en`. Select the **synthetic simulator's** true hypothesis, simulate a trial, watch beliefs change, and export hypotheses and observations. The entry panel records a supplied observation; entry does not prove instrumental provenance.

```sh
python3 -m fab_discovery demo --lang en
python3 -m fab_discovery analyze fab_discovery/examples/process-window.json
python3 -m fab_discovery observe case.json p1-d5 underfused measurement-001 > next.json
python3 -m fab_discovery benchmark > benchmark.json
```

`pip install .` also provides `fab-discovery`. UI and CLI messages support FR/EN/ES.

## A checkable learning loop

1. Describe finite hypotheses: formation threshold, damage threshold, transition widths and prior weight.
2. Supply candidate experiments: power, dwell time, cost and required capabilities.
3. Compute exact **expected** entropy reduction across `underfused`, `good`, and `damaged` outcomes.
4. Exclude trials exceeding budget, machine limits or conditional risk, lacking capabilities or already pending; rank the remainder by expected information/cost.
5. Record the result and update Bayesian weights in log space.

Replaying an identical `evidence_id` and result consumes no extra budget and counts no extra observation. A different payload under that identifier is rejected. Without an identifier, each observation is treated as an independent repeat. A completed observation can be recorded even if recommendation rules would have excluded the experiment: failures are preserved too.

Recommendations neither execute nor reserve equipment. Cost is deducted when recording a completed observation; teams must separately manage commands, reservations and financial commitments. A case fingerprint binds each recommendation to its supplied assumptions and measurements.

## Reproducible comparison, including tradeoffs

`benchmark` compares three myopic strategies across all three possible true hypotheses, 20 seeds and at most eight trials per campaign. Initial budget: 24 units. Random draws are shared by seed, design and repeat index.

| Strategy             | Mean cost | Mean final entropy, bits | Mean final true-hypothesis weight | Mean damaged trials |
| -------------------- | --------: | -----------------------: | --------------------------------: | ------------------: |
| Information/cost     |     23.14 |                    0.095 |                             0.973 |               0.567 |
| Predicted yield/cost |     23.37 |                    0.203 |                             0.930 |               0.417 |
| Cheapest             |     16.00 |                    1.414 |                             0.399 |               0.000 |

More learning comes with more simulated damage here; the cheapest strategy spends less. True-hypothesis weight **is not industrial accuracy**. Results depend on these toy models, parameters and seeds. No advantage over BayBE or a real process has been measured.

## Existing tools and limits

[BayBE](https://github.com/emdgroup/baybe) already provides general Bayesian optimization and experimental design. This repository does not reinvent those methods: it supplies a small standalone loop focused on hypothesis discrimination, explicit exclusions and a readable zero-dependency demo.

[Atomic Machines](https://www.atomicmachines.com/matter-compiler) describes a design/build/measure manufacturing loop. That cycle inspires this project; **no Atomic Machines API, hardware, license or affiliation is integrated**. Unlike [MeasurePlan](https://github.com/gbesse/measureplan), which allocates inspections, this loop changes the next experiment using newly learned information.

The model intentionally uses two dose thresholds and three categorical outcomes. Observations are assumed conditionally independent. A missing model can never be discovered; a confident posterior may therefore be wrong. Predicted risk is neither a safety certificate nor physical validation. No parallel-batch optimization, continuous surrogate or industrial connector is included. Simulator data are synthetic and marked in the ledger.

## Validation

```sh
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:browser
npm run format:check
```

Fourteen tests cover information gain against an independent KL formulation, exclusions, repeats, budget and numerical stability. Browser flows cover FR/EN/ES, simulation, entered observations, risk, export and mobile layout. CI checks Python 3.11/3.12 and wheel installation outside the source tree. MIT license; research alpha.
