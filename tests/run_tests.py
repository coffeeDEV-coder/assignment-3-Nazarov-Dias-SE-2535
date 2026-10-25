"""Own test suite for Assignment 3 (Python).

Run from the repository root:
    python tests/run_tests.py

What it does
  1. Builds the test cases (hand-made, boundary, full-limit, deep chains and
     seeded random fuzz). Every case carries a written justification.
  2. Sends ALL cases through src/Python/main.py in ONE process, twice (second
     pass in reverse order, with pings in between) to check state reset.
  3. Validates every output semantically with tests/validators.py.
  4. Checks the validators themselves: an alternative valid answer must be
     accepted and an invalid witness must be rejected.
  5. Calls the route helper for reachable / source / unreachable / tied cases.
  6. Writes tests/my_cases.jsonl (inputs) and tests/results.md (inputs,
     justification, actual outputs, verdicts, commands).
"""
import json
import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src", "Python")
sys.path.insert(0, HERE)
sys.path.insert(0, SRC)

import validators as V  # noqa: E402
import algorithms  # noqa: E402

SEED = 20260101
BIG = 1_000_000_000
N_MAX, M_MAX = 100_000, 250_000
CASES = []  # (name, request, justification)


def add(name, request, why):
    CASES.append((name, request, why))


def both(name, n, edges, why):
    add(name + " [kruskal]", {"task": "kruskal", "n": n, "edges": edges}, why)
    add(name + " [prim]", {"task": "prim", "n": n, "edges": edges}, why)


# ---------------------------------------------------------------- DSU
add("dsu: spec example", {"task": "dsu", "n": 4, "operations": [[0, 1], [1, 2], [0, 2], [3, 3]]},
    "0-1 -> 3 comps, largest 2; 1-2 -> 2 comps, largest 3; 0-2 repeated and 3-3 self-union change nothing. Expected [[3,2],[2,3],[2,3],[2,3]].")
add("dsu: n=0", {"task": "dsu", "n": 0, "operations": []}, "Empty graph: states=[].")
add("dsu: n=1 self-union", {"task": "dsu", "n": 1, "operations": [[0, 0], [0, 0]]},
    "One vertex: always [1,1] after each operation.")
add("dsu: no operations", {"task": "dsu", "n": 5, "operations": []}, "q=0 gives states=[].")
add("dsu: repeated unions", {"task": "dsu", "n": 3, "operations": [[0, 1], [1, 0], [0, 1], [2, 2], [1, 2]]},
    "Expected [[2,2],[2,2],[2,2],[2,2],[1,3]].")
_r = random.Random(SEED)
add("dsu: chain n=100000 + random unions (q=250000)",
    {"task": "dsu", "n": N_MAX,
     "operations": [[i, i + 1] for i in range(N_MAX - 1)] + [[_r.randrange(N_MAX), _r.randrange(N_MAX)] for _ in range(M_MAX - N_MAX + 1)]},
    "Full limits. After the chain everything is one component of size n; later states stay [1,100000].")

# --------------------------------------------------- Kruskal and Prim
both("mst: spec example", 4, [[0, 1, 4], [1, 2, 2], [0, 2, 3]],
     "Edges 1(w2)+2(w3)=5, vertex 3 isolated -> components=2, 2 edges.")
both("mst: n=0", 0, [], "Empty graph: cost 0, no edges, components 0.")
both("mst: n=1", 1, [], "Single vertex: cost 0, components 1.")
both("mst: isolates only", 5, [], "No edges: 5 components, cost 0.")
both("mst: self-loops only", 3, [[0, 0, -5], [1, 1, 7]],
     "Loops are never selected even if negative: cost 0, 3 components.")
both("mst: parallel + tied edges", 3, [[0, 1, 5], [0, 1, 2], [0, 1, 2], [1, 2, 2], [1, 2, 2]],
     "Cheapest 0-1 is 2 (id 1 or 2), cheapest 1-2 is 2 (id 3 or 4): cost 4, one component.")
