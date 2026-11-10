from datetime import date
def intersection(windows):
    if not windows: return None
    pairs=[(date.fromisoformat(a),date.fromisoformat(b)) for a,b in windows]
    if any(a>b for a,b in pairs): raise ValueError('日期区间倒置')
    lo=max(a for a,b in pairs);hi=min(b for a,b in pairs)
    return [lo.isoformat(),hi.isoformat()] if lo<=hi else None
def reachable(edges,start,target):
    seen=set();todo=[start]
    while todo:
        n=todo.pop()
        if n==target:return True
        if n in seen:continue
        seen.add(n);todo.extend(b for a,b in edges if a==n)
    return False
def scope_intersection(scopes):
    if not scopes:return []
    return sorted(set(scopes[0]).intersection(*map(set,scopes[1:])))
TOOLS={'intersection':intersection,'reachable':reachable,'scope_intersection':scope_intersection}
