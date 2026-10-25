"""Independent semantic validators for Assignment 3.

Each check_* function returns a list of error strings (empty list = valid).
The reference code here (simple DSU, Kahn, iterative Tarjan) is deliberately
different from the solution (Kosaraju, DFS topological sort), so a bug in the
solution is unlikely to be repeated in the checker.
"""
from collections import deque, Counter
from itertools import combinations


# ------------------------------------------------------------ references
def _find(p, x):
    while p[x] != x:
        p[x] = p[p[x]]
        x = p[x]
    return x


def ref_component_count(n, edges):
    p = list(range(n))
    c = n
    for e in edges:
        a, b = _find(p, e[0]), _find(p, e[1])
        if a != b:
            p[a] = b
            c -= 1
    return c


def ref_mst_cost(n, edges):
    p = list(range(n))
    cost = 0
    for u, v, w in sorted(edges, key=lambda e: e[2]):
        a, b = _find(p, u), _find(p, v)
        if a != b:
            p[a] = b
            cost += w
    return cost


def brute_mst_cost(n, edges):
    """Exhaustive optimum for tiny graphs: best acyclic subset of size n-c."""
    c = ref_component_count(n, edges)
    need = n - c
    best = None
    for subset in combinations(range(len(edges)), need):
        p = list(range(n))
        ok = True
        for i in subset:
            a, b = _find(p, edges[i][0]), _find(p, edges[i][1])
            if a == b:
                ok = False
                break
            p[a] = b
        if ok:
            s = sum(edges[i][2] for i in subset)
            if best is None or s < best:
                best = s
    return best


def ref_kahn(n, edges):
    """Return a topological order, or None when a directed cycle exists."""
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for e in edges:
        adj[e[0]].append(e[1])
        indeg[e[1]] += 1
    q = deque(i for i in range(n) if indeg[i] == 0)
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return order if len(order) == n else None


def ref_tarjan(n, edges):
    """Iterative Tarjan SCC labels."""
    adj = [[] for _ in range(n)]
    for e in edges:
        adj[e[0]].append(e[1])
    index = [-1] * n
    low = [0] * n
    on = [False] * n
    comp = [-1] * n
    st = []
    idx = 0
    c = 0
    for s in range(n):
        if index[s] != -1:
            continue
        work = [(s, 0)]
        index[s] = low[s] = idx
        idx += 1
        st.append(s)
        on[s] = True
        while work:
            u, i = work.pop()
            if i < len(adj[u]):
                work.append((u, i + 1))
                v = adj[u][i]
                if index[v] == -1:
                    index[v] = low[v] = idx
                    idx += 1
                    st.append(v)
                    on[v] = True
                    work.append((v, 0))
                elif on[v]:
                    low[u] = min(low[u], index[v])
            else:
                if low[u] == index[u]:
                    while True:
                        w = st.pop()
                        on[w] = False
                        comp[w] = c
                        if w == u:
                            break
                    c += 1
                if work:
                    p = work[-1][0]
                    low[p] = min(low[p], low[u])
    return comp


def ref_dag_distances(n, edges, source):
    order = ref_kahn(n, edges)
    if order is None:
        return None
    out = [[] for _ in range(n)]
    for e in edges:
        out[e[0]].append((e[1], e[2]))
    dist = [None] * n
    dist[source] = 0
    for u in order:
        if dist[u] is None:
            continue
        for v, w in out[u]:
            if dist[v] is None or dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return dist


# --------------------------------------------------------------- checkers
def check_dsu(req, res):
    n, ops = req["n"], req["operations"]
    if "states" not in res:
        return ["missing 'states'"]
    states = res["states"]
    if len(states) != len(ops):
        return ["expected %d states, got %d" % (len(ops), len(states))]
    p = list(range(n))
    size = [1] * n
    comps = n
    largest = 1 if n > 0 else 0
    for k, (u, v) in enumerate(ops):
        a, b = _find(p, u), _find(p, v)
        if a != b:
            p[a] = b
            size[b] += size[a]
            comps -= 1
            largest = max(largest, size[b])
        if list(states[k]) != [comps, largest]:
            return ["state %d: expected %s, got %s" % (k, [comps, largest], states[k])]
    return []


def check_forest(req, res):
    n, edges = req["n"], req["edges"]
    for key in ("cost", "edge_ids", "components"):
        if key not in res:
            return ["missing '%s'" % key]
    ids, cost, comps = res["edge_ids"], res["cost"], res["components"]
    errs = []
    if len(set(ids)) != len(ids):
        errs.append("repeated edge id")
    if any((not isinstance(i, int)) or i < 0 or i >= len(edges) for i in ids):
        return errs + ["edge id out of range"]
    p = list(range(n))
    for i in ids:
        u, v, _ = edges[i]
        if u == v:
            errs.append("self-loop %d selected" % i)
            continue
        a, b = _find(p, u), _find(p, v)
        if a == b:
            errs.append("selected edges contain a cycle (edge %d)" % i)
        else:
            p[a] = b
    c = ref_component_count(n, edges)
    if comps != c:
        errs.append("components: expected %d, got %s" % (c, comps))
    if len(ids) != n - c:
        errs.append("forest must have n-c=%d edges, got %d" % (n - c, len(ids)))
    if sum(edges[i][2] for i in ids) != cost:
        errs.append("cost does not equal the sum of selected weights")
    opt = ref_mst_cost(n, edges)
    if cost != opt:
        errs.append("cost %s is not optimal (optimum %s)" % (cost, opt))
    return errs