both("mst: negative weights", 4, [[0, 1, -3], [1, 2, -4], [0, 2, -10], [2, 3, 5], [3, 3, -100]],
     "All forest edges are forced by connectivity: -10 (0-2), -4 (1-2) and 5 (2-3) -> -9. The loop is ignored.")
both("mst: total beyond 32 bits", 6, [[i, i + 1, BIG] for i in range(5)],
     "Path of 5 edges of 10^9: cost 5*10^9 = 5000000000 > 2^31.")
both("mst: total beyond 32 bits (negative)", 6, [[i, i + 1, -BIG] for i in range(5)],
     "Cost -5000000000.")
both("mst: two components + isolate", 7, [[0, 1, 1], [1, 2, 1], [3, 4, 9]],
     "Components {0,1,2},{3,4},{5},{6} -> 4; n-c=3 edges; cost 11.")
both("mst: cycle chooses cheaper chord", 4, [[0, 1, 10], [1, 2, 1], [2, 3, 1], [3, 0, 1], [0, 2, 50]],
     "Three weight-1 edges connect all vertices: cost 3.")
_r = random.Random(SEED + 1)
_big_mst = [[_r.randrange(N_MAX), _r.randrange(N_MAX), _r.randint(-BIG, BIG)] for _ in range(M_MAX)]
both("mst: random n=100000 m=250000", N_MAX, _big_mst,
     "Full limits, seed %d+1. Checked against an independent reference MST." % SEED)
both("mst: path n=100000", N_MAX, [[i, i + 1, BIG - i] for i in range(N_MAX - 1)],
     "Deep path: every edge is forced, cost = sum(10^9-i). Tests deep structure.")

# ---------------------------------------------------------------- SCC
add("scc: spec example", {"task": "scc", "n": 4, "edges": [[0, 1], [1, 0], [1, 2], [0, 2], [2, 3]]},
    "SCCs {0,1},{2},{3}; condensation has exactly two pairs ({0,1}->{2}, {2}->{3}), the duplicate 0->2 and 1->2 collapse.")
add("scc: n=0", {"task": "scc", "n": 0, "edges": []}, "Empty: both arrays empty.")
add("scc: isolates", {"task": "scc", "n": 3, "edges": []}, "Three singleton SCCs, empty condensation.")
add("scc: self-loop and duplicates", {"task": "scc", "n": 3, "edges": [[0, 0], [0, 1], [0, 1], [1, 2]]},
    "Self-loop is internal; duplicates collapse; three SCCs, two condensation pairs.")
add("scc: two cycles linked", {"task": "scc", "n": 6, "edges": [[0, 1], [1, 2], [2, 0], [3, 4], [4, 5], [5, 3], [2, 3], [0, 4]]},
    "SCC {0,1,2} and {3,4,5}; both cross edges give the single pair A->B.")
add("scc: one big cycle n=100000", {"task": "scc", "n": N_MAX, "edges": [[i, (i + 1) % N_MAX] for i in range(N_MAX)]},
    "Deep cycle: all vertices in one SCC, empty condensation.")
add("scc: chain n=100000", {"task": "scc", "n": N_MAX, "edges": [[i, i + 1] for i in range(N_MAX - 1)]},
    "Deep chain: 100000 singleton SCCs, 99999 condensation pairs.")
_r = random.Random(SEED + 2)
add("scc: random n=100000 m=250000", {"task": "scc", "n": N_MAX, "edges": [[_r.randrange(N_MAX), _r.randrange(N_MAX)] for _ in range(M_MAX)]},
    "Full limits, seed %d+2. Checked against iterative Tarjan." % (SEED))

# --------------------------------------------------------------- topo
add("topo: spec example", {"task": "topo", "n": 4, "edges": [[0, 2], [1, 2], [2, 3]]},
    "Acyclic; any order with 0,1 before 2 before 3.")
