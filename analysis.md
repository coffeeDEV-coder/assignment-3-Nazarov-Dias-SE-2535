# Assignment 3 – Graph Algorithms: Analysis

Language: Python (`submission.json`: `{"language":"Python"}`). The runs reported below were made with Python 3.12 on Windows.
Source: `src/Python/algorithms.py` (algorithms), `src/Python/main.py` (supplied JSON Lines adapter, unchanged).
Own tests: `tests/run_tests.py`, `tests/validators.py`, `tests/my_cases.jsonl`, `tests/results.md`.
Benchmark: `tests/benchmark.py`, `tests/benchmark_results.md`.

## 1. Build, run and test commands

All commands are run from the repository root. Python needs no compilation step.

```
python tools/run.py --setup                          # launch check
python tools/run.py --check                          # 36 public cases, repeated twice in one process
python tools/run.py --input tests/my_cases.jsonl     # print actual results for my own inputs
python tests/run_tests.py                            # my test suite (writes tests/results.md)
python tests/benchmark.py                            # Kruskal vs Prim (writes tests/benchmark_results.md)
echo {"task":"ping"} | python src/Python/main.py     # manual run of the entry point (one JSON request per line)
```

## 2. Common design decisions

**Interface.** `main.py` reads one JSON request per line and prints one result per line. The six public functions
`dsu, kruskal, prim, scc, topo, dag` take the request dictionary and delegate to internal functions
(`_dsu(n, operations)`, `_kruskal(n, edges)`, …). Nothing is printed by the algorithms.

**State reset.** No module-level mutable state exists. Every call builds its own arrays (`parent`, `size`,
adjacency lists, `visited`, colour arrays, heaps, stacks) as local variables, so nothing survives between
requests. The `_DSU` object is created inside each call. This is tested by sending all test cases through one
`main.py` process twice (second pass in reverse order, with `ping` requests in between); both passes must be valid
(`tests/run_tests.py`), and the public checker repeats its batch twice in one process as well.

**Deep graphs / no recursion.** Every DFS (both Kosaraju passes, the three-state topological DFS used by
`topo` and `dag`) uses an explicit stack. Each stack frame is just a vertex; the position inside its neighbour
list is kept in a separate array `ptr[u]`, so a suspended vertex resumes where it stopped and neighbours are never
rescanned. Therefore a chain of 100 000 vertices needs no call-stack depth (tested: chains and one 100 000-vertex cycle for
`scc`, `topo`, `dag`, and a 100 000-vertex path for `kruskal`/`prim`).

**Integers.** Python integers are unbounded, so sums of weights up to 10^9 · 10^5 (≈10^14) cannot overflow. Tests include
totals beyond 32 bits (±5·10^9 and ±99 999·10^9).

**Edge IDs.** An edge ID is the position of the row in `edges`. Sorting (Kruskal) sorts a list of indices, and adjacency
lists store the ID next to the neighbour, so original IDs are never lost.

Notation: `n` vertices, `m` edges, `q` union operations, `α` inverse Ackermann function.

## 3. Methods

### 3.1 DSU (`dsu`)

**Steps.** `parent[i]=i`, `size[i]=1`, `components=n`, `largest=1` if `n>0` else 0. For each pair `[u,v]`:
`find` both ends, and if the roots differ attach the smaller tree to the larger one, add the sizes,
decrease `components` and update `largest`. Append `[components, largest]` after every operation (also for repeated and self-unions).

**`find`.** Iterative: first walk to the root, then a second walk that points every visited vertex directly to the root (path compression).

**Invariant.** After each operation, `parent` forms a forest whose trees are exactly the connected components of the
unions processed so far; `size[root]` equals the number of vertices of that tree; `components` = number of roots;
`largest` = maximum of `size[root]`.

**Correctness.** Compression and union by size do not change which vertices share a root, only the tree shape. A union
of two different roots merges exactly two components (components −1, new size = sum), and a union with equal roots changes
nothing, so repeated and self-unions leave the partition unchanged. `largest` only grows on a merge, so it is the maximum at every moment.

