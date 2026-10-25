"""Assignment 3: graph algorithms (pure Python, no recursion, no printing)."""
import heapq


# ---------------------------------------------------------------- DSU
class _DSU:
    __slots__ = ("parent", "size", "components", "largest")

    def __init__(self, n):
        self.parent = list(range(n))
        self.size = [1] * n
        self.components = n
        self.largest = 1 if n > 0 else 0

    def find(self, x):
        parent = self.parent
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:          # path compression
            parent[x], x = root, parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:  # union by size
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        self.components -= 1
        if self.size[ra] > self.largest:
            self.largest = self.size[ra]
        return True


def _dsu(n, operations):
    d = _DSU(n)
    states = []
    for u, v in operations:
        d.union(u, v)
        states.append([d.components, d.largest])
    return {"states": states}


# ------------------------------------------------------------ Kruskal
def _kruskal(n, edges):
    d = _DSU(n)
    order = sorted(range(len(edges)), key=lambda i: edges[i][2])
    cost = 0
    chosen = []
    for i in order:
        u, v, w = edges[i]
        if d.union(u, v):                  # loops are rejected (same root)
            cost += w
            chosen.append(i)
    return {"cost": cost, "edge_ids": chosen, "components": d.components}


# --------------------------------------------------------------- Prim
def _prim(n, edges):
    adj = [[] for _ in range(n)]
    for i, (u, v, w) in enumerate(edges):
        if u == v:
            continue                       # self-loop never in a forest
        adj[u].append((w, i, v))
        adj[v].append((w, i, u))
    visited = [False] * n
    cost = 0
    chosen = []
    components = 0
    for s in range(n):                     # restart in every component
        if visited[s]:
            continue
        components += 1
        visited[s] = True
        heap = list(adj[s])
        heapq.heapify(heap)
        while heap:
            w, i, v = heapq.heappop(heap)
            if visited[v]:                 # lazy deletion of stale entries
                continue
            visited[v] = True
            cost += w
            chosen.append(i)
            for item in adj[v]:
                if not visited[item[2]]:
                    heapq.heappush(heap, item)
    return {"cost": cost, "edge_ids": chosen, "components": components}


# ---------------------------------------------------------------- SCC
def _scc(n, edges):
    adj = [[] for _ in range(n)]
    radj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        radj[v].append(u)

    # pass 1: finish order on the original graph (iterative DFS)
    seen = [False] * n
    finish = []
    ptr = [0] * n
    for s in range(n):
        if seen[s]:
            continue
        seen[s] = True
        stack = [s]
        while stack:
            u = stack[-1]
            if ptr[u] < len(adj[u]):
                v = adj[u][ptr[u]]
                ptr[u] += 1
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
            else:
                stack.pop()
                finish.append(u)

    # pass 2: transpose graph, decreasing finish time
    comp = [-1] * n
    c = 0
    for s in reversed(finish):
        if comp[s] != -1:
            continue
        comp[s] = c
        stack = [s]
        while stack:
            u = stack.pop()
            for v in radj[u]:
                if comp[v] == -1:
                    comp[v] = c
                    stack.append(v)
        c += 1

    pairs = set()
    for u, v in edges:
        if comp[u] != comp[v]:
            pairs.add((comp[u], comp[v]))
    return {"component": comp, "condensation": [list(p) for p in pairs]}


# --------------------------------------------------------------- topo
def _toposort(n, adj):
    """Three-state iterative DFS. Returns order or None if a cycle exists."""
    WHITE, GRAY, BLACK = 0, 1, 2
    state = [WHITE] * n
    ptr = [0] * n
    finish = []
    for s in range(n):
        if state[s] != WHITE:
            continue
        state[s] = GRAY
        stack = [s]
        while stack:
            u = stack[-1]
            nb = adj[u]
            if ptr[u] < len(nb):
                v = nb[ptr[u]]
                ptr[u] += 1
                if state[v] == GRAY:       # back edge -> cycle (also self-loop)
                    return None
                if state[v] == WHITE:
                    state[v] = GRAY
                    stack.append(v)
            else:
                state[u] = BLACK
                stack.pop()
                finish.append(u)
    finish.reverse()
    return finish


def _topo(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
    order = _toposort(n, adj)
    if order is None:
        return {"acyclic": False, "order": []}
    return {"acyclic": True, "order": order}


# ---------------------------------------------------------------- DAG
def _dag(n, edges, source):
    adj = [[] for _ in range(n)]
    for i, (u, v, w) in enumerate(edges):
        adj[u].append(v)
    order = _toposort(n, adj)              # whole-graph cycle check
    if order is None:
        return {"acyclic": False, "distance": [], "parent_edge": []}

    out = [[] for _ in range(n)]
    for i, (u, v, w) in enumerate(edges):
        out[u].append((v, w, i))
    dist = [None] * n
    parent = [-1] * n
    dist[source] = 0
    for u in order:
        du = dist[u]
        if du is None:                     # never relax from unreachable
            continue
        for v, w, i in out[u]:
            nd = du + w
            if dist[v] is None or nd < dist[v]:
                dist[v] = nd
                parent[v] = i
    return {"acyclic": True, "distance": dist, "parent_edge": parent}


def reconstruct_route(source, target, parent_edge, edges):
    """Vertex sequence source -> target using parent edge IDs.

    Source -> [source]. Unreachable target -> [] (empty list = no route).
    """
    if target == source:
        return [source]
    if parent_edge[target] == -1:
        return []
    route = [target]
    v = target
    while v != source:
        e = parent_edge[v]
        if e == -1:
            return []
        v = edges[e][0]                    # edge goes u -> v, step back to u
        route.append(v)
    route.reverse()
    return route


# ------------------------------------------------ public entry points
# main.py calls these with the whole request dict.
def dsu(request):
    """DSU with path compression and union by size; return states."""
    return _dsu(request["n"], request["operations"])


def kruskal(request):
    """Separate Kruskal implementation; return cost, edge_ids, components."""
    return _kruskal(request["n"], request["edges"])


def prim(request):
    """Separate Prim implementation; restart for every unvisited component."""
    return _prim(request["n"], request["edges"])


def scc(request):
    """Kosaraju with two DFS passes; return component and condensation."""
    return _scc(request["n"], request["edges"])


def topo(request):
    """Three-state DFS and reverse finish order; return acyclic and order."""
    return _topo(request["n"], request["edges"])


def dag(request):
    """Whole-graph cycle check and DAG relaxation."""
    return _dag(request["n"], request["edges"], request["source"])