add("topo: n=0", {"task": "topo", "n": 0, "edges": []}, "acyclic=true, order=[].")
add("topo: self-loop", {"task": "topo", "n": 2, "edges": [[1, 1]]}, "A self-loop is a cycle: false, [].")
add("topo: diamond (finished vertex, no cycle)", {"task": "topo", "n": 4, "edges": [[0, 1], [0, 2], [1, 3], [2, 3]]},
    "Edge 2->3 reaches an already finished vertex: this is NOT a cycle; acyclic=true.")
add("topo: duplicate edges", {"task": "topo", "n": 3, "edges": [[0, 1], [0, 1], [1, 2]]}, "Duplicates are harmless: acyclic.")
add("topo: cycle in second component", {"task": "topo", "n": 6, "edges": [[0, 1], [1, 2], [3, 4], [4, 5], [5, 3]]},
    "Whole graph is checked: cycle 3->4->5->3 gives false, [].")
add("topo: chain n=100000", {"task": "topo", "n": N_MAX, "edges": [[i, i + 1] for i in range(N_MAX - 1)]},
    "Deep chain, acyclic; order must be 0..n-1.")
add("topo: chain with back edge n=100000", {"task": "topo", "n": N_MAX, "edges": [[i, i + 1] for i in range(N_MAX - 1)] + [[N_MAX - 1, 0]]},
    "Deep cycle: false, [].")
_r = random.Random(SEED + 3)
_perm = list(range(N_MAX))
_r.shuffle(_perm)
_dag_e = []
for _ in range(M_MAX):
    a, b = sorted(_r.sample(range(N_MAX), 2))
    _dag_e.append([_perm[a], _perm[b]])
add("topo: random DAG n=100000 m=250000", {"task": "topo", "n": N_MAX, "edges": _dag_e},
    "Edges respect a hidden random permutation, so the graph is acyclic.")

# ---------------------------------------------------------------- DAG
add("dag: spec example", {"task": "dag", "n": 5, "source": 0, "edges": [[0, 1, 3], [0, 2, 8], [1, 2, -7], [2, 3, 4]]},
    "d=[0,3,-4,0,null]: 0->1->2 costs -4, then 2->3 gives 0. Vertex 4 unreachable. parent=[-1,0,2,3,-1].")
add("dag: n=1", {"task": "dag", "n": 1, "source": 0, "edges": []}, "Only the source: distance [0], parent [-1].")
add("dag: reachable distance -1 is finite", {"task": "dag", "n": 3, "source": 0, "edges": [[0, 1, 4], [1, 2, -5]]},
    "Vertex 2 has distance -1 (a real value, not 'unreachable').")
add("dag: cycle unreachable from source", {"task": "dag", "n": 4, "source": 0, "edges": [[0, 1, 1], [2, 3, 1], [3, 2, 1]]},
    "Cycle 2<->3 is not reachable from 0 but the whole graph is checked: false, [], [].")
add("dag: self-loop", {"task": "dag", "n": 2, "source": 0, "edges": [[0, 1, 1], [1, 1, 0]]}, "Self-loop is a cycle.")
add("dag: source in the middle, unreachable ancestors", {"task": "dag", "n": 5, "source": 2, "edges": [[0, 1, 1], [1, 2, 1], [2, 3, 2], [3, 4, 2]]},
    "Vertices 0,1 are before the source: null/-1. d(3)=2, d(4)=4.")
add("dag: parallel and tied edges", {"task": "dag", "n": 3, "source": 0, "edges": [[0, 1, 5], [0, 1, 2], [0, 1, 2], [1, 2, 1], [0, 2, 3]]},
    "d(1)=2 via id 1 or 2; d(2)=3 via id 3 (2+1) or id 4 (3): both ids valid.")
add("dag: long chain with weights 10^9 (n=100000)", {"task": "dag", "n": N_MAX, "source": 0, "edges": [[i, i + 1, BIG] for i in range(N_MAX - 1)]},
    "d(n-1) = 99999*10^9 = 99999000000000 (beyond 32 bits).")
add("dag: long chain with weights -10^9 (n=100000)", {"task": "dag", "n": N_MAX, "source": 0, "edges": [[i, i + 1, -BIG] for i in range(N_MAX - 1)]},
    "d(n-1) = -99999000000000.")