**Boundaries.** `n=0` → `states=[]`, `largest=0` (the initial value). `q=0` → `states=[]`. `n=1` → always `[1,1]`.
Self-union `[v,v]` and repeated union do not change the state.

**Complexity.** Time `O(n + q·α(n))` amortised, memory `O(n + q)` (the `q` states are part of the output).

### 3.2 Kruskal (`kruskal`)

**Steps.** Sort the edge IDs by weight; scan them in this order with a DSU and take an edge when its endpoints have
different roots; add its weight to `cost` and its ID to `edge_ids`. `components` is the final DSU component count
(`n − |edge_ids|`, isolated vertices included).

**Invariant.** The selected edges form a forest that is contained in some minimum spanning forest of the whole graph.
DSU components = components of the selected forest.

**Correctness.** Cut/cycle property: the lightest edge that crosses between two different components of the current
forest is safe, because the DSU test accepts exactly such edges in non-decreasing weight order. Edges with the same
endpoints component are skipped (they would close a cycle). At the end every graph component is spanned, so the result
has `n − c` edges and minimum cost; ties can give different but equally optimal forests.

**Boundaries.** Self-loops: `find(u)==find(u)`, so they are never taken. Parallel edges: the lighter one wins, the others
are skipped. Negative weights need no special treatment (only the order matters). `n=0` → cost 0, no edges, 0 components.
No edges → every vertex is a component.

**Complexity.** `O(m log m + (n+m)·α(n))`, i.e. `O(n + m log(m+1))`; memory `O(n+m)`.

### 3.3 Prim (`prim`)

**Steps.** Build adjacency lists with entries `(weight, edge_id, neighbour)`, skipping self-loops. For every vertex `s`
not yet visited, start a new component (`components += 1`), mark `s`, push its edges into a binary heap. Repeatedly pop the
lightest entry; if its neighbour is already visited, discard it (lazy deletion), otherwise visit the neighbour, add the
weight and the edge ID, and push the neighbour's edges to unvisited vertices. When the heap is empty the component is complete and
the outer loop restarts from the next unvisited vertex.

**Invariant.** The visited vertices of the current component form a tree built from selected edges, and the heap holds
all edges that leave that tree (plus stale entries to visited vertices).

**Correctness.** The lightest edge leaving the visited set is safe for the minimum spanning tree of that component (cut
property). Because the heap is rebuilt for each start vertex, every component of the graph gets its own tree; isolated
vertices give a component with no edges. This is an independent implementation (adjacency lists, heap, no DSU).

**Boundaries.** Self-loops are never inserted. Parallel and equal edges: the first one popped connects the vertex, the
others become stale. Negative weights are fine (a heap does not need non-negative keys for this algorithm). `n=0` →
the outer loop does nothing: cost 0, no edges, 0 components.

**Complexity.** Lazy heap: every edge is pushed at most twice, so `O(n + m log(m+1))` time and `O(n+m)` memory.

### 3.4 Strongly connected components (`scc`, Kosaraju)

**Steps.**
1. Build the graph and its transpose.
2. First pass: iterative DFS over the original graph from every unvisited vertex; push a vertex to `finish` when all its out-neighbours have been processed.
3. Second pass: go through `finish` in reverse order; every still-unlabelled vertex starts a DFS on the **transposed** graph; all vertices reached get the next label.
4. Condensation: for each edge `u→v` with `comp[u]≠comp[v]` add the pair `(comp[u], comp[v])` to a set; output the set.

**Invariant.** In the second pass, the DFS from the vertex with the largest remaining finish time cannot leave its own
SCC in the transposed graph, because every other SCC reachable from it in the transpose is an SCC that precedes it in the
condensation order and has already been labelled.

**Correctness.** In the first pass, for two SCCs `A→B` the maximum finish time in `A` is greater than in `B` (standard
Kosaraju lemma). Processing in decreasing finish time in the transpose therefore starts in a source component of the
remaining condensation, and the transposed DFS reaches exactly the vertices of that component. The condensation set
contains every cross pair once; internal edges and duplicates disappear.

