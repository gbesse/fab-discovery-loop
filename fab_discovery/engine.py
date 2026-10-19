from copy import deepcopy
import hashlib
import json
import math
import random

OUTCOMES = ("underfused", "good", "damaged")


def number(value, positive=False):
    return type(value) in (float, int) and math.isfinite(value) and (0 < value if positive else 0 <= value) and value <= 1_000_000


def validate(case):
    if not isinstance(case, dict):
        raise ValueError("invalid_case")
    hypotheses, designs = case.get("hypotheses"), case.get("designs")
    if not isinstance(hypotheses, list) or not 1 <= len(hypotheses) <= 128 or not all(isinstance(x, dict) for x in hypotheses):
        raise ValueError("invalid_hypotheses")
    if not isinstance(designs, list) or not 1 <= len(designs) <= 256 or not all(isinstance(x, dict) for x in designs):
        raise ValueError("invalid_designs")
    for collection in (hypotheses, designs):
        ids = [x.get("id") for x in collection]
        if any(not isinstance(x, str) or not x or len(x) > 128 for x in ids) or len(set(ids)) != len(ids):
            raise ValueError("invalid_ids")
    for hypothesis in hypotheses:
        if not all(number(hypothesis.get(k), True) for k in ("fuse_dose", "damage_dose", "fuse_width", "damage_width", "prior")):
            raise ValueError("invalid_hypothesis")
    for design in designs:
        if not all(number(design.get(k), True) for k in ("power", "dwell", "cost")):
            raise ValueError("invalid_design")
        if not isinstance(design.get("capabilities", []), list) or not all(isinstance(c, str) for c in design.get("capabilities", [])):
            raise ValueError("invalid_capability")
    machine = case.get("machine", {})
    if not isinstance(machine, dict) or not isinstance(machine.get("capabilities", []), list) or not all(isinstance(c, str) for c in machine.get("capabilities", [])):
        raise ValueError("invalid_machine")
    for k in ("max_power", "max_dose"):
        if not number(machine.get(k), True):
            raise ValueError("invalid_machine")
    if not number(case.get("remaining_budget")) or not number(case.get("max_damage_probability")) or case["max_damage_probability"] > 1:
        raise ValueError("invalid_budget_or_risk")
    observations = case.get("observations", [])
    if not isinstance(observations, list) or len(observations) > 1024:
        raise ValueError("invalid_observations")
    design_ids = {d["id"] for d in designs}
    for observation in observations:
        if not isinstance(observation, dict) or observation.get("design") not in design_ids or observation.get("outcome") not in OUTCOMES:
            raise ValueError("invalid_observation")
    pending = case.get("pending", [])
    if not isinstance(pending, list) or any(d not in design_ids for d in pending):
        raise ValueError("invalid_pending")
    return hypotheses, {d["id"]: d for d in designs}


def logistic(x):
    return 1 / (1 + math.exp(-min(30, max(-30, x))))


def likelihood(hypothesis, design):
    """Two toy dose thresholds, not a validated thermomechanical model."""
    dose = design["power"] * design["dwell"]
    heat = design["power"] ** 2 * design["dwell"]
    formed = logistic((dose - hypothesis["fuse_dose"]) / hypothesis["fuse_width"])
    damaged = logistic((heat - hypothesis["damage_dose"]) / hypothesis["damage_width"])
    return {"underfused": (1 - formed) * (1 - damaged), "good": formed * (1 - damaged), "damaged": damaged}


def normalize(log_weights):
    maximum = max(log_weights)
    weights = [math.exp(w - maximum) for w in log_weights]
    total = sum(weights)
    return [w / total for w in weights]


def entropy(weights):
    return -sum(w * math.log2(w) for w in weights if w > 0)


def posterior(case):
    hypotheses, designs = validate(case)
    logs = [math.log(h["prior"]) for h in hypotheses]
    for observation in case.get("observations", []):
        for i, hypothesis in enumerate(hypotheses):
            logs[i] += math.log(likelihood(hypothesis, designs[observation["design"]])[observation["outcome"]])
    return normalize(logs)