_r = random.Random(SEED + 4)
_perm = list(range(N_MAX))
_r.shuffle(_perm)
_dg = []
for _ in range(M_MAX):
    a, b = sorted(_r.sample(range(N_MAX), 2))
    _dg.append([_perm[a], _perm[b], _r.randint(-BIG, BIG)])
add("dag: random DAG n=100000 m=250000", {"task": "dag", "n": N_MAX, "source": _perm[0], "edges": _dg},
    "Full limits, source is the first vertex of the hidden order. Checked against an independent Kahn-based reference.")

# ------------------------------------------------- seeded random fuzz
_r = random.Random(SEED + 5)
for k in range(60):
    n = _r.randint(0, 7)
    m = _r.randint(0, 10) if n else 0
    we = [[_r.randrange(n), _r.randrange(n), _r.randint(-4, 4)] for _ in range(m)]
    de = [[u, v] for u, v, _ in we]
    add("fuzz %d: kruskal" % k, {"task": "kruskal", "n": n, "edges": we}, "Small random graph; optimum also confirmed by brute force.")
    add("fuzz %d: prim" % k, {"task": "prim", "n": n, "edges": we}, "Same graph as the Kruskal fuzz case.")
    add("fuzz %d: scc" % k, {"task": "scc", "n": n, "edges": de}, "Small random digraph.")
    add("fuzz %d: topo" % k, {"task": "topo", "n": n, "edges": de}, "Small random digraph.")
    add("fuzz %d: dsu" % k, {"task": "dsu", "n": n, "operations": [[_r.randrange(n), _r.randrange(n)] for _ in range(_r.randint(0, 8))] if n else []}, "Small random unions.")
    if n:
        add("fuzz %d: dag" % k, {"task": "dag", "n": n, "source": _r.randrange(n), "edges": we}, "Small random digraph (may contain cycles).")


# ------------------------------------------------------------- running
def run_batch(requests):
    data = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in requests)
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, os.path.join(SRC, "main.py")], input=data.encode("utf-8"),
                       capture_output=True, timeout=300)
    dt = time.perf_counter() - t0
    if p.returncode != 0:
        raise SystemExit("main.py crashed:\n" + p.stderr.decode("utf-8", "replace")[-2000:])
    lines = p.stdout.decode("utf-8").splitlines()
    if len(lines) != len(requests):
        raise SystemExit("expected %d output lines, got %d (stdout must contain only results)" % (len(requests), len(lines)))
    return [json.loads(x) for x in lines], dt


def short(obj, limit=220):
    s = json.dumps(obj, separators=(",", ":"))
    return s if len(s) <= limit else s[:limit] + "... (%d chars)" % len(s)


def describe(req):
    s = {k: v for k, v in req.items() if k not in ("edges", "operations")}
    if "edges" in req:
        s["m"] = len(req["edges"])
    if "operations" in req:
        s["q"] = len(req["operations"])
    if len(json.dumps(req)) <= 300:
        return short(req, 300)
    return short(s) + " (large input, generated with a fixed seed)"