**Boundaries.** Isolated vertices are singleton SCCs. Self-loops and duplicate edges are harmless (internal edge / set
deduplication). `n=0` → both arrays empty. Labels are consecutive integers from 0, which fit in 64 bits.

**Complexity.** Time `O(n+m)` expected (hash set for pairs), memory `O(n+m)`.

### 3.5 Topological order (`topo`)

**Steps.** Three-state DFS (0 = unvisited, 1 = active, 2 = finished) with an explicit stack and a per-vertex neighbour
pointer. For vertex `u` and neighbour `v`: if `v` is active → directed cycle, return `acyclic=false`, `order=[]`; if
unvisited → mark active and push; if finished → ignore. When all neighbours are processed, mark `u` finished and append
it to `finish`. The order is `finish` reversed. The loop starts DFS from every unvisited vertex, so the whole graph is checked.

**Invariant.** The stack contains exactly the active vertices, forming a directed path; a vertex is finished only
after all vertices reachable from it are finished.

**Correctness.** An edge to an active vertex closes a cycle with the stack path. If no such edge occurs, every edge
`u→v` ends in a finished or newly visited vertex, so `v` finishes before `u`; in the reversed finish order `u` comes before `v`.
An edge to a finished vertex alone is not a cycle (diamond test).

**Boundaries.** Self-loop: `v=u` is active → cycle. Duplicate edges are harmless. Cycle in a component that is processed later is still found. `n=0` → `acyclic=true`, `order=[]`.

**Complexity.** `O(n+m)` time and memory; each neighbour is examined once thanks to `ptr[u]`.

### 3.6 Shortest paths in a DAG (`dag`) and route helper

**Steps.**
1. Run the same three-state DFS over the **whole** graph; if a cycle is found (even one unreachable from `source`) return `acyclic=false`, `distance=[]`, `parent_edge=[]`.
2. Initialise `distance[source]=0`, `parent_edge[source]=-1`; all other entries `None` / `-1`.
3. Process vertices in topological order; skip a vertex whose distance is `None` (never relax from unreachable vertices); for every outgoing edge `(v, w, id)` set `distance[v]=distance[u]+w` and `parent_edge[v]=id` if it is shorter (or `v` was unreachable).

**Invariant.** When `u` is processed, `distance[u]` is final: all its predecessors precede it in the topological order and have already relaxed their edges into `u`. `parent_edge[v]` is the ID of an edge that ends at `v` and satisfies `distance[parent source] + w = distance[v]`.

**Correctness.** Every path to `v` ends with an edge `u→v` where `u` precedes `v`. Induction over the order: `distance[u]` is optimal, so relaxing `u→v` produces the optimum over all paths whose last edge is that edge; taking the minimum over all incoming edges gives the optimum for `v`. Negative weights do not matter because no vertex is revisited. `None` marks "unreachable" explicitly, so a finite distance of `-1` is never confused with it. The parent edges follow tight edges to the source, and a DAG has no cycle, so the walk terminates at the source.

**Boundaries.** `n=1` → `[0]`, `[-1]`. Self-loop → cyclic. Source in the middle of the order → earlier vertices stay `None/-1`. Parallel/tied edges → the first edge that reaches the minimum is kept (strict `<`), any tied edge is valid. Totals up to ±10^14 are exact.

**Complexity.** `O(n+m)` time and memory.

**Route helper.** `reconstruct_route(source, target, parent_edge, edges)`:
- `target == source` → `[source]`;
- `parent_edge[target] == -1` (unreachable) → `[]` (documented no-route result; the JSON `distance` still uses `null`);
- otherwise walk from `target` back with `v = edges[parent_edge[v]][0]` until `source`, then reverse the list.

Time and output size are `O(L)` for a route with `L` vertices.

**Actual helper calls** (from `tests/run_tests.py`, written to `tests/results.md`; the route direction and total weight are verified by `check_route`):