def analyze(case, strategy="information"):
    if strategy not in ("information", "yield", "cheapest"):
        raise ValueError("invalid_strategy")
    hypotheses, designs = validate(case)
    weights = posterior(case)
    current_entropy = entropy(weights)
    rows = []
    for key, design in designs.items():
        outcomes = [likelihood(h, design) for h in hypotheses]
        prediction = {o: sum(w * p[o] for w, p in zip(weights, outcomes)) for o in OUTCOMES}
        expected_entropy = 0
        for outcome in OUTCOMES:
            p = prediction[outcome]
            if p:
                conditional = [w * probabilities[outcome] / p for w, probabilities in zip(weights, outcomes)]
                expected_entropy += p * entropy(conditional)
        information = max(0.0, current_entropy - expected_entropy)
        reasons = []
        if design["power"] > case["machine"]["max_power"] or design["power"] * design["dwell"] > case["machine"]["max_dose"]:
            reasons.append("machine_limit")
        if not set(design.get("capabilities", [])) <= set(case["machine"]["capabilities"]):
            reasons.append("capability_missing")
        if key in case.get("pending", []):
            reasons.append("already_pending")
        if design["cost"] > case["remaining_budget"] + 1e-12:
            reasons.append("budget_exceeded")
        if prediction["damaged"] > case["max_damage_probability"] + 1e-12:
            reasons.append("model_risk_exceeded")
        score = information / design["cost"] if strategy == "information" else prediction["good"] / design["cost"] if strategy == "yield" else -design["cost"]
        rows.append({"id": key, "prediction": prediction, "information_bits": information,
                     "information_per_cost": information / design["cost"], "cost": design["cost"],
                     "score": score, "eligible": not reasons, "exclusions": reasons})
    eligible = sorted((r for r in rows if r["eligible"]), key=lambda r: (-r["score"], r["id"]))
    fingerprint = hashlib.sha256(json.dumps(case, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"status": "recommendation" if eligible else "no_eligible_experiment", "input_sha256": fingerprint,
            "posterior": [{"id": h["id"], "probability": w} for h, w in zip(hypotheses, weights)],
            "entropy_bits": current_entropy, "strategy": strategy, "recommendation": eligible[0]["id"] if eligible else None,
            "candidates": sorted(rows, key=lambda r: (not r["eligible"], -r["score"], r["id"])),
            "risk_scope": "conditional_on_supplied_hypotheses", "hardware_executed": False}


def observe(case, design_id, outcome, evidence_id=None):
    """Record a completed observation. Never call a machine or fabricate a measurement."""
    _, designs = validate(case)
    if design_id not in designs or outcome not in OUTCOMES:
        raise ValueError("invalid_observation")
    if evidence_id is not None and (not isinstance(evidence_id, str) or not evidence_id):
        raise ValueError("invalid_evidence")
    if evidence_id:
        existing = next((o for o in case.get("observations", []) if o.get("evidence_id") == evidence_id), None)
        if existing:
            if existing["design"] != design_id or existing["outcome"] != outcome:
                raise ValueError("invalid_evidence_conflict")
            return deepcopy(case)
    # Recording truth is allowed even when a completed experiment exceeded predicted risk.
    # Budget is accounted at completion; pending recommendations never reserve or execute it.
    if designs[design_id]["cost"] > case["remaining_budget"] + 1e-12:
        raise ValueError("invalid_insufficient_budget")
    result = deepcopy(case)
    result["remaining_budget"] = max(0, case["remaining_budget"] - designs[design_id]["cost"])
    result.setdefault("observations", []).append({"design": design_id, "outcome": outcome,
                                                  **({"evidence_id": evidence_id} if evidence_id else {})})
    result["pending"] = [x for x in result.get("pending", []) if x != design_id]
    validate(result)
    return result


def simulated_outcome(case, design_id, true_hypothesis, seed, attempt):
    hypotheses, designs = validate(case)
    ground_truth = next((h for h in hypotheses if h["id"] == true_hypothesis), None)
    if ground_truth is None or design_id not in designs:
        raise ValueError("invalid_simulation")
    # Common per-design/per-attempt random numbers; strategy names do not affect draws.
    token = hashlib.sha256(f"{seed}|{design_id}|{attempt}".encode()).digest()
    draw = random.Random(int.from_bytes(token, "big")).random()
    cumulative = 0
    probabilities = likelihood(ground_truth, designs[design_id])
    for outcome in OUTCOMES:
        cumulative += probabilities[outcome]
        if draw <= cumulative:
            return outcome
    return OUTCOMES[-1]


def benchmark(case, seeds=range(20), max_steps=8):
    validate(case)
    seeds = list(seeds)
    if not seeds or len(seeds) > 1000 or not 1 <= max_steps <= 64:
        raise ValueError("invalid_benchmark")
    runs = []
    for true in [h["id"] for h in case["hypotheses"]]:
        for seed in seeds:
            for strategy in ("information", "yield", "cheapest"):
                state = deepcopy(case)
                trace = []
                attempts = {}
                for _ in range(max_steps):
                    report = analyze(state, strategy)
                    chosen = report["recommendation"]
                    if chosen is None:
                        break
                    attempt = attempts.get(chosen, 0)
                    outcome = simulated_outcome(state, chosen, true, seed, attempt)
                    attempts[chosen] = attempt + 1
                    state = observe(state, chosen, outcome, f"simulation:{seed}:{chosen}:{attempt}")
                    trace.append({"design": chosen, "outcome": outcome})
                final = analyze(state, strategy)
                probability = next(p["probability"] for p in final["posterior"] if p["id"] == true)
                runs.append({"true_hypothesis": true, "seed": seed, "strategy": strategy,
                             "experiments": len(trace), "cost": case["remaining_budget"] - state["remaining_budget"],
                             "entropy_bits": final["entropy_bits"], "true_hypothesis_probability": probability,
                             "damaged": sum(x["outcome"] == "damaged" for x in trace), "trace": trace})
    summary = {}
    for strategy in ("information", "yield", "cheapest"):
        subset = [r for r in runs if r["strategy"] == strategy]
        summary[strategy] = {k: sum(r[k] for r in subset) / len(subset)
                             for k in ("experiments", "cost", "entropy_bits", "true_hypothesis_probability", "damaged")}
    return {"synthetic": True, "seed_count": len(seeds), "max_steps": max_steps,
            "comparison_scope": "toy_finite_hypotheses_and_three_myopic_heuristics", "summary": summary, "runs": runs}