def main():
    report = []
    failures = []
    ping = {"task": "ping"}

    # one process: ping, all cases, ping, all cases reversed
    reqs = [ping] + [c[1] for c in CASES] + [ping] + [c[1] for c in reversed(CASES)] + [ping]
    outs, dt = run_batch(reqs)
    k = len(CASES)
    first = outs[1:1 + k]
    second = list(reversed(outs[2 + k:2 + 2 * k]))
    for i in (0, 1 + k, 2 + 2 * k):
        if outs[i] != {"status": "ready"}:
            failures.append("ping not preserved at position %d" % i)

    report.append("# Test results (generated by `python tests/run_tests.py`)\n")
    report.append("Seed: %d. Batch of %d requests x 2 passes in one process took %.2f s.\n" % (SEED, k, dt))
    report.append("| # | case | pass 1 | pass 2 (reversed, same process) |\n|---|---|---|---|")
    details = []
    for i, (name, req, why) in enumerate(CASES):
        chk = V.CHECKERS[req["task"]]
        e1, e2 = chk(req, first[i]), chk(req, second[i])
        # extra independent cross-checks for tiny cases
        if name.startswith("fuzz") and req["task"] in ("kruskal", "prim"):
            br = V.brute_mst_cost(req["n"], req["edges"])
            if first[i].get("cost") != br:
                e1.append("brute-force optimum %s differs" % br)
        ok = not e1 and not e2
        if not ok:
            failures.append("%s: %s %s" % (name, e1, e2))
        report.append("| %d | %s | %s | %s |" % (i + 1, name, "PASS" if not e1 else "FAIL", "PASS" if not e2 else "FAIL"))
        if not name.startswith("fuzz"):
            details.append("### %d. %s\n- Command: `python tools/run.py --input tests/my_cases.jsonl` (or `python tests/run_tests.py`)\n- Input: `%s`\n- Expected (justified): %s\n- Actual output: `%s`\n- Verdict: %s\n"
                           % (i + 1, name, describe(req), why, short(first[i]), "PASS" if ok else "FAIL " + str(e1 + e2)))

    # ------------------------------------------- validators self-check
    report.append("\n## Validator self-check (alternative accepted, invalid witness rejected)\n")
    vc = []

    def expect(label, errs, want_ok):
        good = (not errs) == want_ok
        vc.append("- %s: %s %s" % (label, "accepted" if not errs else "rejected (%s)" % errs[0], "OK" if good else "WRONG"))
        if not good:
            failures.append("validator self-check: " + label)

    kr = {"task": "kruskal", "n": 4, "edges": [[0, 1, 4], [1, 2, 2], [0, 2, 3]]}
    expect("forest [1,2] (spec output)", V.check_forest(kr, {"cost": 5, "edge_ids": [1, 2], "components": 2}), True)
    expect("forest [2,1] (other order)", V.check_forest(kr, {"cost": 5, "edge_ids": [2, 1], "components": 2}), True)
    expect("forest [0,1] cost 6 (not optimal)", V.check_forest(kr, {"cost": 6, "edge_ids": [0, 1], "components": 2}), False)
    expect("forest with cycle [0,1,2]", V.check_forest(kr, {"cost": 9, "edge_ids": [0, 1, 2], "components": 2}), False)
    expect("forest with repeated id [1,1]", V.check_forest(kr, {"cost": 4, "edge_ids": [1, 1], "components": 2}), False)
    expect("forest with wrong component count", V.check_forest(kr, {"cost": 5, "edge_ids": [1, 2], "components": 1}), False)
    sc = {"task": "scc", "n": 4, "edges": [[0, 1], [1, 0], [1, 2], [0, 2], [2, 3]]}
    expect("scc labels [5,5,7,9] (spec output)", V.check_scc(sc, {"component": [5, 5, 7, 9], "condensation": [[5, 7], [7, 9]]}), True)
    expect("scc relabelled [0,0,1,2]", V.check_scc(sc, {"component": [0, 0, 1, 2], "condensation": [[0, 1], [1, 2]]}), True)
    expect("scc merges 0,1,2", V.check_scc(sc, {"component": [0, 0, 0, 1], "condensation": [[0, 1]]}), False)
    expect("scc duplicate pair", V.check_scc(sc, {"component": [5, 5, 7, 9], "condensation": [[5, 7], [5, 7], [7, 9]]}), False)
    expect("scc missing pair", V.check_scc(sc, {"component": [5, 5, 7, 9], "condensation": [[5, 7]]}), False)
    tp = {"task": "topo", "n": 4, "edges": [[0, 2], [1, 2], [2, 3]]}
    expect("topo [1,0,2,3]", V.check_topo(tp, {"acyclic": True, "order": [1, 0, 2, 3]}), True)
    expect("topo [0,1,2,3] (alternative)", V.check_topo(tp, {"acyclic": True, "order": [0, 1, 2, 3]}), True)
    expect("topo [2,0,1,3] (edge goes backwards)", V.check_topo(tp, {"acyclic": True, "order": [2, 0, 1, 3]}), False)
    expect("topo missing vertex", V.check_topo(tp, {"acyclic": True, "order": [0, 1, 2]}), False)
    dg = {"task": "dag", "n": 3, "source": 0, "edges": [[0, 1, 5], [0, 1, 2], [0, 1, 2], [1, 2, 1], [0, 2, 3]]}
    expect("dag parent via id 1", V.check_dag(dg, {"acyclic": True, "distance": [0, 2, 3], "parent_edge": [-1, 1, 3]}), True)
    expect("dag parent via id 2 (tie)", V.check_dag(dg, {"acyclic": True, "distance": [0, 2, 3], "parent_edge": [-1, 2, 4]}), True)
    expect("dag parent edge 0 is not tight", V.check_dag(dg, {"acyclic": True, "distance": [0, 2, 3], "parent_edge": [-1, 0, 3]}), False)
    expect("dag parent edge ends elsewhere", V.check_dag(dg, {"acyclic": True, "distance": [0, 2, 3], "parent_edge": [-1, 3, 3]}), False)
    expect("dag wrong distance", V.check_dag(dg, {"acyclic": True, "distance": [0, 2, 4], "parent_edge": [-1, 1, 3]}), False)
    report.extend(vc)

    # ------------------------------------------------- route helper
    report.append("\n## Route helper calls (`algorithms.reconstruct_route`)\n")
    E = [[0, 1, 3], [0, 2, 8], [1, 2, -7], [2, 3, 4]]
    r = algorithms.dag({"n": 5, "source": 0, "edges": E})
    helper_cases = [("reachable target 3", E, 5, 0, 3, r), ("source", E, 5, 0, 0, r), ("unreachable target 4", E, 5, 0, 4, r)]
    TE = [[0, 1, 5], [0, 1, 2], [0, 1, 2], [1, 2, 1], [0, 2, 3]]
    rt = algorithms.dag({"n": 3, "source": 0, "edges": TE})
    helper_cases.append(("tied/parallel edges, target 2", TE, 3, 0, 2, rt))
    for label, edges, n, s, t, res in helper_cases:
        route = algorithms.reconstruct_route(s, t, res["parent_edge"], edges)
        errs = V.check_route(route, s, t, edges, res["parent_edge"], res["distance"])
        used = [res["parent_edge"][v] for v in route[1:]]
        report.append("- %s: route=%s, selected edge IDs=%s, distance=%s -> %s" % (label, route, used, res["distance"][t], "OK" if not errs else "WRONG " + str(errs)))
        if errs:
            failures.append("route helper " + label + str(errs))
    # wrong direction detection
    bad = V.check_route([3, 2, 1, 0], 0, 3, E, r["parent_edge"], r["distance"])
    report.append("- reversed route [3,2,1,0] is rejected: %s" % ("OK" if bad else "WRONG"))
    if not bad:
        failures.append("reversed route not rejected")

    report.append("\n## Summary\n")
    report.append("%d cases x 2 passes, %d failures." % (k, len(failures)))
    report.append("\n## Case details\n")
    report.extend(details)

    with open(os.path.join(HERE, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    # small inputs for `python tools/run.py --input tests/my_cases.jsonl`
    with open(os.path.join(HERE, "my_cases.jsonl"), "w", encoding="utf-8") as f:
        for name, req, _ in CASES:
            if len(json.dumps(req)) < 5000 and not name.startswith("fuzz"):
                f.write(json.dumps(req, separators=(",", ":")) + "\n")

    print("cases: %d x 2 passes, time %.2f s" % (k, dt))
    if failures:
        print("FAILED (%d):" % len(failures))
        for x in failures[:20]:
            print(" -", x)
        sys.exit(1)
    print("ALL TESTS PASSED. See tests/results.md")


if __name__ == "__main__":
    main()