| Case | Graph | Result of `dag` | Route | Selected edge IDs | Check |
|---|---|---|---|---|---|
| reachable target 3 | `n=5`, edges `[0,1,3] [0,2,8] [1,2,-7] [2,3,4]`, source 0 | `distance=[0,3,-4,0,null]`, `parent_edge=[-1,0,2,3,-1]` | `[0,1,2,3]` | `[0,2,3]` | 3 + (−7) + 4 = 0 = `distance[3]`, direction 0→3 |
| source | same | same | `[0]` | `[]` | route to the source is `[source]` |
| unreachable target 4 | same | same | `[]` | `[]` | `distance[4]=null` |
| tied / parallel edges, target 2 | `n=3`, edges `[0,1,5] [0,1,2] [0,1,2] [1,2,1] [0,2,3]`, source 0 | `distance=[0,2,3]`, `parent_edge=[-1,1,4]` | `[0,2]` | `[4]` | weight 3 = `distance[2]`; the other tied route `0→1→2` (IDs 1, 3) also costs 3 and would be accepted |

## 4. Tests

`tests/run_tests.py` runs 410 requests (hand-made, boundary, full-limit, deep-chain and seeded random cases) twice in one
`main.py` process and checks each answer with independent validators from `tests/validators.py`
(simple DSU for MST cost, Kahn's algorithm for topological order and DAG distances, iterative Tarjan for SCCs,
brute-force MST for tiny graphs). Non-unique answers are checked semantically: forest feasibility and optimum cost,
exact SCC partition and condensation, topological precedence, shortest distances with valid parent paths.
The validators themselves are tested: alternative valid answers (other forest ID order, relabelled SCCs, another
topological order, a tied parent edge) are accepted, and invalid witnesses (non-optimal forest, forest with a cycle,
repeated ID, merged SCCs, duplicate condensation pair, backwards topological edge, non-tight parent edge, reversed
route) are rejected. Cases and verdicts are written to `tests/results.md`; the inputs are in `tests/my_cases.jsonl`.

**What I ran on my machine.**

- `python tools/run.py --check`: all 36 public cases passed, and so did the check that two complete batches in one process give the same state-reset result.
- `python tests/run_tests.py`: `ALL TESTS PASSED`, 410 requests in two passes (about 9.8 s on my computer).
- `python tests/benchmark.py`: finished without errors, see section 5.

## 5. Benchmark: Kruskal vs Prim

**Protocol.** Three sizes, the same graph for both methods at each size: random undirected graphs with endpoints uniform in
`0..n-1` (self-loops and parallel edges possible) and weights uniform in `[-10^9, 10^9]`, generated with
`random.Random(20260101 + size_index)`. Sizes: (n=10 000, m=40 000), (n=50 000, m=150 000), (n=100 000, m=250 000).
Before timing, both costs and component counts are compared and both forests are validated. Timer: `time.perf_counter()`.
One untimed warm-up call per method and size, then 5 timed calls; the median is reported. **Timed region:** a single call of
`algorithms.kruskal(request)` / `algorithms.prim(request)` on an in-memory request; graph generation, JSON parsing and
output are excluded for both methods. There is no compilation step in Python.

Command: `python tests/benchmark.py` (output also saved in `tests/benchmark_results.md`).

**Environment.**

- CPU: AMD64 Family 25 Model 80 (AuthenticAMD), as reported by Python's `platform.processor()`
- RAM: <8 gb>
- OS: Windows (reported as `Windows-10-10.0.22631-SP0`)
- Python: 3.11.9 (CPython)
- Timer: `time.perf_counter()`, 1 untimed warm-up call and 5 timed calls per method and size, median reported
- The benchmark was started from the VS Code terminal; I did not isolate the machine from other programs, so small fluctuations between runs are expected.

**Results** (copied from `tests/benchmark_results.md`; times are in seconds):