def check_scc(req, res):
    n, edges = req["n"], req["edges"]
    if "component" not in res or "condensation" not in res:
        return ["missing 'component' or 'condensation'"]
    comp, cond = res["component"], res["condensation"]
    if len(comp) != n:
        return ["component must have length n"]
    if any((not isinstance(x, int)) or x < 0 for x in comp):
        return ["labels must be nonnegative integers"]
    ref = ref_tarjan(n, edges)
    m1, m2 = {}, {}
    for a, b in zip(comp, ref):
        if m1.setdefault(a, b) != b or m2.setdefault(b, a) != a:
            return ["partition into SCCs is wrong"]
    expected = {(comp[u], comp[v]) for u, v in edges if comp[u] != comp[v]}
    got = [tuple(x) for x in cond]
    errs = []
    if len(got) != len(set(got)):
        errs.append("duplicate condensation pair")
    if set(got) != expected:
        errs.append("condensation pairs differ from the expected set")
    return errs


def check_topo(req, res):
    n, edges = req["n"], req["edges"]
    if "acyclic" not in res or "order" not in res:
        return ["missing 'acyclic' or 'order'"]
    cyc = ref_kahn(n, edges) is None
    if cyc:
        if res["acyclic"] is not False or res["order"] != []:
            return ["graph has a cycle: expected acyclic=false, order=[]"]
        return []
    if res["acyclic"] is not True:
        return ["graph is acyclic: expected acyclic=true"]
    order = res["order"]
    if sorted(order) != list(range(n)):
        return ["order must contain every vertex exactly once"]
    pos = [0] * n
    for i, v in enumerate(order):
        pos[v] = i
    for u, v in edges:
        if pos[u] >= pos[v]:
            return ["edge %d->%d goes backwards" % (u, v)]
    return []


def check_dag(req, res):
    n, edges, s = req["n"], req["edges"], req["source"]
    for key in ("acyclic", "distance", "parent_edge"):
        if key not in res:
            return ["missing '%s'" % key]
    ref = ref_dag_distances(n, edges, s)
    if ref is None:
        if res["acyclic"] is not False or res["distance"] != [] or res["parent_edge"] != []:
            return ["cyclic graph: expected false and two empty arrays"]
        return []
    if res["acyclic"] is not True:
        return ["graph is acyclic: expected acyclic=true"]
    dist, par = res["distance"], res["parent_edge"]
    if len(dist) != n or len(par) != n:
        return ["arrays must have length n"]
    if dist != ref:
        return ["distances differ from the reference"]
    if par[s] != -1:
        return ["source parent_edge must be -1"]
    for v in range(n):
        if v == s:
            continue
        if dist[v] is None:
            if par[v] != -1:
                return ["unreachable vertex %d must have parent_edge -1" % v]
            continue
        e = par[v]
        if not (0 <= e < len(edges)) or edges[e][1] != v:
            return ["parent edge of %d does not end at %d" % (v, v)]
        u, _, w = edges[e]
        if dist[u] is None or dist[u] + w != dist[v]:
            return ["parent edge of %d is not tight" % v]
    # following parent edges must reach the source; memoised so the whole
    # check is O(n) even for a chain of 100000 vertices
    reaches = [False] * n
    reaches[s] = True
    for v in range(n):
        if dist[v] is None or reaches[v]:
            continue
        path, x = [], v
        while not reaches[x]:
            path.append(x)
            if len(path) > n:
                return ["parent walk from %d does not reach the source" % v]
            x = edges[par[x]][0]
        for y in path:
            reaches[y] = True
    return []


def check_route(route, source, target, edges, parent_edge, dist):
    """Validate a helper result: direction, endpoints and total weight."""
    if dist[target] is None:
        return [] if route == [] else ["unreachable target must give []"]
    if not route or route[0] != source or route[-1] != target:
        return ["route must run from source to target"]
    total = 0
    for a, b in zip(route, route[1:]):
        e = parent_edge[b]
        if e < 0 or edges[e][0] != a or edges[e][1] != b:
            return ["step %d->%d does not use the selected parent edge" % (a, b)]
        total += edges[e][2]
    if total != dist[target]:
        return ["route weight %d != distance %s" % (total, dist[target])]
    return []


CHECKERS = {
    "dsu": check_dsu, "kruskal": check_forest, "prim": check_forest,
    "scc": check_scc, "topo": check_topo, "dag": check_dag,
}