| n | m | method | run times (s) | median (s) | cost |
|---|---|--------|---------------|------------|------|
| 10000 | 40000 | kruskal | 0.0254, 0.0238, 0.0247, 0.0242, 0.0237 | 0.0242 | -7028788929900 |
| 10000 | 40000 | prim | 0.0667, 0.0733, 0.0682, 0.0836, 0.1888 | 0.0733 | -7028788929900 |
| 50000 | 150000 | kruskal | 0.1854, 0.1825, 0.1723, 0.1676, 0.1716 | 0.1723 | -30076262214927 |
| 50000 | 150000 | prim | 0.4094, 0.4705, 0.4222, 0.4431, 0.4086 | 0.4222 | -30076262214927 |
| 100000 | 250000 | kruskal | 0.3214, 0.3360, 0.3664, 0.4090, 0.3975 | 0.3664 | -52751843922883 |
| 100000 | 250000 | prim | 1.0220, 0.8875, 0.8535, 0.8664, 0.8835 | 0.8835 | -52751843922883 |

Both methods returned the same cost and component count at every size, and every forest passed the validator
before timing started. Median ratios Prim / Kruskal: 3.03 (n=10 000), 2.45 (n=50 000), 2.41 (n=100 000).

**Observations.** Kruskal was faster than Prim at all three sizes, by a factor of about 2.4 to 3. The ratio was
largest on the smallest graph and settled around 2.4 on the two larger ones. Both methods got slower roughly in
line with `m log m`: for example, going from m = 150 000 to m = 250 000 (a factor of 1.67) raised Kruskal's median
from 0.17 s to 0.37 s and Prim's from 0.42 s to 0.88 s. Since both algorithms have the same asymptotic bound, the gap
is a constant factor. My explanation is that Kruskal spends most of its time in `list.sort`, which is implemented
in C, while Prim has to build adjacency lists and do many heap pushes and pops in interpreted Python. I did not
profile the code, so this is a likely explanation and not something I measured.

**Limitations.** Everything ran in pure Python on one Windows computer that was not isolated from other programs. Only random graphs
were used; paths, dense graphs or graphs with many equal weights could give a different ratio. Five repetitions are
few, and some runs are clearly noisy (Prim at n = 10 000 had one run of 0.1888 s against about 0.07 s for the
others; the first Prim run at n = 100 000 took 1.0220 s against about 0.87 s later), which is why I report medians and
not means. The benchmark covers only the algorithm call itself, so reading the JSON input and printing the result
would add the same extra time to both methods. The benchmark was run with Python 3.11.9, while the assignment asks for
Python 3.12 or newer; the algorithms use nothing version-specific, but the absolute times could differ on 3.12+.

**Asymptotic argument.** Kruskal: sorting `O(m log m)` plus `O(m α(n))` for the DSU. Prim with a lazy heap:
`O(m log m)` heap operations, since each edge is pushed at most twice. Both use `O(n+m)` memory. Asymptotically they are
equal; the constant factors differ (Prim builds adjacency lists and performs heap pushes and pops in interpreted Python, Kruskal
uses the built-in sort).

## 6. Sources and AI assistance

**Sources.**

- The course lectures and the textbook description of the algorithms: Kruskal, Prim with a priority queue, Kosaraju's SCC algorithm, DFS-based topological sorting, shortest paths in a DAG by relaxation in topological order, and the disjoint-set union with path compression and union by size.
- The assignment specification in the repository README (`README.md`, `docs/Assignment_3_EN.pdf`), including the examples that I used as test cases.
- The Python standard library documentation for `heapq`, `statistics`, `time.perf_counter` and `subprocess`.

**AI assistance.** I used Claude and Gemini as AI assistants to help clarify the task requirements, search for information, and explain the core concepts of the assignment. I conducted all checks independently on my local machine: the 36 public checks (tools/run.py --check), my custom test suite (tests/run_tests.py, 410 requests across two passes), and the performance benchmarks (tests/benchmark.py). All test results and benchmark metrics presented in this document reflect actual outputs from these local runs. I reviewed all parts of the implementation and analysis, and I take full responsibility for their correctness.