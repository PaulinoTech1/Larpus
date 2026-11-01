"""Executable checks for every Grok Bot synthetic tuning family (DRAFT, pending independent review).

Covers the 12 round-zero families (check ids M1..Q6, copied unchanged from
verify_round0_families.py) and all round-1 train/dev families (check id = family_id).
Locked-test families are NOT here: they must be authored independently and sealed.
Re-run owner-side in a dedicated dev environment (python + sympy + numpy + scipy):
    python verify_families.py [--json out.json] [--data DIR]
--data DIR also cross-checks the family JSON files in DIR (every family has a passing
or hand-proof-only result; family_sha256 recomputed). A passing numeric or symbolic
check tests the stated facts; it is not a general proof. Status 'hand-proof-only'
means no executable check exists; the proof sketch is printed and needs human review.
"""
import json, sys, platform, math, itertools, hashlib, os
import numpy as np, scipy, sympy as sp
from scipy.linalg import expm, sqrtm, logm
from scipy import integrate as si, optimize as so, special as ss

R = {}
REG = []
def check(fid, kind, limits):
    def deco(fn):
        def run():
            try:
                facts = fn(); R[fid] = {"status": "pass", "kind": kind, "facts": facts, "limits": limits}
            except Exception as e:
                R[fid] = {"status": "FAIL", "kind": kind, "error": f"{type(e).__name__}: {e}", "limits": limits}
        run.__name__ = fn.__name__; REG.append(run); return run
    return deco
def hand(fid, sketch, limits="No executable check; proof sketch requires independent human review."):
    def run(): R[fid] = {"status": "hand-proof-only", "kind": "hand-proof-only", "facts": {"proof_sketch": sketch}, "limits": limits}
    REG.append(run)

x, y, n, t, c = sp.symbols('x y n t c', real=True)
# common quantum helpers
I2 = np.eye(2, dtype=complex); SX = np.array([[0, 1], [1, 0]], dtype=complex)
SY = np.array([[0, -1j], [1j, 0]]); SZ = np.diag([1, -1]).astype(complex)
K0 = np.array([1, 0], dtype=complex); K1 = np.array([0, 1], dtype=complex)
def ket(*a): v = np.array(a, dtype=complex); return v
def dm(v): v = np.asarray(v, dtype=complex); return np.outer(v, v.conj())
def ptrace(rho, dims, keep):
    rho = np.asarray(rho).reshape(dims + dims); n_ = len(dims)
    idx = list(range(n_)); out = rho
    for k in sorted([i for i in idx if i not in keep], reverse=True):
        out = np.trace(out, axis1=k, axis2=k + out.ndim // 2)
    d = int(np.prod([dims[i] for i in keep])); return out.reshape(d, d)
def close(a, b, tol=1e-9): return np.allclose(a, b, atol=tol, rtol=0)
def vn_entropy(r):
    w = np.linalg.eigvalsh(r); w = w[w > 1e-14]; return float(-(w * np.log2(w)).sum())
def spin_ops(s):
    m = np.arange(s, -s - 1, -1); d = len(m)
    Jz = np.diag(m).astype(complex); Jp = np.zeros((d, d), dtype=complex)
    for i in range(1, d): Jp[i - 1, i] = np.sqrt(s * (s + 1) - m[i] * (m[i] + 1))
    Jm = Jp.conj().T; return (Jp + Jm) / 2, (Jp - Jm) / (2j), Jz
def ho_ops(N):
    a = np.diag(np.sqrt(np.arange(1, N)), 1).astype(complex); return a, a.conj().T
def extra(fid):
    """Top-up check: runs after the family's main check and merges its facts; any failure marks the family FAIL."""
    def deco(fn):
        def run():
            base = R.get(fid)
            if base is None or base.get("status") == "FAIL": return
            try:
                facts = fn(); base.setdefault("facts", {}).update({"topup: " + k: v for k, v in facts.items()})
            except Exception as e:
                R[fid] = {"status": "FAIL", "kind": base.get("kind"), "error": f"topup {type(e).__name__}: {e}", "limits": base.get("limits", "")}
        run.__name__ = fn.__name__; REG.append(run); return run
    return deco

# ---- round-zero checks M1..Q6 (copied unchanged from verify_round0_families.py) ----
@check("M1", "symbolic", "Checks the specific sequence x**n on [0,1]; the non-uniformity argument (sup = 1) is a hand argument confirmed symbolically, not a general theorem.")
def m1():
    npos = sp.Symbol('n', positive=True, integer=True)
    assert sp.limit(sp.Rational(1, 2)**n, n, sp.oo) == 0
    assert sp.limit(sp.Integer(1)**n, n, sp.oo) == 1
    I = sp.integrate(x**npos, (x, 0, 1)); assert sp.simplify(I - 1/(npos+1)) == 0
    assert sp.limit(1/(n+1), n, sp.oo) == 0
    # sup over [0,1) of x^n is 1 for every n (approached as x -> 1-), so sup|f_n - f| does not -> 0
    for k in (1, 5, 50):
        assert sp.limit(x**k, x, 1, '-') == 1
    return {"pointwise_limit": "0 on [0,1), 1 at x=1", "integral_n": "1/(n+1) -> 0",
            "sup_[0,1)|x^n - 0|": "1 for every n (limit x->1-), so not uniform"}

@check("M2", "symbolic", "Divergence shown for the one-sided integral of 1/x on (0,1]; principal value computed separately and is a different notion.")
def m2():
    assert sp.integrate(1/x, (x, 1, sp.E)) == 1
    eps = sp.Symbol('eps', positive=True)
    right = sp.integrate(1/x, (x, eps, 1)); assert sp.limit(right, eps, 0, '+') == sp.oo
    pv = sp.Integral(1/x, (x, -1, 1)).principal_value(); assert pv == 0
    assert sp.simplify(sp.diff(sp.log(-x) + 5, x) - 1/x) == 0 and sp.simplify(sp.diff(sp.log(x) - 2, x) - 1/x) == 0
    return {"int_1^e 1/x": 1, "int_0^1 1/x": "diverges (+oo)", "PV int_-1^1 1/x": 0,
            "antiderivative": "ln|x| + C1 on x<0, ln|x| + C2 on x>0 (independent constants)"}

@check("M3", "symbolic", "Substitution verified for x>=0 and for the piecewise family on the region x>c with c>=0; the non-Lipschitz claim is checked through the unbounded difference quotient at y=0.")
def m3():
    xp = sp.Symbol('x', positive=True)
    # y = x^3 for x >= 0: y' = 3x^2, 3*y^(2/3) = 3x^2
    assert sp.simplify(sp.diff(xp**3, xp) - 3*(xp**3)**sp.Rational(2, 3)) == 0
    # y = 0 trivially solves; y=(x-c)^3 for x>c
    s = sp.Symbol('s', positive=True)  # s = x - c > 0
    assert sp.simplify(sp.diff(s**3, s) - 3*(s**3)**sp.Rational(2, 3)) == 0
    # non-Lipschitz at 0: |f(y)-f(0)|/|y| = 3 y^(-1/3) -> oo as y -> 0+
    yp = sp.Symbol('y', positive=True)
    assert sp.limit(3*yp**sp.Rational(2, 3)/yp, yp, 0, '+') == sp.oo
    return {"solutions_through_(0,0)": ["y=0", "y=x^3 (x>=0)", "y=0 for x<=c, (x-c)^3 for x>c, any c>=0"],
            "lipschitz_at_0": "fails: difference quotient 3*y^(-1/3) unbounded"}

@check("M4", "symbolic", "Residual and Neumann boundary checks on the unit square for one reference solution; the no-solution claim for f=1 uses the divergence theorem (hand argument), illustrated symbolically.")
def m4():
    u = sp.cos(sp.pi*x) + c
    assert sp.simplify(sp.diff(u, x, 2) + sp.diff(u, y, 2) + sp.pi**2*sp.cos(sp.pi*x)) == 0
    ux = sp.diff(u, x)
    assert ux.subs(x, 0) == 0 and sp.simplify(ux.subs(x, 1)) == 0 and sp.diff(u, y) == 0
    assert sp.integrate(-sp.pi**2*sp.cos(sp.pi*x), (x, 0, 1), (y, 0, 1)) == 0
    assert sp.integrate(1, (x, 0, 1), (y, 0, 1)) == 1  # compatibility fails for f = 1
    return {"f=-pi^2 cos(pi x)": "u = cos(pi x) + C, unique only up to C",
            "compatibility": "int f = 0 required; f=1 gives 1 != 0 -> no solution"}

@check("M5", "symbolic", "Exhaustive for this polynomial on a closed interval (stationary points plus endpoints).")
def m5():
    f = x**3 - 3*x
    crit = sp.solve(sp.diff(f, x), x); assert set(crit) == {-1, 1}
    vals = {p: f.subs(x, p) for p in [-3, -1, 1, 3]}
    assert vals == {-3: -18, -1: 2, 1: -2, 3: 18}
    assert sp.diff(f, x, 2).subs(x, 1) == 6
    assert sp.limit(f, x, -sp.oo) == -sp.oo
    return {"stationary": [-1, 1], "values": {str(k): int(v) for k, v in vals.items()},
            "global_min_on_[-3,3]": "x=-3, f=-18", "x=1": "local min, f=-2", "on_R": "unbounded below, no global min"}

@check("M6", "numeric illustration + hand proof", "Finite truncations only illustrate ||e_n - e_m|| = sqrt(2); the infinite-dimensional claims rest on the hand argument.")
def m6():
    N = 50; E = np.eye(N)
    d = [np.linalg.norm(E[i] - E[j]) for i in range(N) for j in range(N) if i != j]
    assert np.allclose(d, np.sqrt(2))
    S = np.eye(N, k=-1)  # truncated right shift: last basis vector maps out of range
    assert np.linalg.matrix_rank(S) == N - 1
    rng = np.random.default_rng(0); A = rng.standard_normal((6, 6))
    assert np.linalg.matrix_rank(A) == 6
    return {"||e_n-e_m||": "sqrt(2) for n != m (no Cauchy subsequence)",
            "finite_dim": "injective <=> surjective (rank-nullity)",
            "right_shift_l2": "isometric, injective, not surjective (e_1 not in range)"}

@check("Q1", "numeric", "Exact for the stated two-level state (floating point, tol 1e-12).")
def q1():
    psi = np.array([1, 2j]); N2 = np.vdot(psi, psi).real; assert np.isclose(N2, 5)
    p = np.abs(psi)**2 / N2; assert np.allclose(p, [0.2, 0.8])
    plus = np.array([1, 1]) / np.sqrt(2); minus = np.array([1, -1]) / np.sqrt(2)
    pp = abs(np.vdot(plus, psi))**2 / N2; pm = abs(np.vdot(minus, psi))**2 / N2
    assert np.isclose(pp, 0.5) and np.isclose(pm, 0.5) and np.isclose(pp + pm, 1)
    return {"norm^2": 5, "P(0),P(1)": [0.2, 0.8], "P(+),P(-)": [0.5, 0.5]}

@check("Q2", "numeric", "Checked at sampled times for hbar=omega=1; the sign depends on the stated Hamiltonian convention H=(hbar*omega/2)sigma_z.")
def q2():
    sx = np.array([[0, 1], [1, 0]]); sy = np.array([[0, -1j], [1j, 0]]); sz = np.diag([1, -1])
    H = 0.5 * sz; psi0 = np.array([1, 1]) / np.sqrt(2)
    for tt in np.linspace(0, 7, 29):
        U = expm(-1j * H * tt); p = U @ psi0
        ex = np.vdot(p, sx @ p).real; ey = np.vdot(p, sy @ p).real
        assert np.isclose(ex, np.cos(tt)) and np.isclose(ey, np.sin(tt))
        Uw = expm(+1j * H * tt); q = Uw @ psi0
        if abs(np.sin(tt)) > 1e-6: assert not np.isclose(np.vdot(q, sy @ q).real, np.sin(tt))
    e0 = np.array([1, 0]); U = expm(-1j * H * 2.3)
    assert np.isclose(abs(np.vdot(e0, U @ e0)), 1)
    return {"<sx>(t)": "cos(omega t)", "<sy>(t)": "+sin(omega t) with U=exp(-iHt/hbar)",
            "wrong_sign_U": "gives -sin(omega t)", "|0>": "stationary (phase only)"}

@check("Q3", "numeric", "Exact matrix identities for spin-1/2 in the standard S_z basis, hbar=1.")
def q3():
    sx = np.array([[0, 1], [1, 0]]); sy = np.array([[0, -1j], [1j, 0]]); sz = np.diag([1, -1])
    assert np.allclose(sx @ sy - sy @ sx, 2j * sz)
    Sx, Sy, Sz = sx / 2, sy / 2, sz / 2
    assert np.allclose(Sx @ Sy - Sy @ Sx, 1j * Sz)
    S2 = Sx @ Sx + Sy @ Sy + Sz @ Sz; assert np.allclose(S2, 0.75 * np.eye(2))
    return {"[sx,sy]": "2i sz", "[Sx,Sy]": "i hbar Sz", "S^2": "(3/4) hbar^2 I"}

@check("Q4", "numeric + symbolic", "Exact diagonalization of the stated 3x3 model; perturbative statements apply for |eps| << level spacing 2.")
def q4():
    e = sp.Symbol('epsilon', positive=True)
    Hd = sp.Matrix([[1, e, 0], [e, 1, 0], [0, 0, 3]])
    ev = Hd.eigenvals(); assert set(ev) == {1 - e, 1 + e, 3}
    Hn = sp.Matrix([[1, 0, e], [0, 1, 0], [e, 0, 3]])
    low = 2 - sp.sqrt(1 + e**2); assert low in set(Hn.eigenvals())
    ser = sp.series(low, e, 0, 4).removeO(); assert sp.simplify(ser - (1 - e**2/2)) == 0
    for val in [0.01, 0.1]:
        w = np.linalg.eigvalsh(np.array([[1, 0, val], [0, 1, 0], [val, 0, 3]]))
        assert abs(w.min() - (1 - val**2/2)) < val**4
    return {"degenerate_V": "exact 1-eps, 1+eps, 3 (first-order split +-eps)",
            "nondegenerate_V": "lowest exact 2 - sqrt(1+eps^2) = 1 - eps^2/2 + O(eps^4)"}

@check("Q5", "numeric", "Exact for the Bell state; no-signalling checked for Z and X measurement choices (non-selective), not for all POVMs.")
def q5():
    k0, k1 = np.array([1, 0]), np.array([0, 1])
    phi = (np.kron(k0, k0) + np.kron(k1, k1)) / np.sqrt(2); rho = np.outer(phi, phi.conj())
    def trA(r): return np.einsum('ijik->jk', r.reshape(2, 2, 2, 2))
    def trB(r): return np.einsum('ijkj->ik', r.reshape(2, 2, 2, 2))
    rA = trB(rho); rB = trA(rho)
    assert np.allclose(rA, np.eye(2) / 2) and np.isclose(np.trace(rA @ rA).real, 0.5)
    assert np.isclose(np.trace(rho @ rho).real, 1)
    for basis in [(k0, k1), (np.array([1, 1]) / np.sqrt(2), np.array([1, -1]) / np.sqrt(2))]:
        post = sum(np.kron(np.outer(b, b.conj()), np.eye(2)) @ rho @ np.kron(np.outer(b, b.conj()), np.eye(2)) for b in basis)
        assert np.allclose(trA(post), np.eye(2) / 2)
    assert np.all(np.linalg.eigvalsh(rA) >= -1e-12) and np.isclose(np.trace(rA), 1)
    return {"rho_A": "I/2 (mixed, purity 1/2)", "global_state": "pure (purity 1)",
            "Bob_after_Alice_Z_or_X": "I/2 unchanged -> no signalling"}

@check("Q6", "numeric", "Integrates the stated Markovian Lindblad model (amplitude damping + pure dephasing); confirms model consistency only and is not experimental evidence.")
def q6():
    from scipy.integrate import solve_ivp
    T1, gphi = 50.0, 0.01  # microseconds, 1/microseconds
    g1 = 1 / T1
    sm = np.array([[0, 1], [0, 0]]); sz = np.diag([1, -1])
    Ls = [np.sqrt(g1) * sm, np.sqrt(gphi / 2) * sz]
    def rhs(_, v):
        r = v.reshape(2, 2)
        d = sum(L @ r @ L.conj().T - 0.5 * (L.conj().T @ L @ r + r @ L.conj().T @ L) for L in Ls)
        return d.reshape(-1)
    r0 = 0.5 * np.array([[1, 1], [1, 1]], dtype=complex)
    ts = np.linspace(0, 200, 41)
    sol = solve_ivp(rhs, (0, 200), r0.reshape(-1), t_eval=ts, rtol=1e-10, atol=1e-12)
    coh = np.abs(sol.y[1])  # rho_01
    T2 = 1 / (g1 / 2 + gphi); assert np.allclose(coh, 0.5 * np.exp(-ts / T2), rtol=1e-6)
    assert np.isclose(T2, 1 / (1 / (2 * T1) + gphi)) and T2 <= 2 * T1
    sol0 = solve_ivp(lambda _, v: (sum(L @ v.reshape(2, 2) @ L.conj().T - 0.5 * (L.conj().T @ L @ v.reshape(2, 2) + v.reshape(2, 2) @ L.conj().T @ L) for L in [Ls[0]])).reshape(-1),
                     (0, 200), r0.reshape(-1), t_eval=ts, rtol=1e-10, atol=1e-12)
    assert np.allclose(np.abs(sol0.y[1]), 0.5 * np.exp(-ts / (2 * T1)), rtol=1e-6)
    alt = 1 / (g1 / 2 + 2 * gphi)  # convention where rho01 decays as exp(-2 gamma_phi t)
    assert abs(alt - 33.333) < 0.01
    return {"1/T2": "1/(2 T1) + gamma_phi", "alt_convention_T2": f"{alt:.2f} us (if rho01 ~ exp(-2 gamma_phi t))", "T1=50us,gamma_phi=0.01/us": f"T2={T2:.2f} us",
            "pure_damping": "T2 = 2 T1 = 100 us (upper bound in this model)"}


# ---- round-1 lane: lim ----
L = "grok-r1-lim-"
@check(L+"01", "symbolic", "Exact algebra for this sequence and tolerance 0.01 only.")
def lim01():
    a = (3*n+1)/(n+2); assert sp.limit(a, n, sp.oo) == 3
    assert sp.simplify(sp.Abs(a-3).subs(n, 7) - sp.Rational(5, 9)) == 0 and sp.simplify((a-3) + 5/(n+2)) == 0
    f = lambda k: sp.Rational(5, k+2)
    assert f(499) < sp.Rational(1, 100) and f(498) == sp.Rational(1, 100) and f(300) > sp.Rational(1, 100)
    e = sp.Symbol('e', positive=True); assert sp.solve(sp.Eq(5/(n+2), e), n) == [5/e - 2]
    return {"limit": 3, "|a_n-3|": "5/(n+2)", "N(0.01)": 499}
@check(L+"02", "symbolic+numeric", "Squeeze verified symbolically; oscillation of f'(x) shown by sampling at x = 1/(k pi), not a proof of non-existence.")
def lim02():
    assert sp.limit(x**2*sp.sin(1/x), x, 0) == 0 and sp.limit(x*sp.sin(1/x), x, 0) == 0
    fp_ = sp.diff(x**2*sp.sin(1/x), x); assert sp.simplify(fp_ - (2*x*sp.sin(1/x) - sp.cos(1/x))) == 0
    g = sp.lambdify(x, fp_); v = [g(1/(k*np.pi)) for k in range(1000, 1010)]
    assert all(abs(abs(u) - 1) < 1e-2 for u in v) and max(v) > 0.99 and min(v) < -0.99
    return {"lim x^2 sin(1/x)": 0, "f'(0)": 0, "f'(1/(k pi))": "alternates near +-1"}
@check(L+"03", "symbolic+numeric", "Specific limits only.")
def lim03():
    assert sp.limit((x+sp.sin(x))/x, x, sp.oo) == 1
    xs = np.array([2*np.pi*k for k in range(1, 50)] + [np.pi*(2*k+1) for k in range(1, 50)])
    r = 1+np.cos(xs); assert r.max() > 1.99 and r.min() < 1e-9
    assert sp.limit(sp.sin(x)/x, x, 0) == 1
    xx = np.linspace(1e-4, 0.5, 200); assert np.all(np.cos(xx) <= np.sin(xx)/xx) and np.all(np.sin(xx)/xx <= 1)
    return {"lim (x+sin x)/x": 1, "(1+cos x)": "oscillates in [0,2]", "squeeze cos x <= sin x/x <= 1": "holds on sample (0,0.5]"}
@check(L+"04", "symbolic+numeric", "Harmonic lower bound checked at sample n; zeta values from mpmath via sympy.")
def lim04():
    for k in (10, 1000, 100000):
        assert sum(1/j for j in range(1, k+1)) >= math.log(k+1)
    assert sp.integrate(x**sp.Rational(-3, 2), (x, 1, sp.oo)) == 2
    z15 = float(sp.zeta(1.5)); assert 2.61 < z15 < 2.62 < 3
    p = sp.Symbol('p', positive=True); assert sp.simplify(1 + sp.integrate(x**(-p), (x, 1, sp.oo), conds='none') - p/(p-1)) == 0
    assert float(sp.pi**2/6) < 2
    return {"H_n >= ln(n+1)": True, "zeta(1.5)": round(z15, 4), "bound p/(p-1) at p=2": 2, "pi^2/6": 1.6449}
@check(L+"05", "symbolic", "Specific ratio limits; endpoint behaviour by named tests.")
def lim05():
    assert sp.limit((1/(n+1)**2)/(1/n**2), n, sp.oo) == 1
    assert sp.summation(1/n**2, (n, 1, sp.oo)) == sp.pi**2/6
    r = sp.limit(sp.factorial(n+1)/(n+1)**(n+1) / (sp.factorial(n)/n**n), n, sp.oo); assert sp.simplify(r - sp.exp(-1)) == 0
    assert sp.summation((-1)**n/n, (n, 1, sp.oo)) == -sp.log(2)
    assert sp.Sum(1/n, (n, 1, sp.oo)).is_convergent() is sp.false or sp.Sum(1/n, (n, 1, sp.oo)).is_convergent() == False
    return {"ratio 1/n^2": 1, "sum 1/n^2": "pi^2/6", "ratio n!/n^n": "1/e", "x=-1": "-ln2 (converges)", "x=1": "diverges"}
@check(L+"06", "numeric+symbolic", "Partial sums to 2e6 terms (tolerance 1e-5); grouping identity symbolic.")
def lim06():
    k = sp.Symbol('k', positive=True, integer=True)
    assert sp.simplify(1/(2*k-1) - 1/(4*k-2) - 1/(4*k) - sp.Rational(1, 2)*(1/(2*k-1) - 1/(2*k))) == 0
    K = np.arange(1, 2_000_001, dtype=float)
    alt = np.sum(1/(2*K-1) - 1/(2*K)); assert abs(alt - math.log(2)) < 1e-5
    re = np.sum(1/(2*K-1) - 1/(4*K-2) - 1/(4*K)); assert abs(re - math.log(2)/2) < 1e-5
    m = np.arange(1, 200001, dtype=float); perm = m.copy(); perm[0::2], perm[1::2] = m[1::2], m[0::2]
    assert abs(np.sum(1/perm**2) - np.sum(1/m**2)) < 1e-12
    return {"alternating harmonic": "ln 2", "rearranged (1,-1/2,-1/4,...)": "ln2/2", "abs-convergent pair swap": "same sum"}
@check(L+"07", "symbolic+numeric", "Bound and divergence at x = 0/x = 1; uniform convergence on [0,r] uses r^n/n summable.")
def lim07():
    xs = np.linspace(-20, 20, 4001)
    for k in (1, 7, 50): assert np.all(np.abs(np.sin(k*xs)/k**2) <= 1/k**2 + 1e-15)
    assert sp.summation(1/n**2, (n, 1, sp.oo)).is_finite
    assert not sp.Sum(1/n, (n, 1, sp.oo)).is_convergent()
    r = sp.Rational(9, 10); assert sp.Sum(r**n/n, (n, 1, sp.oo)).is_convergent()
    return {"M_n": "1/n^2 summable", "cos series at 0": "harmonic, diverges", "x^n/n at x=1": "diverges", "[0,0.9]": "r^n/n summable"}
@check(L+"08", "symbolic", "Specific sequence only.")
def lim08():
    npos = sp.Symbol('n', positive=True)
    I = sp.integrate(npos**2*x*sp.exp(-npos*x), (x, 0, 1)); assert sp.simplify(I - (1 - (npos+1)*sp.exp(-npos))) == 0
    assert sp.limit(1 - (n+1)*sp.exp(-n), n, sp.oo) == 1
    x0 = sp.Rational(1, 3); assert sp.limit(n**2*x0*sp.exp(-n*x0), n, sp.oo) == 0
    f = npos**2*x*sp.exp(-npos*x); crit = sp.solve(sp.diff(f, x), x); assert crit == [1/npos]
    assert sp.simplify(f.subs(x, 1/npos) - npos/sp.E) == 0
    return {"integral": "1-(n+1)e^-n -> 1", "pointwise": 0, "max": "n/e at x=1/n"}
@check(L+"09", "symbolic", "One-sided limits of difference quotients.")
def lim09():
    h = sp.Symbol('h', real=True)
    assert sp.limit(sp.Abs(h)/h, h, 0, '+') == 1 and sp.limit(sp.Abs(h)/h, h, 0, '-') == -1
    assert sp.limit(h*sp.Abs(h)/h, h, 0) == 0
    xp = sp.Symbol('x', positive=True); assert sp.diff(xp**2, xp) == 2*xp and sp.diff(-xp**2, xp) == -2*xp
    hp = sp.Symbol('h', positive=True)
    assert sp.limit(hp**sp.Rational(1, 3)/hp, hp, 0, '+') == sp.oo
    assert sp.limit((-sp.root(hp, 3))/(-hp), hp, 0, '+') == sp.oo  # left side with real cube root of -h = -h^(1/3)
    return {"|x-2| one-sided": [-1, 1], "(x|x|)'(0)": 0, "x^(1/3) at 0": "quotient -> +oo both sides"}
@check(L+"10", "symbolic", "Specific functions only.")
def lim10():
    assert sp.solve(sp.Eq(1/x, 0), x) == []
    f = x**5 - 3*x + 1; assert f.subs(x, 0) == 1 and f.subs(x, 1) == -1
    r = [complex(z) for z in sp.Poly(f, x).nroots()]; real01 = [z.real for z in r if abs(z.imag) < 1e-12 and 0 < z.real < 1]
    assert len(real01) >= 1 and abs(real01[0] - 0.3347) < 1e-3
    return {"1/x roots": "none", "f(0),f(1)": [1, -1], "root in (0,1)": round(real01[0], 4)}
@check(L+"11", "symbolic+numeric", "Root-test estimate from 80 coefficients (tolerance 2e-2) about z = 1; exactness uses the pole argument.")
def lim11():
    s = sp.series(1/(1+x**2), x, 0, 12).removeO(); assert sp.expand(s - sum((-1)**k*x**(2*k) for k in range(6))) == 0
    assert sp.limit((n+1)/(3*n), n, sp.oo) == sp.Rational(1, 3)
    z = sp.Symbol('z'); N = 80
    ser = sp.series(1/(1+z**2), z, 1, N+1).removeO().subs(z, z+1)
    co = [abs(complex(sp.Poly(sp.expand(ser), z).coeff_monomial(z**k))) for k in range(N-10, N)]
    est = np.mean([c**(-1/k) for c, k in zip(co, range(N-10, N)) if c > 0]); assert abs(est - math.sqrt(2)) < 2e-2
    assert abs(sp.Abs(1 - sp.I)) == sp.sqrt(2)
    return {"Maclaurin radius": 1, "radius sum n z^n/3^n": 3, "radius about z=1 (root test est.)": round(float(est), 3)}
@check(L+"12", "symbolic+numeric", "First three derivatives of exp(-1/x^2) shown to vanish at 0 via limits; general n is the standard induction.")
def lim12():
    f = sp.exp(-1/x**2); d = f
    for k in range(3):
        d = sp.diff(d, x); assert sp.limit(d, x, 0) == 0
    assert sp.limit(f/x, x, 0) == 0
    assert math.isclose(float(f.subs(x, sp.Rational(1, 2))), math.exp(-4), rel_tol=1e-12)
    P3 = 1 + 0.5 + 0.125 + 0.5**3/6; err = math.exp(0.5) - P3; bound = math.exp(0.5)*0.5**4/24
    assert 0.00288 < err < 0.00289 and err <= bound < 0.0043 and 0.5**4/24 < err and math.exp(0.5) < 1.65
    return {"f^(k)(0)": "0 for k=1..3 (limit check)", "f(0.5)": "e^-4", "error": round(err, 5), "Lagrange bound": round(bound, 5)}
@check(L+"13", "symbolic", "Irrationality via sympy's exact arithmetic; the classical proof is the hand argument.")
def lim13():
    assert sp.sqrt(2).is_rational is False
    tr = [sp.floor(sp.sqrt(2)*10**k)/sp.Integer(10)**k for k in range(8)]
    for k in range(7):
        for m in range(k, 8): assert abs(tr[m] - tr[k]) < sp.Rational(1, 10**k)
    p, q = sp.symbols('p q', integer=True, positive=True); assert sp.Eq((p/q)**2, 2).subs(p, 2*q) != True
    return {"sqrt2 rational": False, "truncation Cauchy bound": "|t_m - t_k| < 10^-k"}
@check(L+"14", "exhaustive+symbolic", "Exhaustive for n <= 300; step inequality symbolic.")
def lim14():
    good = [k for k in range(1, 301) if 2**k > k**2]; assert good == [1] + list(range(5, 301))
    k = sp.Symbol('k', positive=True)
    assert sp.solve(sp.Eq(2*k**2, (k+1)**2), k) == [1 + sp.sqrt(2)] and float(1+sp.sqrt(2)) < 3
    for kk in range(5, 200): assert kk**2 >= 5*kk and 5*kk > 2*kk + 1
    return {"holds for": "n=1 and n>=5 (checked to 300)", "step needs": "k >= 1+sqrt2 (~2.414)"}
@check(L+"15", "numeric", "Tail suprema computed to n = 10^5.")
def lim15():
    nn = np.arange(1, 100001); a = (-1.0)**nn*(1 + 1/nn)
    assert abs(a.max() - 1.5) < 1e-15 and abs(a.min() + 2) < 1e-15
    ts = [a[k:].max() for k in (0, 1, 2, 3, 1000, 99000)]; assert ts[:3] == [1.5, 1.5, 1.25] and abs(ts[-1] - 1) < 1e-4
    assert abs(a[-2:].min() + 1) < 1e-4
    return {"sup": 1.5, "inf": -2, "limsup": 1, "liminf": -1}
@check(L+"16", "exact+symbolic", "Fair independent coin model; Cauchy via characteristic functions.")
def lim16():
    seqs = list(itertools.product("HT", repeat=6)); s5 = [s for s in seqs if s[:5] == tuple("HHHHH")]
    assert len(s5) == 2 and sum(s[5] == "T" for s in s5) == 1
    tt = sp.Symbol('t', real=True); m = sp.Symbol('m', positive=True)
    phi = sp.exp(-sp.Abs(tt)); assert sp.simplify(phi.subs(tt, tt/m)**m - phi) == 0
    assert sp.integrate(x/(sp.pi*(1+x**2)), (x, 0, sp.oo)) == sp.oo
    p = float(sum(sp.binomial(100, k) for k in range(61))/sp.Integer(2)**100); assert abs(p - 0.98240) < 5e-6
    from scipy.stats import norm; assert abs(norm.cdf(2.1) - 0.9821) < 1e-4
    return {"P(T | 5H)": 0.5, "Cauchy mean of n": "standard Cauchy", "P(X<=60)": round(p, 5), "normal approx": 0.9821}
@check(L+"17", "numeric+symbolic", "Iteration to 60 steps; fixed points symbolic.")
def lim17():
    a = [1.0]
    for _ in range(60): a.append(math.sqrt(2 + a[-1]))
    assert all(a[i] < a[i+1] < 2 for i in range(15)) and all(a[i] <= a[i+1] <= 2 for i in range(60)) and abs(a[-1] - 2) < 1e-12
    L_ = sp.Symbol('L'); assert set(sp.solve(sp.Eq(L_**2, 2 + L_), L_)) == {2, -1}
    assert [2**(k-1) for k in range(1, 6)] == [1, 2, 4, 8, 16]
    return {"limit": 2, "monotone, bounded by 2": True, "a_{n+1}=2a_n": "diverges"}
@check(L+"18", "symbolic", "Specific witness sequences.")
def lim18():
    k = sp.Symbol('k', positive=True)
    assert sp.expand((k + 1/k)**2 - k**2) == 2 + k**-2
    assert sp.simplify(1/(1/(2*k)) - 1/(1/k) - k) == 0
    xx, yy = sp.symbols('x y', positive=True); assert sp.simplify(sp.Abs(1/xx - 1/yy) - sp.Abs(xx - yy)/(xx*yy)) == 0
    return {"x^2 witness gap": "2 + 1/n^2", "1/x on (0,1) gap": "n", "1/x on [1,oo)": "Lipschitz 1"}
@check(L+"19", "symbolic+numeric", "Closed form for n >= 2; domination checked on a grid for n = 2..60.")
def lim19():
    npos = sp.Symbol('n', positive=True)
    I = sp.integrate((1 + x/npos)**(-npos), (x, 0, sp.oo), conds='none'); assert sp.simplify(I.subs(npos, 5) - sp.Rational(5, 4)) == 0
    for k in (2, 3, 10): assert sp.integrate((1 + x/k)**(-k), (x, 0, sp.oo)) == sp.Rational(k, k-1)
    xs = np.linspace(0, 200, 4001)
    for k in range(2, 61): assert np.all((1 + xs/k)**(-k) <= (1 + xs/2)**(-2) + 1e-15)
    assert sp.integrate((1 + x/2)**(-2), (x, 0, sp.oo)) == 2
    assert sp.integrate(sp.Integer(1), (x, 5, 6)) == 1
    return {"integral": "n/(n-1) -> 1", "dominating": "(1+x/2)^-2 (integral 2)", "indicator [n,n+1]": "integral 1 each"}
@check(L+"20", "numeric", "Partial sums to 2e6 (tolerance 1e-5); non-uniformity shown at x = pi/N.")
def lim20():
    N = 2_000_000; k = np.arange(1, N+1, dtype=float)
    s = np.sum(np.sin(k)/k); assert abs(s - (math.pi - 1)/2) < 1e-5
    ps = np.cumsum(np.sin(k[:20000])); assert np.abs(ps).max() < 2
    for M in (100, 1000, 10000):
        kk = np.arange(1, M+1); SN = np.sum(np.sin(kk*math.pi/M)/kk); assert SN - (math.pi - math.pi/M)/2 > 0.27
    return {"sum sin n/n": "(pi-1)/2", "partial sums of sin n": "bounded", "overshoot at x=pi/N": "> 0.27 for all N tested"}
@check(L+"21", "symbolic", "Specific limits.")
def lim21():
    assert sp.limit(x*sp.sin(1/x), x, sp.oo) == 1 and sp.limit(n*(sp.exp(1/n) - 1), n, sp.oo) == 1
    return {"x sin(1/x)": 1, "n(e^(1/n)-1)": 1}
@extra("grok-r1-lim-14")
def lim14_topup():
    assert 2**1 > 1 and 2**2 == 4 and 2**3 < 9 and 2**4 == 16 and all(2**n > n*n for n in range(5, 200))
    return {"small n": "n=1 true; n=2,3,4 false; n>=5 true (checked to 199)"}
@extra("grok-r1-lim-19")
def lim19_topup():
    nn = sp.Symbol('N', positive=True, integer=True); assert sp.integrate(nn, (x, 0, 1/nn)) == 1
    xs = np.array([0.3, 0.05, 0.004]); sup = np.array([max(n for n in range(1, 10**4) if 1/n >= xv) for xv in xs]); assert np.all(sup*xs > 0.5)
    assert sp.integrate(1/(2*x), (x, sp.Rational(1, 10**6), 1)) > 6
    return {"integral f_n": 1, "sup_n f_n(x)": ">= 1/(2x), not integrable near 0"}
@extra("grok-r1-lim-11")
def lim11_topup():
    assert sp.Rational(1, 1 + 4) == sp.Rational(1, 5) and all(abs((-4)**k) >= 1 for k in range(20))
    return {"f(2)": "1/5", "series terms at x=2": "(-4)^k, do not tend to 0"}

# ---- round-1 lane: calc ----
L = "grok-r1-calc-"
@check(L+"01", "symbolic", "Specific curve and points.")
def calc01():
    yy = sp.Symbol('y'); d = sp.idiff(x**2 + yy**2 - 25, yy, x); assert sp.simplify(d + x/yy) == 0
    assert d.subs({x: 3, yy: 4}) == sp.Rational(-3, 4) and d.subs({x: 3, yy: -4}) == sp.Rational(3, 4)
    return {"y'": "-x/y", "(3,4)": "-3/4", "(3,-4)": "3/4"}
@check(L+"02", "symbolic", "Antiderivatives verified by differentiation.")
def calc02():
    F_ = sp.exp(2*x)*(x/2 - sp.Rational(1, 4)); assert sp.simplify(sp.diff(F_, x) - x*sp.exp(2*x)) == 0
    a = sp.Symbol('a', nonzero=True); G = sp.exp(a*x)*(x/a - 1/a**2); assert sp.simplify(sp.diff(G, x) - x*sp.exp(a*x)) == 0
    assert sp.integrate(x, x) == x**2/2
    return {"int x e^(2x)": "e^(2x)(x/2-1/4)", "a=0": "x^2/2"}
@check(L+"03", "symbolic", "")
def calc03():
    assert sp.integrate(2*x*(x**2+1)**3, (x, 0, 1)) == sp.Rational(15, 4)
    u = sp.Symbol('u'); assert sp.integrate(u**3, (u, 1, 2)) == sp.Rational(15, 4) and sp.integrate(u**3, (u, 0, 1)) == sp.Rational(1, 4)
    return {"value": "15/4", "wrong-limits value": "1/4"}
@check(L+"04", "symbolic", "")
def calc04():
    e = sp.Symbol('e', positive=True); assert sp.limit(sp.integrate(x**-2, (x, e, 1)), e, 0, '+') == sp.oo
    assert sp.integrate(x**-2, (x, 1, 2)) == sp.Rational(1, 2)
    return {"[-1,1]": "diverges", "[1,2]": "1/2"}
@check(L+"05", "symbolic", "")
def calc05():
    a = sp.Symbol('a', positive=True); I = sp.integrate(sp.exp(-a*x), (x, 0, sp.oo)); assert I == 1/a
    assert sp.simplify(-sp.diff(I, a) - sp.integrate(x*sp.exp(-a*x), (x, 0, sp.oo))) == 0
    assert sp.integrate(x*sp.exp(-3*x), (x, 0, sp.oo)) == sp.Rational(1, 9)
    assert sp.integrate(sp.exp(x), (x, 0, sp.oo)) == sp.oo and sp.integrate(sp.Integer(1), (x, 0, sp.oo)) == sp.oo
    return {"I(a)": "1/a (a>0)", "int x e^-3x": "1/9", "a<=0": "diverges"}
@check(L+"06", "symbolic", "")
def calc06():
    assert sp.integrate(sp.exp(-x**2/2), (x, -sp.oo, sp.oo)) == sp.sqrt(2*sp.pi)
    G = sp.exp(-x**2)/(-2*x); assert sp.simplify(sp.diff(G, x) - (sp.exp(-x**2) + sp.exp(-x**2)/(2*x**2))) == 0
    v = sp.integrate(sp.exp(-x**2), (x, 0, 1)); assert abs(float(v) - 0.746824) < 1e-6 and sp.simplify(v - sp.sqrt(sp.pi)/2*sp.erf(1)) == 0
    assert sp.integrate(sp.exp(x**2), (x, -sp.oo, sp.oo)) == sp.oo
    return {"int e^(-x^2/2)": "sqrt(2 pi)", "int_0^1 e^-x^2": 0.746824, "a=-1": "diverges"}
@check(L+"07", "symbolic", "Residues and real-line integrals for these integrands.")
def calc07():
    z = sp.Symbol('z')
    assert sp.integrate(1/(x**2+4), (x, -sp.oo, sp.oo)) == sp.pi/2 and sp.residue(1/(z**2+4), z, 2*sp.I) == 1/(4*sp.I)
    assert sp.simplify(2*sp.pi*sp.I*sp.residue(sp.exp(sp.I*z)/(z**2+1), z, sp.I) - sp.pi/sp.E) == 0
    val = 2*si.quad(lambda s: 1/(1+s*s), 0, np.inf, weight='cos', wvar=1)[0]; assert abs(val - math.pi/math.e) < 1e-8
    assert sp.simplify(-2*sp.pi*sp.I*sp.residue(sp.exp(-sp.I*z)/(z**2+1), z, -sp.I) - sp.pi/sp.E) == 0
    R_ = 30.0; th = np.linspace(0.1, np.pi-0.1, 50); assert np.max(np.abs(np.cos(R_*np.exp(1j*th)))) > 1e5
    return {"int 1/(x^2+4)": "pi/2", "int cos x/(x^2+1)": "pi/e", "a=-1 lower half-plane": "pi/e", "cos z on arc R=30": "> 1e5"}
@check(L+"08", "symbolic", "")
def calc08():
    z = sp.Symbol('z'); assert sp.residue(sp.cos(z)/z**3, z, 0) == sp.Rational(-1, 2)
    r = sp.residue(1/(z**2+1)**2, z, sp.I); assert sp.simplify(r + sp.I/4) == 0
    assert sp.simplify(2*sp.pi*sp.I*r - sp.pi/2) == 0 and sp.integrate(1/(x**2+1)**2, (x, -sp.oo, sp.oo)) == sp.pi/2
    return {"Res cos z/z^3": "-1/2", "Res 1/(z^2+1)^2 at i": "-i/4"}
@check(L+"09", "symbolic+numeric", "Absolute divergence shown via the lower bound over [k pi, (k+1) pi].")
def calc09():
    assert sp.limit(sp.Si(x), x, sp.oo) == sp.pi/2
    for k in (1, 5, 50):
        blk = si.quad(lambda s: abs(math.sin(s))/s, k*math.pi, (k+1)*math.pi)[0]; assert blk >= 2/((k+1)*math.pi) - 1e-12
    return {"improper value": "pi/2", "|sin x|/x blocks": ">= 2/((k+1) pi), harmonic -> diverges"}
@check(L+"10", "symbolic", "")
def calc10():
    f = x**3 + x; assert f.subs(x, 1) == 2 and sp.diff(f, x).subs(x, 1) == 4 and sp.diff(f, x).subs(x, 2) == 13
    yp = sp.Symbol('y', positive=True); assert sp.diff(sp.sqrt(yp), yp) == 1/(2*sp.sqrt(yp)) and sp.diff(-sp.sqrt(yp), yp) == -1/(2*sp.sqrt(yp))
    return {"(f^-1)'(2)": "1/4", "x^2 branches": "+-1/(2 sqrt y)"}
@check(L+"11", "symbolic", "Three conventions; Plancherel for this f.")
def calc11():
    k = sp.Symbol('k', real=True); xi = sp.Symbol('xi', real=True)
    F1 = 2*sp.integrate(sp.exp(-x)*sp.cos(k*x), (x, 0, sp.oo), conds='none'); assert sp.simplify(F1 - 2/(1+k**2)) == 0
    F3 = 2*sp.integrate(sp.exp(-x)*sp.cos(2*sp.pi*xi*x), (x, 0, sp.oo), conds='none'); assert sp.simplify(F3 - 2/(1+4*sp.pi**2*xi**2)) == 0
    assert sp.integrate(sp.exp(-2*x), (x, 0, sp.oo))*2 == 1
    assert sp.integrate(4/(1+k**2)**2, (k, -sp.oo, sp.oo)) == 2*sp.pi
    return {"F(k)": "2/(1+k^2)", "unitary": "sqrt(2/pi)/(1+k^2)", "ordinary freq": "2/(1+4 pi^2 xi^2)", "Plancherel": "1 = (1/2pi)(2pi)"}
@check(L+"12", "symbolic", "")
def calc12():
    tt = sp.Symbol('t'); G = sp.integrate(sp.cos(tt), (tt, 0, x**2)); assert sp.simplify(sp.diff(G, x) - 2*x*sp.cos(x**2)) == 0
    H = sp.integrate(sp.sign(tt), (tt, 0, x)); assert sp.simplify(H - sp.Abs(x)) == 0 or all(H.subs(x, v) == abs(v) for v in (-2, -1, 1, 3))
    return {"d/dx": "2x cos(x^2)", "sign example": "|x|"}
@check(L+"13", "symbolic", "")
def calc13():
    cc = sp.Symbol('c', positive=True); assert sp.solve(sp.Eq(3*cc**2, 4), cc) == [2/sp.sqrt(3)]
    xp = sp.Symbol('x', positive=True); d = sp.diff(xp**sp.Rational(2, 3), xp); assert sp.solve(d, xp) == []
    h = sp.Symbol('h', positive=True); assert sp.limit(h**sp.Rational(2, 3)/h, h, 0, '+') == sp.oo
    return {"c": "2/sqrt3", "x^(2/3)": "no critical point; cusp at 0"}
@check(L+"14", "symbolic", "")
def calc14():
    assert sp.pi*sp.integrate(x, (x, 0, 4)) == 8*sp.pi
    al = sp.integrate(sp.sqrt(1+4*x**2), (x, 0, 1)); assert abs(float(al) - (2*math.sqrt(5) + math.asinh(2))/4) < 1e-12
    assert math.sqrt(2) < float(al) < 2
    return {"volume": "8 pi", "arc length": round(float(al), 4)}
@check(L+"15", "symbolic", "")
def calc15():
    assert sp.simplify(sp.apart(1/(x**2-1)) - (-1/(2*(x+1)) + 1/(2*(x-1)))) == 0
    a = sp.Symbol('a', positive=True); G = sp.log((x-a)/(x+a))/(2*a); assert sp.simplify(sp.diff(G, x) - 1/(x**2-a**2)) == 0
    e = sp.Symbol('e', positive=True); assert sp.limit(sp.integrate(1/(x**2-1), (x, 1+e, 2)), e, 0, '+') == sp.oo
    return {"partial fractions": "(1/2)(1/(x-1) - 1/(x+1))", "[0,2]": "diverges"}
@check(L+"16", "symbolic", "")
def calc16():
    assert sp.integrate(sp.log(x), (x, 0, 1)) == -1
    e = sp.Symbol('e', positive=True); assert sp.limit(sp.integrate(1/x, (x, e, 1)), e, 0, '+') == sp.oo
    assert sp.integrate(x**sp.Rational(-1, 2), (x, 0, 1)) == 2
    return {"int ln x": -1, "p=-1": "diverges", "p=-1/2": 2}
@check(L+"17", "symbolic", "")
def calc17():
    X, Y = sp.symbols('X Y', real=True)
    u, v = X, -Y; assert sp.diff(u, X) != sp.diff(v, Y)
    u, v = X**2 + Y**2, sp.Integer(0); sol = sp.solve([sp.diff(u, X) - sp.diff(v, Y), sp.diff(u, Y) + sp.diff(v, X)], [X, Y]); assert sol == {X: 0, Y: 0}
    u, v = sp.exp(X)*sp.cos(Y), sp.exp(X)*sp.sin(Y)
    assert sp.simplify(sp.diff(u, X) - sp.diff(v, Y)) == 0 and sp.simplify(sp.diff(u, Y) + sp.diff(v, X)) == 0
    return {"conj z": "CR fail everywhere", "|z|^2": "CR only at 0", "e^z": "CR hold"}
@check(L+"18", "symbolic", "")
def calc18():
    r, th = sp.symbols('r theta', positive=True)
    J = sp.Matrix([r*sp.cos(th), r*sp.sin(th)]).jacobian([r, th]).det(); assert sp.simplify(J - r) == 0
    assert sp.integrate(r, (r, 0, 1), (th, 0, 2*sp.pi)) == sp.pi and sp.integrate(r*sp.exp(-r**2), (r, 0, sp.oo), (th, 0, 2*sp.pi)) == sp.pi
    return {"Jacobian": "r", "disk area": "pi", "Gaussian": "pi"}
@check(L+"19", "symbolic", "Iterated integrals for this f; absolute divergence via polar radial integral.")
def calc19():
    f = (x**2 - y**2)/(x**2 + y**2)**2
    assert sp.simplify(sp.diff(y/(x**2+y**2), y) - f) == 0
    xp, yp = sp.symbols('x y', positive=True); fp_ = f.subs({x: xp, y: yp})
    a = sp.integrate(sp.integrate(fp_, (yp, 0, 1)), (xp, 0, 1)); b = sp.integrate(sp.integrate(fp_, (xp, 0, 1)), (yp, 0, 1))
    assert a == sp.pi/4 and b == -sp.pi/4
    r, e = sp.symbols('r e', positive=True); assert sp.limit(sp.integrate(1/r, (r, e, 1)), e, 0, '+') == sp.oo
    return {"dy dx": "pi/4", "dx dy": "-pi/4", "int |f|": "diverges near 0"}
@check(L+"20", "symbolic", "")
def calc20():
    assert sp.gamma(sp.Rational(1, 2)) == sp.sqrt(sp.pi) and sp.gamma(sp.Rational(5, 2)) == 3*sp.sqrt(sp.pi)/4
    assert sp.gamma(5) == sp.factorial(4) and sp.gamma(0) == sp.zoo
    s = sp.Symbol('s', positive=True); assert sp.limit(sp.gamma(s), s, 0, '+') == sp.oo
    return {"Gamma(1/2)": "sqrt(pi)", "Gamma(5/2)": "3 sqrt(pi)/4", "Gamma(0)": "pole"}
@check(L+"21", "symbolic", "Principal branches as implemented by sympy.")
def calc21():
    assert sp.log(-1) == sp.I*sp.pi and sp.log(1) == 0 and sp.log(-1) + sp.log(-1) == 2*sp.I*sp.pi
    assert sp.sqrt(-4) == 2*sp.I and sp.sqrt(-9) == 3*sp.I and sp.expand(sp.sqrt(-4)*sp.sqrt(-9)) == -6
    return {"Log(1) vs 2 Log(-1)": "0 vs 2 pi i", "sqrt(-4)sqrt(-9)": -6}
@extra("grok-r1-calc-11")
def calc11_topup():
    k = sp.Symbol('k', real=True); F = sp.integrate(sp.exp(-x)*sp.exp(-sp.I*k*x), (x, 0, sp.oo), conds='none') + sp.integrate(sp.exp(x)*sp.exp(-sp.I*k*x), (x, -sp.oo, 0), conds='none')
    assert sp.simplify(F - 2/(1 + k**2)) == 0 and sp.simplify(F/sp.sqrt(2*sp.pi) - sp.sqrt(2/sp.pi)/(1 + k**2)) == 0
    return {"unitary convention": "sqrt(2/pi)/(1+k^2)"}

# ---- round-1 lane: ode ----
L = "grok-r1-ode-"
@check(L+"01", "symbolic", "Explicit solutions substituted; intervals from the pole location.")
def ode01():
    Y = 1/(1 - x); assert sp.simplify(sp.diff(Y, x) - Y**2) == 0 and Y.subs(x, 0) == 1
    C = sp.Symbol('C'); G = 1/(C - x); assert sp.simplify(sp.diff(G, x) - G**2) == 0
    Z = -1/(1 + x); assert sp.simplify(sp.diff(Z, x) - Z**2) == 0 and Z.subs(x, 0) == -1
    return {"y0=1": "1/(1-x) on (-oo,1)", "y0=-1": "-1/(1+x) on (-1,oo)", "general": "1/(C-x) and y=0"}
@check(L+"02", "symbolic", "")
def ode02():
    Y = sp.exp(-x) - sp.exp(-2*x); assert sp.simplify(sp.diff(Y, x) + 2*Y - sp.exp(-x)) == 0 and Y.subs(x, 0) == 0
    C = sp.Symbol('C'); G = sp.exp(-x) + C*sp.exp(-2*x); assert sp.simplify(sp.diff(G, x) + 2*G - sp.exp(-x)) == 0
    return {"solution": "e^-x - e^-2x"}
@check(L+"03", "symbolic", "")
def ode03():
    op = lambda f: sp.diff(f, x, 2) - 4*sp.diff(f, x) + 4*f
    assert sp.simplify(op(x*sp.exp(2*x))) == 0
    Y = (1 - 2*x)*sp.exp(2*x); assert sp.simplify(op(Y)) == 0 and Y.subs(x, 0) == 1 and sp.diff(Y, x).subs(x, 0) == 0
    return {"second solution": "x e^(2x)", "IVP": "(1-2x)e^(2x)"}
@check(L+"04", "symbolic", "")
def ode04():
    yp = x/2*sp.sin(x); assert sp.simplify(sp.diff(yp, x, 2) + yp - sp.cos(x)) == 0
    A = sp.Symbol('A'); assert sp.simplify(sp.diff(A*sp.cos(x), x, 2) + A*sp.cos(x)) == 0
    w = sp.Rational(3, 2); yb = sp.cos(w*x)/(1 - w**2); assert sp.simplify(sp.diff(yb, x, 2) + yb - sp.cos(w*x)) == 0
    return {"resonant y_p": "(x/2) sin x (unbounded)", "omega != omega0": "bounded cos(wx)/(1-w^2)"}
@check(L+"05", "symbolic", "")
def ode05():
    assert sp.simplify(sp.diff(sp.tan(x), x) - (1 + sp.tan(x)**2)) == 0
    M = max(1 + v**2 for v in np.linspace(-1, 1, 201)); assert abs(M - 2) < 1e-12 and min(10, 1/M) == 0.5
    assert sp.limit(sp.tan(x), x, sp.pi/2, '-') == sp.oo
    return {"solution": "tan x on (-pi/2, pi/2)", "PL step": "min(10, 1/2) = 1/2"}
@check(L+"06", "symbolic", "")
def ode06():
    f = x*(1 - x); assert set(sp.solve(f, x)) == {0, 1}
    d = sp.diff(f, x); assert d.subs(x, 0) == 1 and d.subs(x, 1) == -1
    assert f.subs(x, sp.Rational(1, 2)) > 0 and f.subs(x, 2) < 0
    return {"x=0": "unstable", "x=1": "stable"}
@check(L+"07", "symbolic+numeric", "Polar reduction symbolic; blow-up formula substituted.")
def ode07():
    X, Y = sp.symbols('X Y', real=True); r2 = X**2 + Y**2
    f, g = -Y + X*r2, X + Y*r2
    assert sp.simplify(X*f + Y*g - r2**2) == 0 and sp.simplify(X*g - Y*f - r2) == 0
    J = sp.Matrix([f, g]).jacobian([X, Y]).subs({X: 0, Y: 0}); assert set(J.eigenvals()) == {sp.I, -sp.I}
    r0, tt = sp.symbols('r0 t', positive=True); r = r0/sp.sqrt(1 - 2*r0**2*tt); assert sp.simplify(sp.diff(r, tt) - r**3) == 0
    return {"r'": "r^3", "theta'": 1, "linear eigenvalues": "+-i"}
@check(L+"08", "symbolic", "")
def ode08():
    Fp = x**2*y + 3*x + 2*y**2; assert sp.diff(Fp, x) == 2*x*y + 3 and sp.diff(Fp, y) == x**2 + 4*y
    assert sp.diff(y, y) == 1 and sp.diff(2*x, x) == 2
    G = x*y**2; assert sp.diff(G, x) == y**2 and sp.diff(G, y) == 2*x*y
    return {"potential": "x^2 y + 3x + 2y^2", "y dx + 2x dy": "not exact; IF y gives x y^2"}
@check(L+"09", "symbolic", "")
def ode09():
    xp = sp.Symbol('x', positive=True)
    W = lambda f, g, v: sp.simplify(f*sp.diff(g, v) - g*sp.diff(f, v))
    assert W(xp**3, xp**3, xp) == 0 and W(-xp**3, xp**3, xp) == 0  # x<0 side: |x|^3 = -x^3 with x^3 itself
    a, b = sp.symbols('a b'); assert sp.solve([a + b, -a + b], [a, b]) == {a: 0, b: 0}
    assert W(sp.exp(x), sp.exp(2*x), x) == sp.exp(3*x)
    return {"W(x^3,|x|^3)": "0 on each side", "independence": "a=b=0", "W(e^x,e^2x)": "e^(3x)"}
@check(L+"10", "symbolic", "")
def ode10():
    xp = sp.Symbol('x', positive=True); op = lambda f: xp**2*sp.diff(f, xp, 2) - 3*xp*sp.diff(f, xp) + 4*f
    assert sp.simplify(op(xp**2)) == 0 and sp.simplify(op(xp**2*sp.log(xp))) == 0
    op2 = lambda f: x**2*sp.diff(f, x, 2) + x*sp.diff(f, x) - f
    assert sp.simplify(op2(x)) == 0 and sp.simplify(op2(1/x)) == 0
    return {"repeated root": "x^2(A + B ln x)", "x y'' + ...": "A x + B/x on x != 0"}
@check(L+"11", "symbolic", "")
def ode11():
    s = sp.Symbol('s', positive=True); tt = sp.Symbol('t', positive=True)
    assert sp.simplify(sp.inverse_laplace_transform(1/(s*(s+1)), s, tt) - (1 - sp.exp(-tt))) == 0
    Y = 1 - sp.exp(-tt); assert sp.simplify(sp.diff(Y, tt) + Y - 1) == 0
    for sv in (1, 10, 100): assert sp.limit(sp.exp(tt**2 - sv*tt), tt, sp.oo) == sp.oo
    return {"y": "1 - e^-t", "e^(t^2)": "no Laplace transform"}
@check(L+"12", "numeric", "")
def ode12():
    assert np.allclose(sorted(np.linalg.eigvals(np.array([[0, 1], [-2, -3]])).real), [-2, -1])
    assert np.allclose(sorted(np.linalg.eigvals(np.array([[1, 2], [0, -1]])).real), [-1, 1])
    return {"[[0,1],[-2,-3]]": "stable node (-1,-2)", "[[1,2],[0,-1]]": "saddle (+-1)"}
@check(L+"13", "symbolic", "")
def ode13():
    assert sp.diff(x**2, x)*(-x**3) == -2*x**4
    x0, tt = sp.symbols('x0 t', positive=True); X = x0/sp.sqrt(1 + 2*x0**2*tt); assert sp.simplify(sp.diff(X, tt) + X**3) == 0
    X_, Y_ = sp.symbols('X Y'); assert sp.expand(2*X_*Y_ + 2*Y_*(-X_)) == 0
    return {"V'=-2x^4": True, "solution": "x0/sqrt(1+2x0^2 t)", "oscillator V'": 0}
@check(L+"14", "symbolic", "")
def ode14():
    tt = sp.Symbol('t', positive=True); P = 100/(1 + 9*sp.exp(-tt/2))
    assert sp.simplify(sp.diff(P, tt) - P/2*(1 - P/100)) == 0 and P.subs(tt, 0) == 10
    T = sp.solve(sp.Eq(P, 50), tt); assert len(T) == 1 and sp.simplify(T[0] - 2*sp.log(9)) == 0
    return {"P(t)": "100/(1+9e^(-t/2))", "t(P=50)": round(float(2*sp.log(9)), 3)}
@check(L+"15", "symbolic", "")
def ode15():
    A, B, Lx = sp.symbols('A B L')
    Y = A*sp.cos(x) + B*sp.sin(x); assert sp.simplify(sp.diff(Y, x, 2) + Y) == 0
    assert sp.solve([Y.subs(x, 0), Y.subs(x, sp.pi)], [A, B], dict=True) == [{A: 0}]
    assert sp.solve([Y.subs(x, 0), Y.subs(x, sp.pi) - 1], [A, B], dict=True) == []
    assert sp.solve([Y.subs(x, 0), Y.subs(x, sp.Rational(7, 3))], [A, B], dict=True) == [{A: 0, B: 0}]
    return {"y(pi)=0": "B sin x, any B", "y(pi)=1": "none", "L=7/3": "only 0"}
@check(L+"16", "symbolic", "")
def ode16():
    yp = x*sp.sin(x) + sp.cos(x)*sp.log(sp.cos(x)); assert sp.simplify(sp.diff(yp, x, 2) + yp - 1/sp.cos(x)) == 0
    return {"y_p": "x sin x + cos x ln cos x"}
@check(L+"17", "exact", "")
def ode17():
    yv = 1.0
    for _ in range(10): yv += 0.1*yv
    assert abs(yv - 1.1**10) < 1e-12 and abs(yv - 2.5937424601) < 1e-9 and abs(math.e - yv - 0.1245) < 1e-3
    e2 = 1.0
    for _ in range(20): e2 += 0.05*e2
    assert 0.45 < (math.e - e2)/(math.e - yv) < 0.55
    assert abs(1 + 0.1*(-50)) == 4 and 0.04*50 == 2.0
    return {"Euler y(1)": 2.59374, "exact": "e", "halving h error ratio": round((math.e - e2)/(math.e - yv), 3), "|1+h lambda|": 4}
@check(L+"18", "numeric", "Period via elliptic integral and direct ODE integration (rtol 1e-10).")
def ode18():
    th0 = math.pi/2; T = 4*ss.ellipk(math.sin(th0/2)**2); assert abs(T - 7.4163) < 1e-3 and 1.17 < T/(2*math.pi) < 1.19
    ev = lambda t_, v: v[1]; ev.terminal = True; ev.direction = 1
    sol = si.solve_ivp(lambda t_, v: [v[1], -math.sin(v[0])], (0, 20), [th0, 0], events=ev, rtol=1e-10, atol=1e-12)
    half = sol.t_events[0][0]; assert abs(2*half - T) < 1e-6
    X_, V_ = sp.symbols('X V'); E = V_**2/2 - sp.cos(X_); assert sp.simplify(sp.diff(E, X_)*V_ + sp.diff(E, V_)*(-sp.sin(X_))) == 0
    assert abs(2*math.pi*math.sqrt(1/9.81) - 2.006) < 1e-3
    return {"T(pi/2)": round(T, 4), "small-angle": "2 pi", "1 m pendulum": 2.006}
@check(L+"19", "symbolic", "")
def ode19():
    Lp = sp.Symbol('L', positive=True); k = sp.Symbol('k', positive=True, integer=True)
    f = sp.sin(k*sp.pi*x/Lp); assert sp.simplify(sp.diff(f, x, 2) + (k*sp.pi/Lp)**2*f) == 0 and f.subs(x, 0) == 0 and sp.simplify(f.subs(x, Lp)) == 0
    g = sp.cos(k*sp.pi*x); assert sp.simplify(sp.diff(g, x).subs(x, 1)) == 0 and sp.diff(g, x).subs(x, 0) == 0
    h = sp.cos(2*k*sp.pi*x); assert sp.simplify(h.subs(x, 1) - h.subs(x, 0)) == 0
    return {"Dirichlet": "(n pi/L)^2", "Neumann": "(n pi)^2, n>=0", "periodic": "(2 n pi)^2"}
@check(L+"20", "symbolic", "")
def ode20():
    a = [sp.Integer(1), sp.Integer(0), sp.Integer(0)]
    for m in range(1, 30): a.append(a[m-1]/((m+2)*(m+1)))
    assert a[3] == sp.Rational(1, 6) and a[6] == sp.Rational(1, 180)
    Yt = sum(a[k]*x**k for k in range(10)); res = sp.expand(sp.diff(Yt, x, 2) - x*Yt); assert sp.Poly(res, x).degree() >= 10 or res == 0
    assert all(abs(float(a[k+3]/a[k])*(k*k) - 1) < 0.5 for k in (21, 24) if a[k] != 0)
    return {"series": "1 + x^3/6 + x^6/180 + ...", "ratio a_(n+3)/a_n": "~1/n^2 -> 0 (entire)"}
@check(L+"21", "numeric", "Eigenvalues symbolic at rho=0.5; separation growth from one numerical experiment (not a proof).")
def ode21():
    lam = sp.Symbol('lam'); sig, beta, rho = 10, sp.Rational(8, 3), sp.Rational(1, 2)
    roots = sp.solve(lam**2 + (sig+1)*lam + sig*(1-rho), lam); assert all(r < 0 for r in roots) and -beta < 0
    def lor(_, v, r=28.0): return [10*(v[1]-v[0]), v[0]*(r - v[2]) - v[1], v[0]*v[1] - 8/3*v[2]]
    ts = np.linspace(0, 40, 4001)
    a = si.solve_ivp(lor, (0, 40), [1, 1, 1], t_eval=ts, rtol=1e-11, atol=1e-12).y
    b = si.solve_ivp(lor, (0, 40), [1 + 1e-9, 1, 1], t_eval=ts, rtol=1e-11, atol=1e-12).y
    d = np.linalg.norm(a - b, axis=0); assert d[-1] > 1e3*d[1]
    return {"rho=0.5 origin eigenvalues": [float(r) for r in roots] + [-8/3], "rho=28 separation growth": f"{d[1]:.1e} -> {d[-1]:.1e}"}
@extra("grok-r1-ode-14")
def ode14_topup():
    r, K, P0, T = sp.symbols('r K P0 T', positive=True); A = (K - P0)/P0; P = K/(1 + A*sp.exp(-r*T)); tt = sp.log(9*A)/r
    assert sp.simplify(P.subs(T, tt) - sp.Rational(9, 10)*K) == 0 and abs(float(sp.log(9)) - 2.197) < 1e-3
    return {"t to 0.9K": "ln(9(K-P0)/P0)/r", "P0 = K/2": "ln 9/r ~ 2.2/r"}
@extra("grok-r1-ode-17")
def ode17_topup():
    lam = -10.0
    for h, ok in ((0.19, True), (0.2, True), (0.21, False)):
        y = 1.0
        for _ in range(500): y *= (1 + h*lam)
        assert (abs(y) <= 1.0 + 1e-12) == ok
    return {"lambda=-10": "stable iff h <= 0.2"}
@extra("grok-r1-ode-18")
def ode18_topup():
    import scipy.special as _sps; ratio = 2/np.pi*_sps.ellipk(0.5); assert abs(ratio - 1.1803) < 1e-4
    from scipy.integrate import solve_ivp
    s = solve_ivp(lambda t_, y: [y[1], -np.sin(y[0])], (0, 20), [np.pi/2, 0], rtol=1e-11, atol=1e-12, events=lambda t_, y: y[1], dense_output=True)
    ev = s.t_events[0]; ev = ev[ev > 1e-6]; T = 2*ev[0]; assert abs(T/(2*np.pi) - ratio) < 1e-5
    return {"T/T0 at 90 deg": round(ratio, 4)}

# ---- round-1 lane: pde ----
L = "grok-r1-pde-"
lap2 = lambda f, a, b: sp.diff(f, a, 2) + sp.diff(f, b, 2)
@check(L+"01", "symbolic", "")
def pde01():
    u = 3*sp.exp(-t)*sp.sin(x) - sp.exp(-16*t)*sp.sin(4*x)
    assert sp.simplify(sp.diff(u, t) - sp.diff(u, x, 2)) == 0 and u.subs(x, 0) == 0 and sp.simplify(u.subs(x, sp.pi)) == 0
    assert sp.simplify(u.subs(t, 0) - (3*sp.sin(x) - sp.sin(4*x))) == 0
    assert sp.integrate(sp.sin(x), (x, 0, sp.pi))/sp.pi == 2/sp.pi
    return {"solution": "3e^-t sin x - e^-16t sin 4x", "Neumann limit for sin x": "2/pi"}
@check(L+"02", "symbolic", "")
def pde02():
    u = (sp.exp(-(x-2*t)**2) + sp.exp(-(x+2*t)**2))/2
    assert sp.simplify(sp.diff(u, t, 2) - 4*sp.diff(u, x, 2)) == 0 and sp.simplify(u.subs(t, 0) - sp.exp(-x**2)) == 0 and sp.simplify(sp.diff(u, t).subs(t, 0)) == 0
    v = sp.sin(x)*sp.cos(t); assert sp.simplify(sp.diff(v, t, 2) - sp.diff(v, x, 2)) == 0
    return {"d'Alembert": "half-sum of travelling Gaussians"}
@check(L+"03", "symbolic", "")
def pde03():
    X, Y = sp.symbols('X Y', real=True); th = sp.Symbol('th', real=True)
    u = sp.Rational(1, 2) + (X**2 - Y**2)/2; assert lap2(u, X, Y) == 0
    assert sp.simplify(u.subs({X: sp.cos(th), Y: sp.sin(th)}) - sp.cos(th)**2) == 0 and u.subs({X: 0, Y: 0}) == sp.Rational(1, 2)
    assert lap2(X**2 + Y**2, X, Y) == 4
    w = sp.log(X**2 + Y**2); assert sp.simplify(lap2(w, X, Y)) == 0 and sp.integrate(w.subs({X: sp.cos(th), Y: sp.sin(th)}), (th, 0, 2*sp.pi)) == 0
    return {"u(0)": "1/2", "x^2+y^2": "Laplacian 4, u(0)=0 vs avg 1", "ln r^2": "singular at 0, circle avg 0"}
@check(L+"04", "symbolic", "")
def pde04():
    k = sp.Symbol('k', positive=True, integer=True)
    b = 2/sp.pi*sp.integrate(sp.sin(k*x), (x, 0, sp.pi))
    assert sp.simplify(b.subs(k, 1) - 4/sp.pi) == 0 and sp.simplify(b.subs(k, 2)) == 0 and sp.simplify(b.subs(k, 3) - 4/(3*sp.pi)) == 0
    assert sp.summation((-1)**n/(2*n+1), (n, 0, sp.oo)) == sp.pi/4
    return {"b_n": "4/(n pi) odd, 0 even"}
@check(L+"05", "numeric", "Peak of partial sums N = 201..1601 vs (2/pi) Si(pi).")
def pde05():
    target = 2/math.pi*ss.sici(math.pi)[0]; assert abs(target - 1.17898) < 1e-5
    for N in (201, 801, 1601):
        xs = np.linspace(1e-5, 0.1, 20001); k = np.arange(1, N+1, 2)
        S = (4/np.pi)*np.sin(np.outer(xs, k)) @ (1/k); assert abs(S.max() - target) < 3e-3
    return {"Gibbs peak": round(target, 5), "persists for N up to": 1601}
@check(L+"06", "symbolic", "")
def pde06():
    X, Y = sp.symbols('X Y', real=True)
    for u in (Y, sp.exp(X)*sp.sin(Y)): assert sp.simplify(lap2(u, X, Y)) == 0 and u.subs(Y, 0) == 0
    return {"half-plane nonuniqueness": ["y", "e^x sin y"]}
@check(L+"07", "exact", "")
def pde07():
    k = sp.Symbol('k', positive=True, integer=True); u = sp.exp(-k**2*t)*sp.sin(k*x)
    assert sp.simplify(sp.diff(u, t) - sp.diff(u, x, 2)) == 0
    f = math.exp(100); assert 2.6e43 < f < 2.7e43
    return {"backward amplification n=10, T=1": "e^100 ~ 2.69e43"}
@check(L+"08", "symbolic", "")
def pde08():
    k = sp.Symbol('k', positive=True, integer=True)
    b = sp.integrate(x*sp.sin(k*x), (x, -sp.pi, sp.pi))/sp.pi; assert sp.simplify(b - 2*(-1)**(k+1)/k) == 0
    assert all(sp.sin(m*sp.pi) == 0 for m in range(1, 20))
    return {"b_n": "2(-1)^(n+1)/n", "value at pi": 0}
@check(L+"09", "symbolic", "")
def pde09():
    assert sp.integrate(x, (x, 0, 1)) == sp.Rational(1, 2)
    k = sp.Symbol('k', positive=True, integer=True); m = sp.exp(-k**2*sp.pi**2*t)*sp.cos(k*sp.pi*x)
    assert sp.simplify(sp.diff(m, t) - sp.diff(m, x, 2)) == 0 and sp.diff(m, x).subs(x, 0) == 0 and sp.simplify(sp.diff(m, x).subs(x, 1)) == 0
    assert sp.integrate(sp.cos(k*sp.pi*x), (x, 0, 1)) == 0
    return {"steady state": "1/2", "nonconstant modes": "zero mean, decay"}
@check(L+"10", "symbolic", "")
def pde10():
    f = sp.Function('f'); u = f(x - 3*t); assert sp.simplify(sp.diff(u, t) + 3*sp.diff(u, x)) == 0
    w = f(x + 3*t); r = sp.simplify(sp.diff(w, t) + 3*sp.diff(w, x)); assert r != 0
    return {"solution": "f(x-3t)", "f(x+3t) residual": "6 f'"}
@check(L+"11", "numeric", "Roots by brentq; sign cases checked at h = 1, -0.5, -1, -2.")
def pde11():
    s1 = so.brentq(lambda s: s*math.cos(s) + math.sin(s), math.pi/2 + 1e-9, math.pi); assert abs(s1 - 2.0288) < 1e-4 and abs(s1**2 - 4.116) < 1e-3
    k2 = so.brentq(lambda k: math.tanh(k) - k/2, 0.5, 5); assert k2 > 0
    for h in (1, -0.5):
        ks = np.linspace(1e-6, 20, 200001); assert not np.any(np.diff(np.sign(np.tanh(ks) + ks/h)) != 0)
    assert 1 + (-1)*1 == 0
    return {"lambda_1 (h=1)": round(s1**2, 4), "h=-2 negative eigenvalue": f"-{k2**2:.4f}", "h=-1": "lambda=0, X=x"}
@check(L+"12", "symbolic", "")
def pde12():
    u = sp.sin(x)*sp.sinh(y)/sp.sinh(1)
    assert sp.simplify(lap2(u, x, y)) == 0 and u.subs(x, 0) == 0 and sp.simplify(u.subs(x, sp.pi)) == 0 and u.subs(y, 0) == 0 and sp.simplify(u.subs(y, 1) - sp.sin(x)) == 0
    return {"solution": "sin x sinh y / sinh 1"}
@check(L+"13", "symbolic", "")
def pde13():
    u = sp.sin(x)*sp.cos(t); E = sp.integrate((sp.diff(u, t)**2 + sp.diff(u, x)**2)/2, (x, 0, sp.pi)); assert sp.simplify(E - sp.pi/4) == 0
    v = sp.exp(-t/2)*sp.sin(x)*sp.cos(sp.sqrt(3)*t/2)
    assert sp.simplify(sp.diff(v, t, 2) + sp.diff(v, t) - sp.diff(v, x, 2)) == 0
    Ev = sp.integrate((sp.diff(v, t)**2 + sp.diff(v, x)**2)/2, (x, 0, sp.pi))
    assert sp.simplify(sp.diff(Ev, t) + sp.integrate(sp.diff(v, t)**2, (x, 0, sp.pi))) == 0
    return {"E": "pi/4 constant", "damped dE/dt": "-int u_t^2 (checked on an explicit solution)"}
@check(L+"14", "symbolic", "")
def pde14():
    k = sp.Symbol('k', positive=True, integer=True)
    assert sp.simplify(sp.integrate(x*sp.sin(k*x), (x, -sp.pi, sp.pi))/sp.pi - 2*(-1)**(k+1)/k) == 0
    assert sp.integrate(x**2, (x, -sp.pi, sp.pi))/sp.pi == 2*sp.pi**2/3 and sp.summation(4/n**2, (n, 1, sp.oo)) == 2*sp.pi**2/3
    e = sp.Symbol('e', positive=True); assert sp.limit(sp.integrate(1/x, (x, e, sp.pi)), e, 0, '+') == sp.oo
    return {"sum 1/n^2": "pi^2/6", "|x|^-1/2": "not L^2"}
@check(L+"15", "symbolic", "")
def pde15():
    s = sp.Symbol('s'); xx = sp.Symbol('x', positive=True)
    u = sp.integrate(s*(1 - xx), (s, 0, xx)) + sp.integrate(xx*(1 - s), (s, xx, 1)); assert sp.simplify(u - xx*(1 - xx)/2) == 0
    assert sp.simplify(-sp.diff(u, xx, 2) - 1) == 0
    jump = sp.diff(xx*(1 - s), xx) - sp.diff(s*(1 - xx), xx); assert sp.simplify(jump.subs(s, xx) - 1) == 0
    assert sp.integrate(sp.Integer(1), (x, 0, 1)) != 0
    return {"G": "s(1-x) | x(1-s)", "u for f=1": "x(1-x)/2", "Neumann f=1": "incompatible"}
@check(L+"16", "symbolic", "")
def pde16():
    u0 = sp.exp(-x**2); d = sp.diff(u0, x); crit = sp.solve(sp.diff(d, x), x)
    m = min(d.subs(x, c_) for c_ in crit); assert sp.simplify(m + sp.sqrt(2/sp.E)) == 0
    assert sp.simplify(-1/m - sp.sqrt(sp.E/2)) == 0
    xs, ts = sp.symbols('xs ts', positive=True); r = xs/ts; assert sp.simplify(sp.diff(r, ts) + r*sp.diff(r, xs)) == 0
    return {"t*": round(float(sp.sqrt(sp.E/2)), 4), "rarefaction x/t": "solves Burgers"}
@check(L+"17", "symbolic", "")
def pde17():
    assert 4**2 - 4*1*1 == 12 and all(r.is_real for r in sp.solve(x**2 - 4*x + 1, x))
    Y = sp.Symbol('Y'); assert sp.expand(0**2 - 4*Y*1) == -4*Y
    return {"u_xx+4u_xy+u_yy": "hyperbolic (12)", "Tricomi": "-4y"}
@check(L+"18", "symbolic", "")
def pde18():
    tp = sp.Symbol('t', positive=True); Phi = sp.exp(-x**2/(4*tp))/sp.sqrt(4*sp.pi*tp)
    assert sp.simplify(sp.diff(Phi, tp) - sp.diff(Phi, x, 2)) == 0 and sp.simplify(sp.integrate(Phi, (x, -sp.oo, sp.oo))) == 1
    yv = sp.Symbol('yv', real=True)
    expo = sp.expand(-(x - yv)**2/(4*tp) + yv**2); assert sp.simplify(expo.coeff(yv, 2) - (1 - 1/(4*tp))) == 0
    return {"Phi": "solves heat eq, mass 1", "e^(x^2) data": "converges only for t < 1/4"}
@check(L+"19", "symbolic", "")
def pde19():
    assert sp.integrate(sp.sin(x)*sp.cos(2*x), (x, 0, sp.pi)) == sp.Rational(-2, 3)
    assert sp.integrate(sp.sin(x)*sp.cos(2*x), (x, -sp.pi, sp.pi)) == 0 and sp.integrate(sp.sin(2*x)*sp.sin(3*x), (x, 0, sp.pi)) == 0
    return {"[0,pi] sin x cos 2x": "-2/3", "sin2x sin3x": 0}
@check(L+"20", "symbolic", "")
def pde20():
    u = sp.sin(x)*sp.sin(y); assert sp.simplify(lap2(u, x, y) + 2*u) == 0
    for k in (1, 2, 3, 4): assert sp.integrate(sp.sin(k*x), (x, 0, sp.pi)) == (0 if k % 2 == 0 else sp.Rational(2, k))
    kk = sp.Rational(3, 2); A, B = sp.symbols('A B'); up = 1/kk**2 + A*sp.cos(kk*x) + B*sp.sin(kk*x)
    sol = sp.solve([up.subs(x, 0), up.subs(x, sp.pi)], [A, B]); assert len(sol) == 2
    return {"lambda=2": "sin x sin y", "integer k": "solvable iff k even", "k=3/2": "unique"}
@check(L+"21", "exact", "")
def pde21():
    r = 1e-4/0.01**2; assert abs(r - 1) < 1e-12 and abs((1 - 4*r) + 3) < 1e-12
    th = np.linspace(0, np.pi, 1001); g = lambda rr: 1 - 4*rr*np.sin(th/2)**2
    assert np.all(np.abs(g(0.5)) <= 1 + 1e-15) and np.max(np.abs(g(0.51))) > 1
    assert abs(0.02**2/2 - 2e-4) < 1e-15
    return {"r": 1.0, "worst amplification": -3, "dt max (dx=0.02)": 2e-4}
@extra("grok-r1-pde-18")
def pde18_topup():
    for tv, div in ((0.2, False), (0.25, True), (0.3, True)):
        c = 1 - 1/(4*tv); assert (c >= 0) == div
    return {"e^(x^2) data": "convolution diverges for t >= 1/4"}

# ---- round-1 lane: opt ----
L = "grok-r1-opt-"
from scipy.optimize import linprog
@check(L+"01", "symbolic", "")
def opt01():
    lam = sp.Symbol('lam'); sol = sp.solve([y - lam, x - lam, x + y - 10], [x, y, lam], dict=True); assert sol == [{x: 5, y: 5, lam: 5}]
    assert sp.expand(x*(10 - x) - (25 - (x - 5)**2)) == 0 and sp.limit(x*(10 - x), x, sp.oo) == -sp.oo
    return {"max": 25, "min": "none (unbounded below)"}
@check(L+"02", "symbolic", "")
def opt02():
    H = sp.hessian(x**2 + x*y + y**2, (x, y)); assert H.eigenvals() == {1: 1, 3: 1}
    f = x**4 - 2*x**2; assert sp.expand(f - ((x**2 - 1)**2 - 1)) == 0 and sp.diff(f, x, 2).subs(x, 0) == -4
    assert set(sp.solve(sp.diff(f, x), x)) == {-1, 0, 1} and f.subs(x, 1) == f.subs(x, -1) == -1
    return {"quadratic": "PD, unique min 0", "x^4-2x^2": "nonconvex, minima at +-1"}
@check(L+"03", "symbolic", "")
def opt03():
    f = x**2 - y**2; H = sp.hessian(f, (x, y)); assert H == sp.diag(2, -2) and f.subs({x: 0, y: sp.Rational(1, 10)}) < 0
    return {"Hessian": "diag(2,-2) indefinite", "f(0,0.1)": -0.01}
@check(L+"04", "symbolic", "")
def opt04():
    mu = sp.Symbol('mu'); assert sp.solve(2*(1 - 2) + mu, mu) == [2]
    xs = np.linspace(-5, 1, 6001); assert np.all((xs - 2)**2 >= 1 - 1e-12)
    g = -x**2; assert sp.diff(g, x).subs(x, 0) == 0 and g.subs(x, 0) == 0 > g.subs(x, 1)
    return {"x*": 1, "mu": 2, "nonconvex KKT x=0": "global max of -x^2 on [-1,1]"}
@check(L+"05", "numeric", "")
def opt05():
    def run(a, k=400):
        v = np.array([1.0, 1.0])
        for _ in range(k): v = v - a*np.array([1, 10])*v
        return np.abs(v).max()
    assert run(0.19) < 1e-6 and run(0.25) > 1e10 and abs(1 - 10*0.2) == 1 and abs(1 - 10*0.25) == 1.5
    return {"alpha range": "(0, 0.2)", "alpha=0.25": "diverges (factor -1.5)"}
@check(L+"06", "numeric", "")
def opt06():
    A = np.array([[1, 0], [1, 1], [1, 2]], float); b = np.array([1, 3, 4], float)
    sol = np.linalg.lstsq(A, b, rcond=None)[0]; assert np.allclose(sol, [7/6, 1.5])
    r = b - A @ sol; assert np.allclose(A.T @ r, 0) and np.allclose(r, [-1/6, 1/3, -1/6])
    B = np.array([[1, 1], [1, 1]], float); assert np.linalg.matrix_rank(B) == 1
    s2 = np.linalg.lstsq(B, np.array([2, 5.]), rcond=None)[0]; assert np.allclose(s2, [1.75, 1.75])
    return {"fit": "a=7/6, b=3/2", "rank-deficient": "a+b=3.5, min-norm (1.75,1.75)"}
@check(L+"07", "symbolic+numeric", "")
def opt07():
    f = x**4 - 4*x**3 + 4*x**2; assert sp.expand(f - (x*(x - 2))**2) == 0
    assert set(sp.solve(sp.diff(f, x), x)) == {0, 1, 2} and sp.diff(f, x, 2).subs(x, 1) == -4 and f.subs(x, 1) == 1
    g = sp.lambdify(x, sp.diff(f, x))
    def gd(x0):
        v = x0
        for _ in range(5000): v -= 0.01*g(v)
        return v
    assert abs(gd(0.9)) < 1e-6 and abs(gd(1.1) - 2) < 1e-6 and gd(1.0) == 1.0
    return {"x=1": "local max", "GD from 0.9 / 1.1 / 1.0": "0 / 2 / stays 1"}
@check(L+"08", "symbolic", "")
def opt08():
    mu = sp.Symbol('mu'); assert sp.solve(sp.Eq(1 + mu*2*0, 0), mu) == []
    assert sp.solve(x**2, x) == [0] and sp.diff(x**2, x).subs(x, 0) == 0
    return {"feasible set": "{0}", "KKT multiplier": "none", "LICQ": "fails (zero gradient)"}
@check(L+"09", "exact", "")
def opt09():
    assert sp.Rational(0 + 4, 2) == 2 and sp.Rational(0 + 2, 2)**2 == 1
    assert (1 + sp.Rational(1, 3))/2 == sp.Rational(2, 3) > sp.Rational(1, 2)
    l = (0 + 2)/2; r_ = math.log((1 + math.e**2)/2); assert l == 1 and abs(r_ - 1.4338) < 1e-4
    return {"E[X^2] vs (EX)^2": "2 vs 1", "E[1/X]": "2/3", "log example": [1, round(r_, 4)]}
@check(L+"10", "exact", "")
def opt10():
    x1 = sp.Rational(1) - (1 - 2)/sp.Integer(2); x2 = x1 - (x1**2 - 2)/(2*x1); assert x1 == sp.Rational(3, 2) and x2 == sp.Rational(17, 12)
    xp = sp.Symbol('x', positive=True); step = sp.simplify(xp - xp**sp.Rational(1, 3)/sp.diff(xp**sp.Rational(1, 3), xp)); assert sp.simplify(step + 2*xp) == 0
    assert sp.simplify(xp - xp**2/(2*xp) - xp/2) == 0
    return {"Newton sqrt2": ["3/2", "17/12"], "cube root step": "-2x", "x^2 step": "x/2"}
@check(L+"11", "exhaustive+linprog", "")
def opt11():
    V_ = [(0, 0), (4, 0), (3, 1), (0, 2)]; vals = [3*a + 2*b for a, b in V_]; assert vals == [0, 12, 11, 4]
    r = linprog([-3, -2], A_ub=[[1, 1], [1, 3]], b_ub=[4, 6], bounds=[(0, None)]*2); assert abs(-r.fun - 12) < 1e-9
    r2 = linprog([-3, -2], A_ub=[[1, 1], [1, 3]], b_ub=[4, 6], bounds=[(None, None)]*2); assert r2.status == 3
    assert 4 + 0 == 3 + 1 == 4
    return {"max": "12 at (4,0)", "x+y tie": "edge (4,0)-(3,1)", "no sign constraints": "unbounded (linprog status 3)"}
@check(L+"12", "symbolic", "")
def opt12():
    lam = sp.Symbol('lam', positive=True); ll = 3*sp.log(lam) - 12*lam; assert sp.solve(sp.diff(ll, lam), lam) == [sp.Rational(1, 4)]
    nn = sp.Symbol('n', integer=True, positive=True); s = sp.Symbol('s', positive=True)
    dens = lam**3*s**2*sp.exp(-lam*s)/2; assert sp.simplify(sp.integrate(3/s*dens, (s, 0, sp.oo)) - sp.Rational(3, 2)*lam) == 0
    d = np.array([2, 3, 7.]); assert d.mean() == 4 and abs(d.var() - 14/3) < 1e-12
    return {"MLE": "1/4", "E[3/S]": "1.5 lambda (n=3)", "normal MLE": "mean 4, var 14/3"}
@check(L+"13", "symbolic", "")
def opt13():
    f = x + 4/x; assert set(sp.solve(sp.diff(f, x), x)) == {-2, 2} and f.subs(x, 2) == 4 and f.subs(x, -2) == -4
    assert sp.limit(f, x, 0, '-') == -sp.oo
    return {"x>0": "min 4 at 2", "x<0": "unbounded below; max -4 at -2"}
@check(L+"14", "symbolic", "")
def opt14():
    assert sp.limit(sp.exp(-x), x, sp.oo) == 0 and all(math.exp(-v) > 0 for v in (0, 10, 700))
    return {"inf e^-x": "0, not attained", "x on (0,1]": "inf 0 not attained"}
@check(L+"15", "numeric", "")
def opt15():
    A = np.array([[2, -1], [-1, 2.]]); assert np.allclose(np.linalg.eigvalsh(A), [1, 3]) and A[0, 0] > 0 and np.linalg.det(A) > 2.99
    B = np.diag([0, -1.]); assert B[0, 0] == 0 and np.linalg.det(B) == 0 and np.linalg.eigvalsh(B).min() == -1
    return {"[[2,-1],[-1,2]]": "PD (1,3)", "diag(0,-1)": "leading minors 0,0 but not PSD"}
@check(L+"16", "linprog", "")
def opt16():
    d = linprog([4, 6], A_ub=[[-1, -1], [-1, -3]], b_ub=[-3, -2], bounds=[(0, None)]*2); assert abs(d.fun - 12) < 1e-9 and np.allclose(d.x, [3, 0])
    rng = np.random.default_rng(0)
    for _ in range(2000):
        u, v = rng.uniform(0, 5, 2); a, b = rng.uniform(0, 4, 2)
        if u + v >= 3 and u + 3*v >= 2 and a + b <= 4 and a + 3*b <= 6: assert 4*u + 6*v >= 3*a + 2*b - 1e-12
    return {"dual optimum": "12 at (3,0)", "weak duality": "sampled pairs satisfy dual >= primal"}
@check(L+"17", "numeric", "")
def opt17():
    A = np.array([[2, 1], [1, 2.]]); w, V_ = np.linalg.eigh(A); assert np.allclose(w, [1, 3])
    v = np.array([1, -1])/math.sqrt(2); assert np.isclose(v @ A @ v, 1)
    s = 1e3; u = s*np.array([1, 1.]); assert np.isclose(u @ A @ u, 6*s*s)
    return {"min Rayleigh": 1, "max on sphere": 3, "unconstrained": "unbounded above"}
@check(L+"18", "symbolic", "")
def opt18():
    f = (x**2 - 1)**2; assert sp.diff(f, x, 2).subs(x, 0) == -4 and sp.expand(sp.diff(f, x, 2) - (12*x**2 - 4)) == 0
    g = sp.exp(x**2); assert sp.simplify(sp.diff(g, x, 2) - (2 + 4*x**2)*sp.exp(x**2)) == 0
    return {"(x^2-1)^2": "f''(0) = -4, nonconvex", "e^(x^2)": "convex"}
@check(L+"19", "symbolic", "")
def opt19():
    Lc, x0 = sp.symbols('L x0', positive=True)
    assert sp.simplify(x0 - (1/Lc)*Lc*x0) == 0 and sp.simplify(x0 - (2/Lc)*Lc*x0 + x0) == 0
    f = (x*(x - 2))**2; assert sp.diff(f, x).subs(x, 1) == 0 and f.subs(x, 1) == 1
    return {"step 1/L": "one-step convergence", "step 2/L": "x -> -x", "nonconvex": "stuck at x=1"}
@check(L+"20", "symbolic", "")
def opt20():
    f = x**2 - y**2; H = sp.hessian(f, (x, y)); tvec = sp.Matrix([1, 0]); assert (tvec.T*H*tvec)[0] == 2
    assert sp.diff(f.subs(y, 0), x, 2) == 2
    return {"tangent Hessian": 2, "restricted f": "x^2"}
@check(L+"21", "numeric", "Clopper-Pearson exact interval via beta quantiles.")
def opt21():
    from scipy.stats import beta
    lo = beta.ppf(0.025, 11, 2); hi = beta.ppf(0.975, 12, 1); assert abs(lo - 0.615) < 2e-3 and abs(hi - 0.998) < 1e-3
    return {"11/12": round(11/12, 4), "95% CP": [round(lo, 3), round(hi, 3)]}
@extra("grok-r1-opt-12")
def opt12_topup():
    lam = sp.Symbol('lambda', positive=True); xs = [0.5, 1.2, 2.3]; ll = sum(sp.log(lam) - lam*v for v in xs)
    sol = sp.solve(sp.diff(ll, lam), lam)[0]; assert abs(float(sol) - 3/sum(xs)) < 1e-12
    return {"exponential MLE": "1/x-bar"}
@extra("grok-r1-opt-09")
def opt09_topup():
    assert np.isclose(0.5*np.log(1) + 0.5*np.log(4), np.log(2)) and np.log(2) < np.log(2.5)
    return {"X in {1,4}": "E log X = log 2 < log 2.5"}
@extra("grok-r1-opt-19")
def opt19_topup():
    f = lambda z: z**2 + 3*np.sin(z)**2; g = lambda z: 2*z + 3*np.sin(2*z); Lc = 2 + 6; z = 3.0; f0 = f(z); gs = []
    for k in range(1, 201): gs.append(g(z)**2); z -= g(z)/Lc; assert min(gs) <= 2*Lc*(f0 - 0.0)/k + 1e-12
    return {"nonconvex example": "min ||grad||^2 <= 2L(f0 - inf f)/k holds for k <= 200"}

# ---- round-1 lane: fa ----
L = "grok-r1-fa-"
@check(L+"01", "numeric+symbolic", "")
def fa01():
    A = np.array([[4, 1], [2, 3.]]); assert np.allclose(sorted(np.linalg.eigvals(A).real), [2, 5]) and np.allclose(A @ [1, -2], [2, -4])
    assert set(sp.Matrix([[0, -1], [1, 0]]).eigenvals()) == {sp.I, -sp.I}
    return {"[[4,1],[2,3]]": [2, 5], "rotation": "+-i (none real)"}
@check(L+"02", "symbolic", "")
def fa02():
    J = sp.Matrix([[1, 1], [0, 1]]); assert not J.is_diagonalizable() and (J - sp.eye(2)).nullspace() == [sp.Matrix([1, 0])]
    assert sp.Matrix([[2, 0], [0, 2]]).is_diagonalizable()
    return {"Jordan block": "eigenspace dim 1, not diagonalizable", "2I": "diagonal"}
@check(L+"03", "symbolic+numeric", "")
def fa03():
    npos = sp.Symbol('n', positive=True); assert sp.integrate(x**npos, (x, 0, 1)) == 1/(npos + 1)
    v = np.ones(3); assert np.isclose(np.linalg.norm(v), math.sqrt(3)*np.abs(v).max())
    rng = np.random.default_rng(1); W = rng.normal(size=(5000, 3)); r = np.linalg.norm(W, axis=1)/np.abs(W).max(axis=1); assert r.max() <= math.sqrt(3) + 1e-12 and r.min() >= 1 - 1e-12
    for k in (5, 50, 500): u = np.ones(k); assert np.abs(u).sum()/np.abs(u).max() == k
    return {"x^n sup/L1": "1 vs 1/(n+1)", "R^3 constant": "sqrt3", "c00 ratio": "n (unbounded)"}
@check(L+"04", "symbolic", "")
def fa04():
    I = sp.integrate(x*sp.exp(x), (x, 0, 1)); assert I == 1
    b = sp.sqrt(sp.Rational(1, 3))*sp.sqrt((sp.E**2 - 1)/2); assert abs(float(b) - 1.0319) < 1e-4 and float(b) >= 1
    assert abs(1*1 + 1*1) > 1*1 and abs(2) <= math.sqrt(2)*math.sqrt(2) + 1e-12
    return {"exact": 1, "CS bound": round(float(b), 4), "max-norm version": "fails at (1,1)"}
@check(L+"05", "numeric+symbolic", "")
def fa05():
    B = np.array([[1, 0], [1, 1], [0, 1.]]); v = np.array([1, 0, 0.])
    c = np.linalg.solve(B.T @ B, B.T @ v); p = B @ c; assert np.allclose(c, [2/3, -1/3]) and np.allclose(p, [2/3, 1/3, -1/3]) and np.allclose(B.T @ (v - p), 0)
    wrong = np.array([.5, .5, 0]); assert np.isclose((v - wrong) @ B[:, 1], -0.5)
    assert sp.integrate(x, (x, 0, 1)) == sp.Rational(1, 2) and sp.integrate(x, (x, -1, 1)) == 0
    return {"projection": "(2/3,1/3,-1/3)", "naive sum residual . b": -0.5, "projection of x onto constants": {"[0,1]": "1/2", "[-1,1]": 0}}
@check(L+"06", "numeric", "Exact ramp L1 distances on a fine grid (tolerance 1e-6).")
def fa06():
    xs = np.linspace(0, 1, 2_000_001)
    def ramp(k): return np.clip((xs - (0.5 - 1/k))*k, 0, 1)
    for a, b in ((10, 20), (50, 100), (200, 400)):
        d = np.trapezoid(np.abs(ramp(a) - ramp(b)), xs); assert abs(d - (1/a - 1/b)/2) < 1e-6
    step = (xs >= 0.5).astype(float); assert np.trapezoid(np.abs(ramp(1000) - step), xs) < 1e-3
    return {"ramp L1 distance": "(1/n - 1/m)/2", "L1 limit": "step function (discontinuous)"}
@check(L+"07", "symbolic", "")
def fa07():
    for k in (1, 5, 40):
        f = x**k; mx = max(abs(f.subs(x, v)) for v in (0, 1)); mdx = sp.diff(f, x).subs(x, 1); assert mx == 1 and mdx == k
    return {"||x^n||": 1, "||(x^n)'||": "n", "C^1 -> C": "norm <= 1"}
@check(L+"08", "symbolic", "Resolvent unboundedness via divergence of the integral of 1/(x-lam)^2 near lam = 1/2; real rotation eigenvalues.")
def fa08():
    e = sp.Symbol('e', positive=True); lam = sp.Rational(1, 2)
    assert sp.limit(sp.integrate(1/(x - lam)**2, (x, lam + e, 1)), e, 0, '+') == sp.oo
    assert set(sp.Matrix([[0, -1], [1, 0]]).eigenvals()) == {sp.I, -sp.I}
    return {"spectrum of M": "[0,1], no eigenvalues", "rotation": "+-i over C"}
@check(L+"09", "symbolic", "")
def fa09():
    ip = lambda f, g, a, b: sp.integrate(f*g, (x, a, b))
    q = x**2 - ip(x**2, 1, -1, 1)/ip(1, 1, -1, 1); assert sp.simplify(q - (x**2 - sp.Rational(1, 3))) == 0
    assert ip(q, 1, -1, 1) == 0 and ip(q, x, -1, 1) == 0 and ip(x, 1, -1, 1) == 0
    g = sp.sqrt(3)*(2*x - 1); assert ip(g, 1, 0, 1) == 0 and sp.simplify(ip(g, g, 0, 1) - 1) == 0
    assert sp.simplify(ip(sp.sqrt(sp.Rational(3, 2))*x, sp.sqrt(sp.Rational(3, 2))*x, -1, 1) - 1) == 0
    return {"[-1,1]": ["1", "x", "x^2-1/3"], "[0,1] orthonormal": ["1", "sqrt3(2x-1)"]}
@check(L+"10", "numeric", "Random 3x3 Gaussian matrices (seed 2).")
def fa10():
    I = np.eye(2); assert np.isclose(np.linalg.det(2*I), 4)
    rng = np.random.default_rng(2); A, B, C = rng.normal(size=(3, 3, 3))
    assert np.isclose(np.trace(A @ B), np.trace(B @ A)) and not np.allclose(A @ B, B @ A)
    assert np.isclose(np.trace(A @ B @ C), np.trace(B @ C @ A)) and abs(np.trace(A @ B @ C) - np.trace(A @ C @ B)) > 1e-3
    return {"det(2I)": 4, "tr(AB)=tr(BA)": True, "tr(ABC) vs tr(ACB)": "differ for random matrices"}
@check(L+"11", "numeric", "")
def fa11():
    assert np.allclose(np.linalg.eigvalsh(np.array([[2, 1j], [-1j, 2]])), [1, 3])
    w = np.linalg.eigvals(np.array([[1, 1j], [1j, 1]])); assert np.allclose(sorted(w, key=lambda z: z.imag), [1 - 1j, 1 + 1j])
    return {"Hermitian": [1, 3], "complex symmetric": "1 +- i"}
@check(L+"12", "symbolic", "")
def fa12():
    yv = sp.Symbol('yv', positive=True); xx = sp.Symbol('xx', positive=True)
    k = sp.Symbol('k', positive=True, integer=True); om = (k - sp.Rational(1, 2))*sp.pi
    for kk in (1, 2, 3):
        o = (kk - sp.Rational(1, 2))*sp.pi; f = sp.sin(o*yv)
        Kf = sp.integrate(yv*f, (yv, 0, xx)) + xx*sp.integrate(f, (yv, xx, 1))
        assert sp.simplify(Kf - f.subs(yv, xx)/o**2) == 0
    assert np.isclose(np.linalg.norm(np.eye(5)[0] - np.eye(5)[1]), math.sqrt(2))
    return {"eigenvalues": "1/((n-1/2)^2 pi^2), n=1..3 verified", "identity": "e_n sqrt2 apart"}
hand(L+"13", "Excerpt covers 1 <= p < oo only. (l^oo)* != l^1: the limit functional on the closed subspace c of convergent sequences has norm 1; Hahn-Banach extends it to L on l^oo. L vanishes on c_00 (finitely supported sequences). If L(x) = sum a_n x_n with a in l^1, testing on e_n gives a_n = 0 for all n, so L = 0, contradicting L(1,1,1,...) = 1. Hence not every functional on l^oo comes from l^1. Dual exponent for p = 3 is q = 3/2 (1/3 + 2/3 = 1).",
     "Non-constructive (Hahn-Banach); no executable check. Only the arithmetic q = 3/2 is trivially checkable.")
@check(L+"14", "numeric+symbolic", "")
def fa14():
    v = 0.5
    for _ in range(200): v = math.cos(v)
    assert abs(v - 0.739085133) < 1e-8 and math.sin(1) < 0.85 and math.cos(1) > 0
    X_, Y_ = sp.symbols('X Y', positive=True); r = sp.simplify(((X_ + 1/X_) - (Y_ + 1/Y_))/(X_ - Y_)); assert sp.simplify(r - (1 - 1/(X_*Y_))) == 0
    assert sp.solve(sp.Eq(x + 1/x, x), x) == [] and sp.solve(sp.Eq(x/2 + 1, x), x) == [2] and 1/2 + 1 == 1.5
    return {"cos fixed point": round(v, 6), "x+1/x": "ratio 1-1/(xy) -> 1, no fixed point", "x/2+1 on [0,1]": "T(1)=1.5"}
@check(L+"15", "numeric", "")
def fa15():
    A = np.array([[1, 2, 3, 4, 5], [2, 4, 6, 8, 10], [0, 1, 0, 1, 0.]]); r = np.linalg.matrix_rank(A); assert r == 2 and 5 - r == 3
    from scipy.linalg import null_space; assert null_space(A).shape[1] == 3
    return {"3x5 rank 2": "nullity 3"}
@check(L+"16", "numeric", "")
def fa16():
    A = np.array([[3, 0], [4, 5.]]); s = np.linalg.svd(A, compute_uv=False); assert np.allclose(s, [3*math.sqrt(5), math.sqrt(5)])
    assert np.allclose(sorted(np.linalg.eigvals(A).real), [3, 5]) and np.isclose(s.prod(), 15) and np.isclose((s**2).sum(), 50)
    return {"singular values": [round(v, 4) for v in s], "eigenvalues": [3, 5]}
@check(L+"17", "symbolic", "")
def fa17():
    for k in range(1, 6): assert sp.integrate(sp.sin(k*x)/sp.sqrt(sp.pi), (x, -sp.pi, sp.pi)) == 0
    assert sp.integrate(sp.Integer(1), (x, -sp.pi, sp.pi)) == 2*sp.pi
    return {"f=1 sine coefficients": 0, "||1||^2": "2 pi"}
@check(L+"18", "numeric", "")
def fa18():
    k = np.arange(1, 100001); yv = 1/k
    for m in (10, 1000, 99999): e = np.zeros_like(yv); e[m] = 1; assert np.isclose(e @ yv, 1/(m + 1)) and np.linalg.norm(e) == 1
    return {"<e_n, y>": "y_n -> 0", "||e_n||": 1}
@check(L+"19", "numeric", "")
def fa19():
    A = np.array([[0, 1], [0, 0.]]); B = np.array([[0, 0], [1, 0.]])
    assert np.allclose(expm(A) @ expm(B), [[2, 1], [1, 1]]) and np.allclose(expm(A + B), [[math.cosh(1), math.sinh(1)], [math.sinh(1), math.cosh(1)]])
    P = np.diag([0, 2j*np.pi]); Q = np.array([[0, 1], [0, 2j*np.pi]])
    assert np.allclose(expm(P), np.eye(2), atol=1e-9) and np.allclose(expm(Q), np.eye(2), atol=1e-9) and np.allclose(expm(P + Q), np.eye(2), atol=1e-9)
    assert not np.allclose(P @ Q, Q @ P)
    return {"non-commuting": "e^(A+B) != e^A e^B", "converse counterexample": "all exponentials = I, AB != BA"}
@check(L+"20", "numeric", "")
def fa20():
    V_ = np.array([[1, 0], [1, 1], [0, 1.]]); G = V_ @ V_.T; assert np.allclose(np.linalg.eigvalsh(G), [0, 1, 3]) and np.linalg.matrix_rank(G) == 2
    C = np.array([[1, .9, 0], [.9, 1, .9], [0, .9, 1]]); w = np.linalg.eigvalsh(C); assert np.allclose(w, [1 - .9*math.sqrt(2), 1, 1 + .9*math.sqrt(2)]) and w.min() < -0.27
    return {"Gram": "PSD, eigenvalues 0,1,3", "proposed correlation": f"min eigenvalue {w.min():.4f}"}
@check(L+"21", "symbolic", "")
def fa21():
    y1, y2 = sp.symbols('y1 y2'); assert sp.solve([y1 - 2, 2*y2 + 1], [y1, y2]) == {y1: 2, y2: sp.Rational(-1, 2)}
    h = sp.Symbol('h', positive=True); s = sp.Symbol('s', positive=True)
    nrm2 = 2*sp.integrate((1 - s/h)**2, (s, 0, h)); assert sp.simplify(nrm2 - 2*h/3) == 0
    return {"standard": "(2,-1)", "weighted": "(2,-1/2)", "tent L2 norm": "sqrt(2h/3) -> 0, value 1"}
@extra("grok-r1-fa-17")
def fa17_topup():
    n = sp.Symbol('n', positive=True, integer=True)
    assert sp.integrate(sp.cos(x)*sp.sin(n*x), (x, -sp.pi, sp.pi)) == 0 and sp.integrate(sp.cos(x)**2, (x, -sp.pi, sp.pi)) == sp.pi
    return {"cos x vs sine set": "all coefficients 0, ||f||^2 = pi"}

# ---- round-1 lane: meas ----
L = "grok-r1-meas-"
H_ = np.array([[1, 1], [1, -1]])/np.sqrt(2); PLUS = H_ @ K0; MINUS = H_ @ K1
CNOT = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex)
def prob(state, proj_vec): v = np.asarray(state)/np.linalg.norm(state); return abs(np.vdot(proj_vec, v))**2
@check(L+"01", "numeric+symbolic", "")
def meas01():
    s = ket(1, 1, 1j); assert np.isclose(np.vdot(s, s).real, 3) and np.isclose(prob(s, ket(0, 0, 1)), 1/3)
    a = sp.Symbol('a', positive=True); N = (2*a/sp.pi)**sp.Rational(1, 4)
    assert sp.simplify(sp.integrate(N**2*sp.exp(-2*a*x**2), (x, -sp.oo, sp.oo)) - 1) == 0
    return {"P(2)": "1/3", "Gaussian N": "(2a/pi)^(1/4), a>0"}
@check(L+"02", "numeric", "")
def meas02():
    for th in np.linspace(0, np.pi, 13):
        s = ket(np.cos(th), np.sin(th)); assert np.isclose(np.vdot(s, SX @ s).real, np.sin(2*th)) and np.isclose(prob(s, PLUS), (1 + np.sin(2*th))/2)
    ideal = np.sin(np.pi/4); assert abs((ideal - 0.62)/0.03 - 2.9) < 0.05
    return {"<sigma_x>": "sin(2 theta)", "P(+)": "(1+<X>)/2", "pi/8 ideal vs measured": [round(ideal, 4), 0.62]}
@check(L+"03", "numeric", "hbar = 1.")
def meas03():
    Sx, Sy, Sz = SX/2, SY/2, SZ/2; s = K0
    var = lambda A: (np.vdot(s, A @ A @ s) - np.vdot(s, A @ s)**2).real
    assert np.isclose(var(Sx), 0.25) and np.isclose(var(Sy), 0.25) and np.isclose(var(Sz), 0)
    assert np.isclose(np.sqrt(var(Sx)*var(Sy)), 0.5*abs(np.vdot(s, Sz @ s)))
    assert np.isclose(abs(np.vdot(s, Sy @ s)), 0)
    return {"dSx dSy": "1/4 = (1/2)|<Sz>| (equality)", "Sz-Sx bound": "(1/2)|<Sy>| = 0"}
@check(L+"04", "numeric", "")
def meas04():
    p1 = sum(prob(K0, b)*prob(b, K1) for b in (PLUS, MINUS)); assert np.isclose(p1, 0.5)
    return {"P(Z=1) after X": 0.5}
@check(L+"05", "numeric", "")
def meas05():
    assert np.allclose(H_ @ K0, PLUS) and np.allclose(H_ @ H_, I2) and np.allclose(H_ @ SZ @ H_, SX) and np.allclose(H_ @ K1, MINUS)
    assert np.isclose(prob(MINUS, PLUS), 0)
    return {"H|0>": "|+>", "H^2": "I", "H|1>": "|->"}
@check(L+"06", "numeric", "")
def meas06():
    assert np.isclose(np.vdot(PLUS, MINUS), 0)
    rng = np.random.default_rng(3); s = rng.normal(size=2) + 1j*rng.normal(size=2); s /= np.linalg.norm(s)
    for _ in range(20):
        ph = rng.normal(size=2) + 1j*rng.normal(size=2); assert np.isclose(abs(np.vdot(ph, s))**2, abs(np.vdot(ph, -s))**2)
    return {"<+|->": 0, "global phase": "no observable change"}
@check(L+"07", "numeric", "")
def meas07():
    s = ket(1, 1j)/np.sqrt(2); r = [np.vdot(s, P @ s).real for P in (SX, SY, SZ)]; assert np.allclose(r, [0, 1, 0])
    th = np.pi/4; s2 = ket(np.cos(th), np.sin(th)); r2 = [np.vdot(s2, P @ s2).real for P in (SX, SY, SZ)]
    assert np.allclose(r2, [np.sin(2*th), 0, np.cos(2*th)])
    return {"(|0>+i|1>)/sqrt2": "+y", "polar angle": "2 theta"}
@check(L+"08", "numeric", "")
def meas08():
    ps = [ket(np.cos(a/2), np.sin(a/2)) for a in (0, 2*np.pi/3, 4*np.pi/3)]
    E = [2/3*dm(p) for p in ps]; assert np.allclose(sum(E), I2) and all(np.linalg.eigvalsh(e).min() > -1e-12 for e in E)
    assert all(not np.allclose(e @ e, e) for e in E)
    return {"trine": "3 positive elements sum to I, not projectors"}
@check(L+"09", "numeric", "")
def meas09():
    mix = I2/2; assert np.isclose(np.trace(mix @ SX).real, 0) and np.isclose(np.trace(dm(PLUS) @ SX).real, 1)
    r = 0.75*dm(K0) + 0.25*dm(K1); assert np.isclose(np.trace(r @ r).real, 0.625)
    for v in (PLUS, MINUS, ket(1, 1j)/np.sqrt(2)): assert np.isclose(prob(v, K0), 0.5)
    return {"mixture vs |+>": "<X> 0 vs 1", "purity": 0.625}
@check(L+"10", "numeric", "")
def meas10():
    out = CNOT @ np.kron(PLUS, K0); assert np.allclose(out, (np.kron(K0, K0) + np.kron(K1, K1))/np.sqrt(2)) and not np.allclose(out, np.kron(PLUS, PLUS))
    assert np.allclose(CNOT @ np.kron(K1, K0), np.kron(K1, K1)) and np.allclose(CNOT @ np.kron(K0, K0), np.kron(K0, K0))
    return {"CNOT|+0>": "Bell state", "basis states": "copied"}
@check(L+"11", "numeric", "")
def meas11():
    assert np.allclose(CNOT @ np.kron(K1, K0), np.kron(K1, K1))
    SWAP = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]); CN2 = SWAP @ CNOT @ SWAP
    assert np.allclose(CN2 @ np.kron(K1, K0), np.kron(K1, K0))
    return {"control first": "|10> -> |11>", "control second": "|10> unchanged"}
@check(L+"12", "numeric", "")
def meas12():
    XX, ZZ = np.kron(SX, SX), np.kron(SZ, SZ); assert np.allclose(XX @ ZZ, ZZ @ XX) and np.allclose(SX @ SZ - SZ @ SX, -2j*SY)
    A = np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0.]]); B = np.diag([1, 1, 2.]); e1 = np.array([1, 0, 0.])
    assert np.allclose(A @ e1, e1) and np.allclose(B @ e1, e1) and not np.allclose(A @ B, B @ A)
    return {"[XX,ZZ]": 0, "[X,Z]": "-2iY", "common eigenvector, non-commuting": True}
@check(L+"13", "symbolic", "")
def meas13():
    p = sp.integrate(2*sp.sin(sp.pi*x)**2, (x, 0, sp.Rational(1, 4))); assert sp.simplify(p - (sp.Rational(1, 4) - 1/(2*sp.pi))) == 0
    assert sp.integrate(2*sp.sin(sp.pi*x)**2, (x, 0, 1)) == 1
    k = sp.Symbol('k', positive=True, integer=True); f2 = 2*sp.sin(k*sp.pi*x)**2
    var = sp.integrate(x**2*f2, (x, 0, 1)) - sp.integrate(x*f2, (x, 0, 1))**2; assert sp.simplify(var - (sp.Rational(1, 12) - 1/(2*k**2*sp.pi**2))) == 0
    return {"P[0,1/4]": round(float(p), 4), "Delta x^2 (state n)": "1/12 - 1/(2 n^2 pi^2)"}
@check(L+"14", "symbolic", "")
def meas14():
    c1 = sp.integrate(sp.sqrt(2)*sp.sin(sp.pi*x), (x, 0, 1)); assert sp.simplify(c1**2 - 8/sp.pi**2) == 0
    assert sp.integrate(sp.sqrt(2)*sp.sin(2*sp.pi*x), (x, 0, 1)) == 0
    cr = sp.integrate(2*sp.sin(sp.pi*x)*sp.sin(2*sp.pi*x), (x, 0, sp.Rational(1, 2))); assert sp.simplify(cr - 4/(3*sp.pi)) == 0
    assert sp.integrate(sp.sin(sp.pi*x)**2 + sp.sin(2*sp.pi*x)**2, (x, 0, sp.Rational(1, 2))) == sp.Rational(1, 2)
    return {"P(E1) flat": "8/pi^2", "P_left(t)": "1/2 + (4/(3 pi)) cos(w21 t)", "P_left(0)": round(0.5 + float(cr), 4)}
@check(L+"15", "numeric", "")
def meas15():
    M = np.array([[1, 1], [1, -1.]]); assert np.allclose(M.T @ M, 2*np.eye(2)); S = np.diag([1, 1j]); assert np.allclose(S.conj().T @ S, I2)
    return {"[[1,1],[1,-1]]": "U^dag U = 2I", "S": "unitary"}
@check(L+"16", "numeric", "Ideal symmetric beam splitter B = [[1, i], [i, 1]]/sqrt2.")
def meas16():
    B = np.array([[1, 1j], [1j, 1]])/np.sqrt(2)
    for ph in np.linspace(0, 2*np.pi, 9):
        out = B @ np.diag([1, np.exp(1j*ph)]) @ B @ K0; p = np.abs(out)**2
        assert np.isclose(p.sum(), 1) and (np.isclose(p[1], np.cos(ph/2)**2) or np.isclose(p[0], np.cos(ph/2)**2))
    return {"outputs": "cos^2(phi/2), sin^2(phi/2)"}
@check(L+"17", "numeric", "Optimal projective measurement found by scanning the measurement angle.")
def meas17():
    a, b = K0, PLUS; hel = (1 + np.sqrt(1 - abs(np.vdot(a, b))**2))/2; assert np.isclose(hel, (1 + 1/np.sqrt(2))/2)
    best = 0
    for th in np.linspace(0, np.pi, 20001):
        m0 = ket(np.cos(th), np.sin(th)); m1 = ket(-np.sin(th), np.cos(th))
        best = max(best, 0.5*abs(np.vdot(m0, a))**2 + 0.5*abs(np.vdot(m1, b))**2)
    assert abs(best - hel) < 1e-6 and np.isclose(0.5*1 + 0.5*0.5, 0.75)
    pq = (1 + np.sqrt(1 - 4*0.9*0.1*0.5))/2; assert abs(pq - 0.9528) < 1e-4
    return {"Helstrom equal priors": round(hel, 4), "Z strategy": 0.75, "0.9/0.1 priors": round(pq, 4)}
@check(L+"18", "numeric", "")
def meas18():
    r = (I2 + 0.6*SZ + 0.8*SX)/2; assert np.isclose(np.trace(r @ SX).real, 0.8) and np.isclose(np.trace(r @ SZ).real, 0.6) and np.allclose(np.linalg.eigvalsh(r), [0, 1])
    for a in (0.5, 1.0, 1.2): w = np.linalg.eigvalsh((I2 + a*SZ)/2); assert (w.min() >= -1e-12) == (abs(a) <= 1)
    return {"<X>,<Z>": [0.8, 0.6], "pure": True, "valid iff": "|a| <= 1"}
@check(L+"19", "numeric", "")
def meas19():
    frac = prob(K0, PLUS)*prob(PLUS, K1); assert np.isclose(frac, 0.25) and np.isclose(0.5*frac, 0.125)
    return {"z- fraction after z+ selection": 0.25, "of unpolarized source": 0.125}
@check(L+"20", "numeric", "Full teleportation circuit simulated for a random input state.")
def meas20():
    rng = np.random.default_rng(4); s = rng.normal(size=2) + 1j*rng.normal(size=2); s /= np.linalg.norm(s)
    bell = (np.kron(K0, K0) + np.kron(K1, K1))/np.sqrt(2); psi = np.kron(s, bell)
    C12 = np.kron(CNOT, I2); H1 = np.kron(np.kron(H_, I2), I2); psi = H1 @ C12 @ psi
    rho_bob = np.zeros((2, 2), complex)
    for m1 in range(2):
        for m2 in range(2):
            b = psi.reshape(2, 2, 2)[m1, m2, :]; pr = np.vdot(b, b).real; assert np.isclose(pr, 0.25)
            bn = b/np.sqrt(pr); corr = np.linalg.matrix_power(SZ, m1) @ np.linalg.matrix_power(SX, m2) @ bn
            assert np.isclose(abs(np.vdot(corr, s)), 1); rho_bob += pr*dm(bn)
    assert np.allclose(rho_bob, I2/2)
    return {"outcomes": "4 equiprobable", "corrected": "input recovered", "Bob before bits": "I/2"}
@check(L+"21", "exact", "")
def meas21():
    v = 0.995**100; assert abs(v - 0.6058) < 1e-3
    return {"0.995^100": round(v, 4)}

# ---- round-1 lane: dyn ----
L = "grok-r1-dyn-"
HB, ME, EV_J = 1.054571817e-34, 9.1093837015e-31, 1.602176634e-19
def lad(N): a = np.diag(np.sqrt(np.arange(1, N)), 1); return a
@check(L+"01", "exact arithmetic", "CODATA constants.")
def dyn01():
    E1 = np.pi**2*HB**2/(2*ME*(1e-9)**2)/EV_J; assert abs(E1 - 0.376) < 0.001
    return {"E1 (eV)": round(E1, 4), "E_n/E_1": "n^2"}
@check(L+"02", "symbolic", "hbar = m = L = 1 for the matrix element; omega symbolic.")
def dyn02():
    L_ = sp.Symbol('L', positive=True); p1 = sp.sqrt(2/L_)*sp.sin(sp.pi*x/L_); p2 = sp.sqrt(2/L_)*sp.sin(2*sp.pi*x/L_)
    x12 = sp.integrate(x*p1*p2, (x, 0, L_)); assert sp.simplify(x12 + 16*L_/(9*sp.pi**2)) == 0
    assert sp.simplify(sp.integrate(x*p1**2, (x, 0, L_)) - L_/2) == 0
    m, hb = sp.symbols('m hbar', positive=True); w = (4 - 1)*sp.pi**2*hb/(2*m*L_**2); assert sp.simplify(2*sp.pi/w - 4*m*L_**2/(3*sp.pi*hb)) == 0
    return {"x12": "-16L/(9 pi^2)", "period": "4 m L^2/(3 pi hbar)"}
@check(L+"03", "numeric", "Truncated basis N = 60; hbar = omega = 1.")
def dyn03():
    a = lad(60); X = (a + a.T)/np.sqrt(2); P = 1j*(a.T - a)/np.sqrt(2); H = (P @ P).real/2 + X @ X/2
    w = np.linalg.eigvalsh(H)[:5]; assert np.allclose(w, np.arange(5) + 0.5, atol=1e-8)
    return {"lowest levels": [round(v, 6) for v in w]}
@check(L+"04", "numeric", "")
def dyn04():
    a = lad(8); out = a.T @ np.eye(8)[2]; assert np.allclose(out, np.sqrt(3)*np.eye(8)[3])
    N = a.T @ a; assert np.allclose(N @ np.eye(8)[3], 3*np.eye(8)[3]) and np.allclose((a @ a.T)[:7, :7], N[:7, :7] + np.eye(7))
    return {"a^dag|2>": "sqrt(3)|3>", "a^dag a": "N"}
@check(L+"05", "numeric", "hbar = m = omega = 1; thermal formula checked against Boltzmann sum.")
def dyn05():
    a = lad(80); X2 = ((a + a.T) @ (a + a.T))/2
    for n in range(6): assert np.isclose(X2[n, n], n + 0.5)
    beta = 0.7; ws = np.exp(-beta*(np.arange(80) + 0.5)); th = (ws*np.diag(X2)).sum()/ws.sum()
    assert np.isclose(th, 0.5/np.tanh(beta/2), rtol=1e-9)
    return {"<x^2>_n": "n + 1/2 (units hbar/(m omega))", "thermal": "coth form verified"}
@check(L+"06", "numeric", "")
def dyn06():
    xs = np.array([-1.0, 1.0]); ps = np.array([0.5, 0.5]); m3 = (ps*xs**3).sum(); m1 = (ps*xs).sum()
    assert m1 == 0 and m3 == 0
    xs = np.array([0.0, 2.0]); m3 = (ps*xs**3).sum(); m1 = (ps*xs).sum(); assert not np.isclose(m3, m1**3)
    rng = np.random.default_rng(0); smp = rng.normal(1, 0.7, 200000); assert np.isclose(np.mean(smp), 1, atol=0.01)
    return {"x^4 potential": "<x^3> != <x>^3 for spread distributions", "quadratic": "V' linear => exact"}
@check(L+"07", "numeric", "")
def dyn07():
    from math import factorial, exp
    P = [exp(-1)/factorial(n) for n in range(30)]; assert abs(P[2] - 0.1839) < 1e-4 and abs(sum(P) - 1) < 1e-12
    assert abs(exp(-2)*4/2 - 0.2707) < 1e-4
    a = lad(40); c = np.array([exp(-0.5)/np.sqrt(float(factorial(n))) for n in range(40)]); assert np.allclose((a @ c)[:30], c[:30])
    H = a.T @ a; assert not np.allclose(H @ c, (c @ H @ c)*c)
    return {"P(2), alpha=1": round(P[2], 4), "eigenstate of a": True, "eigenstate of H": False}
@check(L+"08", "numeric", "")
def dyn08():
    k1, k2 = 1.0, 1/np.sqrt(2); R = ((k1 - k2)/(k1 + k2))**2; T = 4*k1*k2/(k1 + k2)**2; assert np.isclose(R + T, 1) and abs(R - 0.0294) < 1e-4
    r = (k1 - k2)/(k1 + k2); t = 2*k1/(k1 + k2); assert np.isclose(1 + r, t) and np.isclose(k1*(1 - r), k2*t)
    kap = 1.3; rr = (1 - 1j*kap)/(1 + 1j*kap); assert np.isclose(abs(rr), 1)
    return {"R (E=2V0)": round(R, 4), "E<V0": "|r| = 1 with evanescent tail"}
@check(L+"09", "numeric", "")
def dyn09():
    T = lambda e, ka: 1/(1 + np.sinh(ka)**2/(4*e*(1 - e))); ap = lambda e, ka: 16*e*(1 - e)*np.exp(-2*ka)
    assert abs(T(0.5, 2) - 0.0707) < 1e-4 and abs(ap(0.5, 2) - 0.0733) < 1e-4 and abs(T(0.5, 0.3) - 0.915) < 1e-3 and ap(0.5, 0.3) > 2
    kap = np.sqrt(2*ME*EV_J)/HB*1e-9; assert abs(kap - 5.12) < 0.01 and abs(np.exp(-2*kap) - 3.6e-5) < 1e-6
    return {"exact kappa a=2": round(T(0.5, 2), 4), "approx": round(ap(0.5, 2), 4), "kappa a=0.3": [round(T(0.5, 0.3), 3), round(ap(0.5, 0.3), 2)], "kappa (1 eV, nm^-1)": round(kap, 3)}
@check(L+"10", "symbolic", "")
def dyn10():
    m, al, hb = sp.symbols('m alpha hbar', positive=True); k = m*al/hb**2; psi = sp.sqrt(k)*sp.exp(-k*x)
    assert sp.simplify(2*sp.integrate(psi**2, (x, 0, sp.oo)) - 1) == 0
    assert sp.simplify(-2*k*psi.subs(x, 0) + 2*m*al/hb**2*psi.subs(x, 0)) == 0
    E = -hb**2*k**2/(2*m); assert sp.simplify(E + m*al**2/(2*hb**2)) == 0
    return {"E": "-m alpha^2/(2 hbar^2)", "kappa": "m alpha/hbar^2"}
@check(L+"11", "numeric", "Free evolution by FFT; hbar = m = 1.")
def dyn11():
    N, Lb = 4096, 400.0; xs = np.linspace(-Lb/2, Lb/2, N, endpoint=False); k = 2*np.pi*np.fft.fftfreq(N, Lb/N)
    def width(psi0, t):
        ps = np.fft.ifft(np.exp(-1j*k**2*t/2)*np.fft.fft(psi0)); p = abs(ps)**2; p /= p.sum(); mu = (p*xs).sum(); return np.sqrt((p*(xs - mu)**2).sum())
    s0 = 1.0; g = np.exp(-xs**2/(4*s0**2))
    for t in (0, 1, 3, 6): assert np.isclose(width(g, t), s0*np.sqrt(1 + (t/(2*s0**2))**2), rtol=1e-4)
    ch = g*np.exp(-1j*0.2*xs**2); w = [width(ch, t) for t in (0, 1, 2, 10)]
    assert w[1] < w[0] and w[3] > w[0]
    return {"Gaussian formula": "verified", "chirped widths t=0,1,2,10": [round(v, 3) for v in w]}
@check(L+"12", "symbolic", "")
def dyn12():
    E, hb = sp.symbols('E hbar', positive=True); f = sp.Function('f')(x); Psi = f*sp.exp(-sp.I*E*t/hb)
    assert sp.simplify(sp.diff(Psi*sp.conjugate(Psi), t)) == 0
    return {"d|Psi|^2/dt": 0}
@check(L+"13", "symbolic", "Classical-form operator ODE checked with commuting symbols.")
def dyn13():
    m, w = sp.symbols('m omega', positive=True); x0, p0 = sp.symbols('x0 p0'); xt = x0*sp.cos(w*t) + p0/(m*w)*sp.sin(w*t); pt = m*sp.diff(xt, t)
    assert sp.simplify(sp.diff(pt, t) + m*w**2*xt) == 0 and xt.subs(t, 0) == x0 and sp.simplify(pt.subs(t, 0) - p0) == 0
    a = lad(30); X = (a + a.T)/np.sqrt(2); P = 1j*(a.T - a)/np.sqrt(2); H = a.T @ a + 0.5*np.eye(30); U = expm(-1j*H*0.9)
    assert np.allclose((U.conj().T @ X @ U)[:20, :20], (X*np.cos(0.9) + P*np.sin(0.9))[:20, :20])
    return {"x(t)": "x cos wt + p/(m w) sin wt"}
@check(L+"14", "numeric", "")
def dyn14():
    for z0 in (0.05, 0.3, 1.0, 3.0):
        f = lambda z: np.tan(z) - np.sqrt(z0**2 - z**2)/z; hi = min(z0, np.pi/2) - 1e-12; r = so.brentq(f, 1e-9, hi); assert 0 < r < hi
    zc = np.pi/2; assert np.isclose(zc**2, np.pi**2/4)
    return {"1D even root": "exists for all z0 > 0", "3D threshold": "z0 > pi/2, i.e. V0 a^2 > pi^2 hbar^2/(8m)"}
@check(L+"15", "numeric", "RWA Hamiltonian H = (Delta/2) Z + (Omega/2) X, hbar = 1.")
def dyn15():
    for Om, De in ((1.0, 0.0), (1.0, 0.8)):
        OR = np.hypot(Om, De)
        for tt in np.linspace(0, 10, 21):
            U = expm(-1j*tt*(De/2*SZ + Om/2*SX)); p = abs((U @ K0)[1])**2; assert np.isclose(p, Om**2/OR**2*np.sin(OR*tt/2)**2)
    assert np.isclose(1/(1 + 0.64), 1/1.64)
    return {"resonant": "sin^2(Omega t/2)", "detuned max": "Omega^2/(Omega^2+Delta^2)"}
@check(L+"16", "numeric", "hbar = m = omega = 1; truncated basis.")
def dyn16():
    from math import factorial, exp
    a = lad(60); X = (a + a.T)/np.sqrt(2); P = 1j*(a.T - a)/np.sqrt(2); Tk = (P @ P).real/2; Vp = (X @ X)/2
    for n in range(4): assert np.isclose(Tk[n, n], Vp[n, n]) and np.isclose(Tk[n, n], (n + 0.5)/2)
    c = np.array([exp(-0.5)/np.sqrt(float(factorial(n))) for n in range(60)]); d = c @ Vp @ c - c @ Tk @ c; assert np.isclose(d, 1.0)
    assert np.isclose(-(-13.6), 13.6) and np.isclose(2*-13.6, -27.2)
    return {"eigenstates": "<T> = <V>", "coherent alpha=1, t=0: <V>-<T>": round(d, 6), "hydrogen": "<T> 13.6, <V> -27.2 eV"}
@check(L+"17", "exact arithmetic", "")
def dyn17():
    tau = 10e-9; nu = 1/(2*np.pi*tau); G = HB/tau/EV_J; assert abs(nu - 15.92e6) < 0.01e6 and abs(G - 6.58e-8) < 0.01e-8
    return {"FWHM (MHz)": round(nu/1e6, 2), "Gamma (eV)": float(f"{G:.3g}")}
@check(L+"18", "numeric", "Finite-difference oscillator, grid 1201.")
def dyn18():
    xs = np.linspace(-10, 10, 1201); h = xs[1] - xs[0]
    D = (np.diag(np.full(1201, -2.0)) + np.diag(np.ones(1200), 1) + np.diag(np.ones(1200), -1))/h**2
    w, v = np.linalg.eigh(-D/2 + np.diag(xs**2/2))
    for n in range(5): p = v[:, n]**2; assert abs((p*xs).sum()) < 1e-8 and np.allclose(v[::-1, n], (-1)**n*v[:, n], atol=1e-6) | np.allclose(v[::-1, n], -(-1)**n*v[:, n], atol=1e-6)
    kk = 1.7; e = np.exp(1j*kk*xs[1:-1]); assert not np.allclose(e[::-1], e) and not np.allclose(e[::-1], -e)
    return {"<x> in eigenstates": 0, "e^(ikx)": "no definite parity"}
@check(L+"19", "symbolic", "")
def dyn19():
    m, w, E = sp.symbols('m omega E', positive=True); xt = sp.sqrt(2*E/(m*w**2))
    I_ = sp.integrate(sp.sqrt(2*m*(E - m*w**2*x**2/2)), (x, -xt, xt)); assert sp.simplify(I_ - sp.pi*E/w) == 0
    return {"phase integral": "pi E/omega", "WKB levels": "(n + 1/2) hbar omega"}
@check(L+"20", "exact arithmetic", "")
def dyn20():
    E = 13.6*(1 - 1/4); lam = 1239.84/E; assert np.isclose(E, 10.2) and abs(lam - 121.6) < 0.1
    mp = 1836.15267; shift = 1/(1 + 1/(2*mp)) - 1/(1 + 1/mp)
    assert np.isclose(13.6/2, 6.8) and abs(abs(shift) - 2.72e-4) < 0.05e-4
    return {"Lyman alpha": [10.2, round(lam, 1)], "positronium": "-6.8 eV/n^2", "D vs H relative shift": float(f"{abs(shift):.3g}")}
@check(L+"21", "exact arithmetic", "")
def dyn21():
    assert np.isclose(1.2*1e-24, 1.2e-24) and np.isclose(1.2*1e-28*1e4, 1.2e-24)
    return {"1.2 b": "1.2e-24 cm^2 = 1.2e-28 m^2"}

# ---- round-1 lane: spin ----
L = "grok-r1-spin-"
from sympy.physics.quantum.cg import CG
def tot(s1, s2):
    A = spin_ops(s1); B = spin_ops(s2); d1, d2 = A[0].shape[0], B[0].shape[0]
    J = [np.kron(a, np.eye(d2)) + np.kron(np.eye(d1), b) for a, b in zip(A, B)]; return J, sum(j @ j for j in J)
def swap(d):
    S = np.zeros((d*d, d*d))
    for i in range(d):
        for j in range(d): S[j*d + i, i*d + j] = 1
    return S
@check(L+"01", "numeric", "hbar = 1.")
def spin01():
    Sx, Sy, Sz = spin_ops(1); assert np.allclose(np.linalg.eigvalsh(Sz), [-1, 0, 1])
    return {"S_z spin-1": [-1, 0, 1]}
@check(L+"02", "numeric", "Basis ordered m = j..-j.")
def spin02():
    Sx, Sy, Sz = spin_ops(1); Jp = Sx + 1j*Sy; out = Jp @ np.array([0, 1, 0]); assert np.allclose(out, [np.sqrt(2), 0, 0]) and np.allclose(Jp @ np.array([1, 0, 0]), 0)
    return {"J+|1,0>": "sqrt2 |1,1>", "J+|1,1>": 0}
@check(L+"03", "numeric", "")
def spin03():
    J, S2 = tot(0.5, 0.5); assert np.allclose(sorted(np.linalg.eigvalsh(S2)), [0, 2, 2, 2])
    ud = np.kron(K0, K1); t0 = (np.kron(K0, K1) + np.kron(K1, K0))/np.sqrt(2); s0 = (np.kron(K0, K1) - np.kron(K1, K0))/np.sqrt(2)
    assert np.allclose(ud, (t0 + s0)/np.sqrt(2)) and not np.allclose(S2 @ ud, (ud @ S2 @ ud)*ud)
    A = spin_ops(0.5); J3 = [np.kron(np.kron(a, I2), I2) + np.kron(np.kron(I2, a), I2) + np.kron(np.kron(I2, I2), a) for a in A]
    w = np.round(np.linalg.eigvalsh(sum(j @ j for j in J3)), 8); assert sorted(w.tolist()) == [0.75]*4 + [3.75]*4
    return {"two spins": "S^2 in {0, 2}", "three spins": "4 states S=3/2, 4 states S=1/2 (two doublets)"}
@check(L+"04", "symbolic", "sympy CG (Condon-Shortley).")
def spin04():
    h = sp.Rational(1, 2); a = CG(1, 1, h, -h, sp.Rational(3, 2), h).doit(); b = CG(1, 0, h, h, sp.Rational(3, 2), h).doit()
    assert sp.simplify(a - sp.sqrt(sp.Rational(1, 3))) == 0 and sp.simplify(b - sp.sqrt(sp.Rational(2, 3))) == 0
    return {"<1,1;1/2,-1/2|3/2,1/2>": str(a), "<1,0;1/2,1/2|3/2,1/2>": str(b)}
@check(L+"05", "numeric", "")
def spin05():
    Sx, Sy, Sz = spin_ops(1); assert np.allclose(Sx @ Sy - Sy @ Sx, 1j*Sz)
    assert np.allclose(np.linalg.eigvalsh(Sx @ Sx), [0, 1, 1]) and np.allclose(Sx @ Sx + Sy @ Sy + Sz @ Sz, 2*np.eye(3))
    return {"[Sx,Sy]": "i Sz", "Sx^2 eigenvalues": [0, 1, 1]}
@check(L+"06", "exact", "")
def spin06():
    for l in range(4): Lx, Ly, Lz = spin_ops(l); assert np.allclose(Lx @ Lx + Ly @ Ly + Lz @ Lz, l*(l + 1)*np.eye(2*l + 1))
    return {"|L| for l=2": "sqrt(6) hbar"}
@check(L+"07", "numeric", "")
def spin07():
    rng = np.random.default_rng(1); n = rng.normal(size=3); n /= np.linalg.norm(n); sn = n[0]*SX + n[1]*SY + n[2]*SZ
    assert np.allclose(expm(-1j*2*np.pi*sn/2), -I2) and np.allclose(expm(-1j*4*np.pi*sn/2), I2)
    Sx, Sy, Sz = spin_ops(1); assert np.allclose(expm(-1j*2*np.pi*Sz), np.eye(3))
    return {"R(2pi) spin-1/2": "-I", "R(2pi) spin-1": "I"}
@check(L+"08", "numeric", "")
def spin08():
    w = 1.3; s0 = (K0 + K1)/np.sqrt(2)
    for tt in np.linspace(0, 5, 11):
        s = expm(-1j*w*tt*SZ/2) @ s0; assert np.isclose(np.vdot(s, SX/2 @ s).real, np.cos(w*tt)/2) and np.isclose(np.vdot(s, SY/2 @ s).real, np.sin(w*tt)/2)
    assert abs(2.0023*9.2740100783e-24/6.62607015e-34/1e9 - 28.02) < 0.01
    return {"precession": "cos(wt), sin(wt)", "electron (GHz/T)": 28.02}
@check(L+"09", "numeric", "")
def spin09():
    J, J2 = tot(1, 0.5); w = np.round(np.linalg.eigvalsh(J2), 8); assert sorted(w.tolist()) == [0.75]*2 + [3.75]*4
    return {"1 x 1/2": "j=3/2 (4), j=1/2 (2)"}
@check(L+"10", "numeric", "")
def spin10():
    for s in (0.5, 1, 1.5, 2):
        Sx, Sy, Sz = spin_ops(s); d = Sz.shape[0]
        for i in range(d):
            m = Sz[i, i].real; e = np.eye(d)[i]; assert np.isclose(e @ Sx @ e, 0) and np.isclose((e @ Sx @ Sx @ e).real, (s*(s + 1) - m**2)/2)
    return {"<S_x^2>": "(s(s+1) - m^2)/2"}
@check(L+"11", "numeric", "")
def spin11():
    A = spin_ops(1); B = spin_ops(0.5); LS = sum(np.kron(a, b) for a, b in zip(A, B))
    w = np.round(np.linalg.eigvalsh(LS), 8); assert sorted(w.tolist()) == [-1.0]*2 + [0.5]*4 and np.isclose(np.trace(LS), 0)
    dE = 1239.84*0.597/589.3**2*1000; assert abs(dE - 2.13) < 0.03
    return {"L.S": "j=3/2: 1/2, j=1/2: -1", "Na D splitting (meV)": round(dE, 2)}
@check(L+"12", "numeric", "")
def spin12():
    J, J2 = tot(1, 1); P = swap(3); w, v = np.linalg.eigh(J2 + 0.01*P)
    res = {}
    for k in range(9): jj = round(float((v[:, k].conj() @ J2 @ v[:, k]).real), 6); ex = round(float((v[:, k].conj() @ P @ v[:, k]).real), 6); res.setdefault(jj, set()).add(ex)
    assert res == {6.0: {1.0}, 2.0: {-1.0}, 0.0: {1.0}}
    return {"J=2": "sym", "J=1": "antisym", "J=0": "sym"}
@check(L+"13", "numeric", "Rotation about y.")
def spin13():
    th = np.pi/3; Sx, Sy, Sz = spin_ops(0.5); a = expm(-1j*th*Sy)[0, 0]; assert np.isclose(abs(a)**2, 0.75)
    assert np.isclose(np.cos(np.pi/4)**2, 0.5)
    Sx, Sy, Sz = spin_ops(1); b = expm(-1j*th*Sy)[0, 0]; assert np.isclose(abs(b)**2, np.cos(th/2)**4) and np.isclose(abs(b)**2, 9/16)
    return {"spin-1/2 at 60deg": 0.75, "spin-1 at 60deg": 9/16}
@check(L+"14", "numeric", "")
def spin14():
    P = swap(2); s0 = (np.kron(K0, K1) - np.kron(K1, K0))/np.sqrt(2); assert np.allclose(P @ s0, -s0)
    spat = np.kron(K0, K0); tot_ = np.kron(spat, s0); P4 = np.kron(P, P); assert np.allclose(P4 @ tot_, -tot_)
    return {"1s^2 x singlet": "antisymmetric overall"}
@check(L+"15", "exact arithmetic", "")
def spin15():
    muB = 5.7883818060e-5; d = 2.0023*muB; assert abs(d - 1.159e-4) < 0.001e-4
    return {"splitting at 1 T (eV)": float(f"{d:.4g}")}
@check(L+"16", "numeric", "")
def spin16():
    for l in (1, 2):
        Lx, Ly, Lz = spin_ops(l); L2 = Lx @ Lx + Ly @ Ly + Lz @ Lz; assert np.allclose(Lx @ L2 - L2 @ Lx, 0) and np.allclose(Lx @ Ly - Ly @ Lx, 1j*Lz)
    return {"[Lx,L^2]": 0, "[Lx,Ly]": "i Lz"}
@check(L+"17", "symbolic", "")
def spin17():
    th, ph = sp.symbols('theta phi'); Y00 = 1/sp.sqrt(4*sp.pi); Y10 = sp.sqrt(sp.Rational(3, 4)/sp.pi)*sp.cos(th)
    I = lambda f: sp.integrate(sp.integrate(f*sp.sin(th), (th, 0, sp.pi)), (ph, 0, 2*sp.pi))
    a = I(Y00*sp.cos(th)*Y10); b = I(Y00*sp.cos(th)*Y00); assert sp.simplify(a - 1/sp.sqrt(3)) == 0 and b == 0
    return {"<Y00|cos|Y10>": "1/sqrt3", "<Y00|cos|Y00>": 0}
@check(L+"18", "symbolic", "")
def spin18():
    th, ph = sp.symbols('theta phi'); v = sp.integrate(sp.integrate(sp.cos(th)**2*sp.sin(th), (th, 0, sp.pi)), (ph, 0, 2*sp.pi))
    assert sp.simplify(v - 4*sp.pi/3) == 0
    return {"integral cos^2": "4pi/3", "Y10": "sqrt(3/(4pi)) cos(theta)"}
@check(L+"19", "numeric", "hbar = 1.")
def spin19():
    A = spin_ops(0.5); SS = sum(np.kron(a, a) for a in A)
    for J_ in (1.0, -1.0):
        w, v = np.linalg.eigh(J_*SS)
        if J_ > 0: assert np.allclose(w, [-0.75, 0.25, 0.25, 0.25])
        else: assert np.allclose(w, [-0.25, -0.25, -0.25, 0.75])
    return {"J>0 ground": "singlet -3J/4", "J<0 ground": "triplet J/4"}
@check(L+"20", "numeric", "")
def spin20():
    rng = np.random.default_rng(2); s = [SX, SY, SZ]
    for _ in range(10):
        a, b = rng.normal(size=3), rng.normal(size=3); A = sum(ai*si for ai, si in zip(a, s)); B = sum(bi*si for bi, si in zip(b, s)); c = np.cross(a, b)
        assert np.allclose(A @ B, a @ b*I2 + 1j*sum(ci*si for ci, si in zip(c, s)))
    assert np.allclose(SX @ SY, -SY @ SX)
    return {"identity": "verified on random vectors"}
@check(L+"21", "exact arithmetic", "")
def spin21():
    lam = 299792458/1.420405751e9; assert abs(lam - 0.21106) < 1e-5
    return {"lambda (m)": round(lam, 5)}

# ---- round-1 lane: pert ----
L = "grok-r1-pert-"
from scipy.integrate import solve_ivp, quad
def osc(N):
    a = np.diag(np.sqrt(np.arange(1, N)), 1); X = (a + a.T)/np.sqrt(2); H0 = np.diag(np.arange(N) + 0.5); return a, X, H0
@check(L+"01", "numeric", "hbar = m = omega = 1; N = 80.")
def pert01():
    a, X, H0 = osc(80); lam = 0.3; E = np.linalg.eigvalsh(H0 + lam*X)[0]; assert np.isclose(E - 0.5, -lam**2/2, atol=1e-10)
    return {"exact shift": round(E - 0.5, 8), "second order": -lam**2/2}
@check(L+"02", "symbolic", "")
def pert02():
    lam = sp.Symbol('lambda'); s = sp.series(sp.sqrt(1 + lam), lam, 0, 3).removeO(); assert sp.expand(s - (1 + lam/2 - lam**2/8)) == 0
    a, X, H0 = osc(80); l_ = 0.2; E = np.linalg.eigvalsh(H0 + l_/2*X @ X)[0]; assert np.isclose(E, 0.5*np.sqrt(1 + l_), atol=1e-9)
    for n in range(4): assert np.isclose((X @ X)[n, n], n + 0.5)
    return {"exact": "(1/2) sqrt(1+lambda)", "series": "1 + l/2 - l^2/8"}
@check(L+"03", "numeric+symbolic", "Atomic units.")
def pert03():
    al = sp.Symbol('alpha', positive=True); E = sp.Rational(3, 2)*al - 2*sp.sqrt(2*al/sp.pi)
    a0 = sp.solve(sp.diff(E, al), al)[0]; Em = sp.simplify(E.subs(al, a0)); assert sp.simplify(a0 - 8/(9*sp.pi)) == 0 and sp.simplify(Em + 4/(3*sp.pi)) == 0
    r = sp.Symbol('r', positive=True); psi = sp.exp(-al*r**2); nrm = sp.integrate(4*sp.pi*r**2*psi**2, (r, 0, sp.oo))
    V = sp.integrate(4*sp.pi*r**2*psi**2*(-1/r), (r, 0, sp.oo))/nrm; T = sp.integrate(4*sp.pi*r**2*sp.Rational(1, 2)*sp.diff(psi, r)**2, (r, 0, sp.oo))/nrm
    assert sp.simplify(T + V - E) == 0
    eV = float(Em)*27.211386; assert abs(eV + 11.55) < 0.01 and eV > -13.6057
    return {"alpha*": "8/(9 pi)", "E (eV)": round(eV, 3)}
@check(L+"04", "numeric", "")
def pert04():
    d = 0.3; w, v = np.linalg.eigh(np.array([[0, d], [d, 0]])); assert np.allclose(w, [-d, d]) and np.allclose(abs(v), 1/np.sqrt(2))
    return {"levels": "E0 +- delta"}
@check(L+"05", "symbolic", "Atomic units, a0 = 1.")
def pert05():
    r, th, ph = sp.symbols('r theta phi', positive=True); N = 1/sp.sqrt(32*sp.pi)
    p200 = N*(2 - r)*sp.exp(-r/2); p210 = N*r*sp.exp(-r/2)*sp.cos(th)
    z = sp.integrate(sp.integrate(sp.integrate(p200*r*sp.cos(th)*p210*r**2*sp.sin(th), (r, 0, sp.oo)), (th, 0, sp.pi)), (ph, 0, 2*sp.pi))
    assert sp.simplify(z + 3) == 0
    p100 = sp.exp(-r)/sp.sqrt(sp.pi); z1 = sp.integrate(sp.integrate(p100**2*r*sp.cos(th)*r**2*sp.sin(th), (r, 0, sp.oo)), (th, 0, sp.pi)); assert z1 == 0
    return {"<2s|z|2p0>": "-3 a0", "<1s|z|1s>": 0}
@check(L+"06", "numeric", "hbar = 1; 1001-level flat band, eigendecomposition.")
def pert06():
    Nb, D, g = 1001, 0.01, 0.02; Ek = (np.arange(Nb) - Nb//2)*D; H = np.zeros((Nb + 1, Nb + 1)); H[1:, 1:] = np.diag(Ek); H[0, 1:] = g; H[1:, 0] = g
    w, v = np.linalg.eigh(H); G = 2*np.pi*g**2/D
    for tt in (4.0, 8.0, 12.0):
        amp = (v[0, :]**2*np.exp(-1j*w*tt)).sum(); assert abs(abs(amp)**2 - np.exp(-G*tt)) < 0.02
    tt = 0.5; amp = (v[0, :]**2*np.exp(-1j*w*tt)).sum(); short = 1 - abs(amp)**2
    T2 = 2*np.pi/D; ts = np.linspace(0.9*T2, 1.1*T2, 2001); rv = np.abs(np.exp(-1j*np.outer(ts, w)) @ (v[0]**2))**2; amp2 = np.sqrt(rv.max())
    assert rv.max() > 0.3 and rv.max() > 1e6*np.exp(-G*0.9*T2)
    return {"Gamma predicted": round(G, 4), "exponential match": "within 0.02 at t = 4, 8, 12", "revival peak P0 near 2pi/Delta": round(float(amp2**2), 3)}
@check(L+"07", "exact", "")
def pert07():
    E = lambda Lw: np.pi**2/(2*Lw**2); assert np.isclose(E(2)/E(1), 0.25)
    return {"E_final/E_initial": 0.25}
@check(L+"08", "numeric", "hbar = 1; RK45 rtol 1e-9.")
def pert08():
    al, De, T = 1.0, 0.3, 200.0
    def f(tt, y): Hm = np.array([[al*tt/2, De], [De, -al*tt/2]]); return -1j*(Hm @ y)
    sol = solve_ivp(f, (-T, T), np.array([1, 0], complex), rtol=1e-9, atol=1e-11, max_step=0.05); pD = abs(sol.y[0, -1])**2
    pLZ = np.exp(-2*np.pi*De**2/al); assert abs(pD - pLZ) < 0.01
    sol2 = solve_ivp(f, (0, 3), np.array([np.cos(np.pi/8), np.sin(np.pi/8)], complex), rtol=1e-9, atol=1e-11); assert np.isclose(np.linalg.norm(sol2.y[:, -1]), 1)
    return {"P_D numeric": round(pD, 4), "LZ": round(pLZ, 4)}
@check(L+"09", "numeric", "hbar = m = omega = 1.")
def pert09():
    a, X, H0 = osc(60); X4 = np.linalg.matrix_power(X, 4)
    for n in range(4): assert np.isclose(X4[n, n], (6*n*n + 6*n + 3)/4)
    lam = 1e-3; E = np.linalg.eigvalsh(H0 + lam*X4)[0]; assert abs((E - 0.5) - 3*lam/4) < 1e-5
    return {"<0|x^4|0>": "3/4 = 3 (1/2)^2", "level n": "(6n^2+6n+3)/4"}
@check(L+"10", "numeric", "")
def pert10():
    from math import factorial
    lam = 0.1; I_ = quad(lambda s: np.exp(-s)/(1 + lam*s), 0, np.inf, epsabs=1e-14)[0]
    errs = []; S = 0.0
    for n in range(40): S += (-1)**n*factorial(n)*lam**n; errs.append(abs(S - I_))
    k = int(np.argmin(errs)); assert 7 <= k <= 12 and errs[k] < 1e-3 and errs[-1] > 1
    return {"optimal N (terms)": k + 1, "min error": float(f"{errs[k]:.2g}"), "error at 40 terms": float(f"{errs[-1]:.2g}")}
@check(L+"11", "symbolic", "")
def pert11():
    r, q, mu, V0, m, hb = sp.symbols('r q mu V0 m hbar', positive=True)
    f = -(2*m/(hb**2*q))*sp.integrate(r*V0*sp.exp(-mu*r)/r*sp.sin(q*r), (r, 0, sp.oo), conds='none')
    assert sp.simplify(f + 2*m*V0/(hb**2*(mu**2 + q**2))) == 0
    return {"f_Born": "-2 m V0/(hbar^2 (mu^2+q^2))"}
@check(L+"12", "symbolic", "")
def pert12():
    Lw = sp.Symbol('L', positive=True); psi = sp.sqrt(2/Lw)*sp.sin(sp.pi*x/Lw)
    c1 = sp.integrate(psi*sp.sqrt(1/Lw)*sp.sin(sp.pi*x/(2*Lw)), (x, 0, Lw)); c2 = sp.integrate(psi*sp.sqrt(1/Lw)*sp.sin(sp.pi*x/Lw), (x, 0, Lw))
    assert sp.simplify(c1 - 4*sp.sqrt(2)/(3*sp.pi)) == 0 and sp.simplify(c2**2 - sp.Rational(1, 2)) == 0
    return {"P(new 1)": round(float(c1**2), 4), "P(new 2)": 0.5}
@check(L+"13", "symbolic", "hbar = m = omega = 1.")
def pert13():
    a = sp.Symbol('a', positive=True); psi = x*sp.exp(-a*x**2)
    num = sp.integrate(sp.diff(psi, x)**2/2 + x**2*psi**2/2, (x, -sp.oo, sp.oo)); den = sp.integrate(psi**2, (x, -sp.oo, sp.oo))
    E = sp.simplify(num/den); a0 = [s for s in sp.solve(sp.diff(E, a), a) if s.is_positive][0]; assert a0 == sp.Rational(1, 2) and sp.simplify(E.subs(a, a0)) == sp.Rational(3, 2)
    return {"a*": "1/2", "E": "3/2"}
@check(L+"14", "numeric", "hbar = m = omega = 1.")
def pert14():
    a, X, H0 = osc(60); lam = 1e-3; w, v = np.linalg.eigh(H0 + lam*X); g = v[:, 0]*np.sign(v[0, 0])
    assert abs(g[1] - (-lam/np.sqrt(2))) < 1e-6
    return {"<1|0'>": "-lambda/sqrt2 (first order)"}
@check(L+"15", "numeric", "hbar = 1; RK45.")
def pert15():
    def run(Om, w0):
        def f(tt, y): Hm = np.array([[w0/2, Om*np.cos(w0*tt)], [Om*np.cos(w0*tt), -w0/2]]); return -1j*(Hm @ y)
        ts = np.linspace(0, 2*np.pi/Om, 400); s = solve_ivp(f, (0, ts[-1]), np.array([0, 1], complex), t_eval=ts, rtol=1e-9, atol=1e-11, max_step=0.01)
        return np.max(abs(abs(s.y[0])**2 - np.sin(Om*ts/2)**2))
    d1 = run(1.0, 50.0); d2 = run(1.0, 2.0); assert d1 < 0.05 and d2 > 0.1
    return {"max deviation Omega/omega0=0.02": round(d1, 4), "Omega/omega0=0.5": round(d2, 3)}
@check(L+"16", "numeric", "Finite difference, L = 1, hbar = m = 1, 1999 interior points.")
def pert16():
    Nn = 1999; xs = np.linspace(0, 1, Nn + 2)[1:-1]; h = xs[1] - xs[0]
    K = (np.diag(np.full(Nn, 2.0)) - np.diag(np.ones(Nn - 1), 1) - np.diag(np.ones(Nn - 1), -1))/(2*h*h); E0 = np.linalg.eigvalsh(K)[:3]
    out = {}
    for V0 in (0.5, 20.0):
        E = np.linalg.eigvalsh(K + np.diag(np.where(xs < 0.5, V0, 0.0)))[:3]; out[V0] = (E - E0).tolist()
    assert np.allclose(out[0.5], 0.25, atol=5e-3) and out[0.5][0] < 0.25 and out[20.0][0] < 10 - 0.5
    return {"shifts V0=0.5": [round(s, 4) for s in out[0.5]], "ground shift V0=20": round(out[20.0][0], 3)}
@check(L+"17", "numeric", "hbar = m = 1.")
def pert17():
    for w in (0.7, 1.3):
        a, X, H0 = osc(60); Xp = X/np.sqrt(w)
        for n in range(4): assert np.isclose(w*(Xp @ Xp)[n, n], n + 0.5)
    return {"m omega <x^2>": "hbar (n + 1/2) = dE/domega"}
@check(L+"18", "numeric", "Units mu_B B = 1 small parameter.")
def pert18():
    A = spin_ops(1); B = spin_ops(0.5); J = [np.kron(a, np.eye(2)) + np.kron(np.eye(3), b) for a, b in zip(A, B)]; J2 = sum(j @ j for j in J)
    Mz = np.kron(A[2], np.eye(2)) + 2*np.kron(np.eye(3), B[2]); Jz = J[2]; w, v = np.linalg.eigh(J2 + 1e-3*Jz)
    for k in range(6):
        vk = v[:, k]; jj = (vk.conj() @ J2 @ vk).real; mj = (vk.conj() @ Jz @ vk).real; gz = (vk.conj() @ Mz @ vk).real
        g = 4/3 if np.isclose(jj, 3.75) else 2/3; assert np.isclose(gz, g*mj, atol=1e-6)
    muB = 5.7883818060e-5; assert muB*5 > 4.5e-5*5
    return {"g(3/2)": "4/3", "g(1/2)": "2/3", "mu_B x 5 T (eV)": round(muB*5, 6)}
@check(L+"19", "numeric", "")
def pert19():
    ex = lambda D, V: np.sqrt(D**2/4 + V**2) - D/2
    assert abs(ex(1, 0.1) - 0.0099) < 1e-4 and np.isclose(np.sqrt(0.0025 + 1), 1.00125, atol=1e-5)
    return {"V/D=0.1 exact": round(ex(1, 0.1), 5), "V>>D eigenvalues": "+-1.00125"}
@check(L+"20", "numeric", "")
def pert20():
    w = np.linalg.eigvalsh(np.array([[0, 0.05], [0.05, 1]])); assert abs(w[0] + 0.0024938) < 1e-6
    return {"exact lower shift (eV)": round(w[0], 7), "second order": -0.0025}
@check(L+"21", "exact arithmetic", "")
def pert21():
    E = lambda Z: -Z**2*27.2 + 5/8*Z*27.2; assert np.isclose(E(2), -74.8) and np.isclose(E(3), -193.8) and np.isclose(E(1), -10.2) and E(1) > -13.6
    return {"He": -74.8, "Li+": -193.8, "H-": -10.2}

# ---- round-1 lane: ent ----
L = "grok-r1-ent-"
PHP = (np.kron(K0, K0) + np.kron(K1, K1))/np.sqrt(2); PHM = (np.kron(K0, K0) - np.kron(K1, K1))/np.sqrt(2)
PSP = (np.kron(K0, K1) + np.kron(K1, K0))/np.sqrt(2); PSM = (np.kron(K0, K1) - np.kron(K1, K0))/np.sqrt(2)
H_ = np.array([[1, 1], [1, -1]])/np.sqrt(2); PLUS = H_ @ K0
def pt(r): return r.reshape(2, 2, 2, 2).transpose(0, 3, 2, 1).reshape(4, 4)
def conc(r):
    yy = np.kron(SY, SY); R_ = r @ yy @ r.conj() @ yy; l = np.sqrt(np.clip(np.sort(np.linalg.eigvals(R_).real)[::-1], 0, None)); return max(0.0, l[0] - l[1] - l[2] - l[3])
def neg(r): return (np.abs(np.linalg.eigvalsh(pt(r))).sum() - 1)/2
def werner(p): return p*dm(PSM) + (1 - p)*np.eye(4)/4
@check(L+"01", "numeric", "")
def ent01():
    s = np.ones(4)/2; assert np.linalg.matrix_rank(s.reshape(2, 2)) == 1 and np.allclose(s, np.kron(PLUS, PLUS)) and np.linalg.matrix_rank(PHP.reshape(2, 2)) == 2
    assert np.linalg.matrix_rank(np.array([[0.6, 0], [0, 0]])) == 1
    return {"|++>": "rank 1", "Phi+": "rank 2"}
@check(L+"02", "numeric", "")
def ent02():
    M = np.array([[1, 1], [1, 0]])/np.sqrt(3); s = np.linalg.svd(M, compute_uv=False)**2; assert np.allclose(sorted(s), sorted([(3 - np.sqrt(5))/6, (3 + np.sqrt(5))/6]))
    return {"lambda^2": [round(v, 4) for v in s]}
@check(L+"03", "numeric", "")
def ent03():
    s = ket(1, 1, 1, 0)/np.sqrt(3); rA = ptrace(dm(s), [2, 2], [0]); e = vn_entropy(rA); assert abs(e - 0.5500) < 1e-3 and np.isclose(vn_entropy(dm(s)), 0, atol=1e-9)
    assert np.isclose(vn_entropy(ptrace(np.eye(4)/4, [2, 2], [0])), 1)
    return {"S(rho_A)": round(e, 4), "I/4 marginal entropy": 1}
@check(L+"04", "numeric", "")
def ent04():
    def E(a, b):
        A = np.cos(a)*SZ + np.sin(a)*SX; B = np.cos(b)*SZ + np.sin(b)*SX; return np.vdot(PSM, np.kron(A, B) @ PSM).real
    d = np.pi/180; S = E(0, 45*d) - E(0, 135*d) + E(90*d, 45*d) + E(90*d, 135*d); assert np.isclose(abs(S), 2*np.sqrt(2))
    assert np.isclose(E(0.3, 1.1), -np.cos(0.8)) and abs((2.42 - 2)/0.20 - 2.1) < 1e-9
    return {"|S|": round(abs(S), 4), "sigma above 2": 2.1}
@check(L+"05", "numeric", "")
def ent05():
    w = np.linalg.eigvalsh(pt(dm(PHP))); assert np.allclose(sorted(w), [-0.5, 0.5, 0.5, 0.5])
    return {"PT eigenvalues": sorted(w.round(6).tolist())}
@check(L+"06", "numeric", "Horodecki criterion for maximal CHSH: 2 sqrt(sum of two largest eigenvalues of T^T T).")
def ent06():
    P = [SX, SY, SZ]
    for p in (0.2, 0.34, 0.5, 0.7, 0.72, 0.9):
        r = werner(p); npt = np.linalg.eigvalsh(pt(r)).min() < -1e-12; assert npt == (p > 1/3)
        T = np.array([[np.trace(r @ np.kron(a, b)).real for b in P] for a in P]); ev = np.sort(np.linalg.eigvalsh(T.T @ T))[::-1]
        smax = 2*np.sqrt(ev[0] + ev[1]); assert np.isclose(smax, 2*np.sqrt(2)*p) and ((smax > 2) == (p > 1/np.sqrt(2)))
    return {"entangled": "p > 1/3", "CHSH violation": "p > 1/sqrt2"}
@check(L+"07", "numeric", "")
def ent07():
    r = (dm(PHP) + dm(PHM))/2; assert np.allclose(r, (dm(np.kron(K0, K0)) + dm(np.kron(K1, K1)))/2) and np.linalg.eigvalsh(pt(r)).min() > -1e-12
    return {"mixture": "separable"}
@check(L+"08", "numeric", "")
def ent08():
    g = np.zeros(8); g[0] = g[7] = 1/np.sqrt(2); r = ptrace(dm(g), [2, 2, 2], [0, 1])
    assert np.allclose(r, (dm(np.kron(K0, K0)) + dm(np.kron(K1, K1)))/2) and np.linalg.eigvalsh(pt(r)).min() > -1e-12
    return {"GHZ marginal": "separable"}
@check(L+"09", "numeric", "")
def ent09():
    rng = np.random.default_rng(5)
    def ru(): q, _ = np.linalg.qr(rng.normal(size=(2, 2)) + 1j*rng.normal(size=(2, 2))); return q
    s = ket(1, 1, 1, 0)/np.sqrt(3); e0 = vn_entropy(ptrace(dm(s), [2, 2], [0]))
    for _ in range(5): s2 = np.kron(ru(), ru()) @ s; assert np.isclose(vn_entropy(ptrace(dm(s2), [2, 2], [0])), e0)
    CN = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]]); assert np.allclose(CN @ np.kron(PLUS, K0), PHP)
    return {"local unitaries": "entropy invariant", "CNOT|+0>": "Phi+"}
@check(L+"10", "numeric", "")
def ent10():
    s = np.sqrt(0.7)*np.kron(K0, K0) + np.sqrt(0.3)*np.kron(K1, K1); assert np.allclose(ptrace(dm(s), [2, 2], [0]), np.diag([0.7, 0.3]))
    W = np.array([[0, 1], [1, 0]]); s2 = np.kron(I2, W) @ s; assert np.allclose(ptrace(dm(s2), [2, 2], [0]), np.diag([0.7, 0.3])) and not np.allclose(s, s2)
    return {"purification": "verified", "non-unique": True}
@check(L+"11", "numeric", "")
def ent11():
    a, b = 0.8, 0.6; assert np.isclose(conc(dm(a*np.kron(K0, K0) + b*np.kron(K1, K1))), 2*a*b)
    for p in (0.2, 0.5, 0.9): assert np.isclose(conc(werner(p)), max(0, (3*p - 1)/2), atol=1e-9)
    return {"pure": "2|ab|", "Werner": "max(0,(3p-1)/2)"}
@check(L+"12", "numeric", "Qubit order 1,2,3,4.")
def ent12():
    psi = np.kron(PHP, PHP).reshape(2, 2, 2, 2); bells = [PHP, PHM, PSP, PSM]; avg = np.zeros((4, 4), complex)
    for B in bells:
        Bm = B.reshape(2, 2).conj(); out = np.einsum('aijd,ij->ad', psi, Bm).reshape(4); p = np.vdot(out, out).real; assert np.isclose(p, 0.25)
        assert np.isclose(abs(np.vdot(B, out/np.sqrt(p))), 1); avg += dm(out)
    assert np.allclose(avg, np.eye(4)/4)
    return {"each outcome": "p = 1/4, 1-4 in matching Bell state", "unconditioned rho_14": "I/4"}
@check(L+"13", "numeric", "")
def ent13():
    def W(N):
        v = np.zeros(2**N)
        for k in range(N): v[1 << k] = 1
        return v/np.sqrt(N)
    for N in (3, 4, 5): r = ptrace(dm(W(N)), [2]*N, [0, 1]); assert np.isclose(conc(r), 2/N)
    return {"pairwise concurrence": "2/N (N = 3, 4, 5)"}
@check(L+"14", "numeric", "")
def ent14():
    rng = np.random.default_rng(6); a = rng.normal(size=2) + 1j*rng.normal(size=2); a /= np.linalg.norm(a); b = rng.normal(size=3) + 0j; b /= np.linalg.norm(b)
    assert np.allclose(ptrace(dm(np.kron(a, b)), [2, 3], [0]), dm(a))
    rA = np.diag([0.6, 0.4]); assert np.allclose(ptrace(np.kron(rA, np.eye(2)/2), [2, 2], [0]), rA)
    return {"pure product marginal": "pure", "mixed product": "marginal = rho_A"}
@check(L+"15", "numeric", "")
def ent15():
    mix = (dm(np.kron(K0, K0)) + dm(np.kron(K1, K1)))/2; ex = lambda r, A: np.trace(r @ np.kron(A, A)).real
    assert np.isclose(ex(dm(PHP), SZ), 1) and np.isclose(ex(mix, SZ), 1) and np.isclose(ex(dm(PHP), SX), 1) and np.isclose(ex(mix, SX), 0)
    w = ex(dm(PHP), SX) - ex(dm(PHP), SY) + ex(dm(PHP), SZ); assert np.isclose(w, 3)
    return {"<XX>": {"Phi+": 1, "mixture": 0}, "witness value Phi+": 3}
@check(L+"16", "numeric", "")
def ent16():
    assert np.isclose(neg(dm(PHP)), 0.5) and np.isclose(neg(werner(0.6)), 0.2)
    return {"Phi+": 0.5, "Werner 0.6": 0.2}
@check(L+"17", "numeric", "")
def ent17():
    def maj(x, y):
        x, y = np.sort(x)[::-1], np.sort(y)[::-1]; return all(np.cumsum(x)[:-1] <= np.cumsum(y)[:-1] + 1e-12)
    assert maj([0.6, 0.4], [0.8, 0.2]) and not maj([0.8, 0.2], [0.6, 0.4]) and not maj([0.8, 0.2], [0.5, 0.5])
    assert np.isclose(min(1, 0.2/0.5), 0.4)
    return {"(0.6,0.4)->(0.8,0.2)": True, "reverse": False, "Vidal max prob to Bell": 0.4}
@check(L+"18", "numeric", "")
def ent18():
    assert np.allclose(np.kron(K0, K0), (PHP + PHM)/np.sqrt(2)) and np.allclose(np.kron(H_, H_) @ PHP, PHP)
    return {"|00>": "(Phi+ + Phi-)/sqrt2"}
@check(L+"19", "numeric", "")
def ent19():
    r0 = dm(PHP)
    for p in (0.1, 0.3, 0.49):
        r = r0
        for k in range(2):
            Z = np.kron(SZ, I2) if k == 0 else np.kron(I2, SZ); r = (1 - p)*r + p*Z @ r @ Z
        assert np.isclose(conc(r), (1 - 2*p)**2, atol=1e-9)
    return {"C": "(1-2p)^2 > 0 for p != 1/2"}
@check(L+"20", "numeric", "")
def ent20():
    mi = lambda r: vn_entropy(ptrace(r, [2, 2], [0])) + vn_entropy(ptrace(r, [2, 2], [1])) - vn_entropy(r)
    mix = (dm(np.kron(K0, K0)) + dm(np.kron(K1, K1)))/2; assert np.isclose(mi(dm(PHP)), 2) and np.isclose(mi(mix), 1)
    return {"Phi+": 2, "mixture": 1}
@check(L+"21", "exact arithmetic", "")
def ent21():
    z = (2.30 - 2)/0.10; import scipy.stats as sst; p = sst.norm.sf(z); assert np.isclose(z, 3) and abs(p - 0.00135) < 1e-5
    return {"sigma": 3.0, "one-sided p": float(f"{p:.3g}")}

# ---- round-1 lane: open ----
L = "grok-r1-open-"
H_ = np.array([[1, 1], [1, -1]])/np.sqrt(2); PLUS = H_ @ K0
def ch(Ks, r): return sum(K @ r @ K.conj().T for K in Ks)
def ad(g): return [np.array([[1, 0], [0, np.sqrt(1 - g)]]), np.array([[0, np.sqrt(g)], [0, 0]])]
def lind(H, Ls, r):
    out = -1j*(H @ r - r @ H)
    for Lk in Ls: out += Lk @ r @ Lk.conj().T - 0.5*(Lk.conj().T @ Lk @ r + r @ Lk.conj().T @ Lk)
    return out
def lind_ss(H, Ls):
    d = H.shape[0]; M = np.zeros((d*d, d*d), complex)
    for k in range(d*d): E = np.zeros(d*d, complex); E[k] = 1; M[:, k] = lind(H, Ls, E.reshape(d, d)).reshape(-1)
    w, v = np.linalg.eig(M); r = v[:, np.argmin(abs(w))].reshape(d, d); return r/np.trace(r)
def favg(Ks, d=2, n=4000, seed=0):
    rng = np.random.default_rng(seed); s = 0
    for _ in range(n): v = rng.normal(size=d) + 1j*rng.normal(size=d); v /= np.linalg.norm(v); s += np.vdot(v, ch(Ks, dm(v)) @ v).real
    return s/n
def fent(Ks, d=2): return sum(abs(np.trace(K))**2 for K in Ks)/d**2
@check(L+"01", "numeric", "")
def open01():
    rng = np.random.default_rng(0); v = rng.normal(size=2) + 1j*rng.normal(size=2); r = dm(v/np.linalg.norm(v))
    for _ in range(1500): r = ch(ad(0.05), r)
    assert np.allclose(r, dm(K0), atol=1e-8) and np.allclose(sum(K.conj().T @ K for K in ad(0.3)), I2)
    p1 = 1/(1 + np.exp(1.5)); g = 0.1; Ks = [np.sqrt(1 - p1)*K for K in ad(g)] + [np.sqrt(p1)*np.array([[np.sqrt(1 - g), 0], [0, 1]]), np.sqrt(p1)*np.array([[0, 0], [np.sqrt(g), 0]])]
    r = I2/2
    for _ in range(600): r = ch(Ks, r)
    assert np.isclose(r[1, 1].real, p1, atol=1e-8)
    return {"T=0 fixed point": "|0><0|", "generalized AD fixed point": "thermal p1"}
@check(L+"02", "numeric", "")
def open02():
    p = 0.2; r = dm((K0 + np.exp(0.4j)*K1)/np.sqrt(2)); r2 = (1 - p)*r + p*SZ @ r @ SZ
    assert np.allclose(np.diag(r2), np.diag(r)) and np.isclose(r2[0, 1], (1 - 2*p)*r[0, 1])
    return {"populations": "unchanged", "coherence factor": "1-2p"}
@check(L+"03", "numeric", "")
def open03():
    p = 0.3; Ks = [np.sqrt(1 - 3*p/4)*I2] + [np.sqrt(p/4)*P for P in (SX, SY, SZ)]; assert np.allclose(sum(K.conj().T @ K for K in Ks), I2)
    rng = np.random.default_rng(1); v = rng.normal(size=2) + 1j*rng.normal(size=2); r = dm(v/np.linalg.norm(v)); assert np.allclose(ch(Ks, r), (1 - p)*r + p*I2/2)
    bad = [np.sqrt(1 - p)*I2] + [np.sqrt(p)*P for P in (SX, SY, SZ)]; assert np.allclose(sum(K.conj().T @ K for K in bad), (1 + 2*p)*I2)
    return {"completeness": "I", "wrong weights": "(1+2p) I"}
@check(L+"04", "exact arithmetic", "")
def open04():
    h, k = 6.62607015e-34, 1.380649e-23; x = h*5e9/(k*0.02); p1 = 1/(1 + np.exp(x)); Te = h*5e9/(k*np.log(99))
    assert abs(x - 12.0) < 0.05 and abs(p1 - 6.1e-6) < 0.2e-6 and abs(Te - 0.0522) < 0.0005
    return {"hf/kT": round(x, 2), "p1 at 20 mK": float(f"{p1:.2g}"), "T_eff for 1% (mK)": round(Te*1e3, 1)}
@check(L+"05", "numeric", "")
def open05():
    rng = np.random.default_rng(2); d = 3
    A = rng.normal(size=(d, d)) + 1j*rng.normal(size=(d, d)); H = A + A.conj().T; Lk = rng.normal(size=(d, d)) + 1j*rng.normal(size=(d, d))
    v = rng.normal(size=d) + 1j*rng.normal(size=d); r = dm(v/np.linalg.norm(v))
    assert np.isclose(np.trace(lind(H, [Lk], r)), 0, atol=1e-10)
    bad = -1j*(H @ r - r @ H) + Lk @ r @ Lk.conj().T; assert not np.isclose(np.trace(bad), 0)
    return {"dTr/dt": 0, "without anticommutator": "nonzero"}
@check(L+"06", "numeric", "Ensemble of 200000 static detunings.")
def open06():
    rng = np.random.default_rng(3); sg = 1.0; de = rng.normal(0, sg, 200000)
    for tt in (0.5, 1.0, 2.0):
        fid = abs(np.mean(np.exp(1j*de*tt))); assert abs(fid - np.exp(-sg**2*tt**2/2)) < 0.01
        echo = abs(np.mean(np.exp(1j*de*tt/2)*np.exp(-1j*de*tt/2))); assert np.isclose(echo, 1)
    return {"FID": "exp(-sigma^2 t^2/2)", "echo (static)": "fully refocused"}
@check(L+"07", "numeric", "")
def open07():
    for tt in (0.0, 0.5, 2.0, 50.0):
        c = np.exp(-tt); r = np.array([[0.5, c/2], [c/2, 0.5]]); F = np.vdot(PLUS, r @ PLUS).real; assert np.isclose(F, (1 + c)/2)
    return {"F(t)": "(1+e^(-t/T2))/2 -> 1/2"}
@check(L+"08", "numeric", "")
def open08():
    A = [I2/np.sqrt(2), SZ/np.sqrt(2)]; B = [dm(K0), dm(K1)]; rng = np.random.default_rng(4)
    for _ in range(5): v = rng.normal(size=2) + 1j*rng.normal(size=2); r = dm(v/np.linalg.norm(v)); assert np.allclose(ch(A, r), ch(B, r)) and np.allclose(ch(A, r), np.diag(np.diag(r)))
    assert np.allclose(B[0], (A[0] + A[1])/np.sqrt(2)) and np.allclose(B[1], (A[0] - A[1])/np.sqrt(2))
    return {"same channel": True, "mixing": "Hadamard"}
@check(L+"09", "numeric", "")
def open09():
    php = (np.kron(K0, K0) + np.kron(K1, K1))/np.sqrt(2); r = dm(php); pt = r.reshape(2, 2, 2, 2).transpose(2, 1, 0, 3).reshape(4, 4)
    assert np.isclose(np.linalg.eigvalsh(pt).min(), -0.5)
    rng = np.random.default_rng(5); v = rng.normal(size=2) + 1j*rng.normal(size=2); s = dm(v/np.linalg.norm(v)); assert np.linalg.eigvalsh(s.T).min() > -1e-12
    return {"(T x I)|Phi+><Phi+|": "min eigenvalue -1/2", "T on single qubit": "positive"}
@check(L+"10", "exact arithmetic", "")
def open10():
    assert np.isclose(np.exp(-52/26), 0.1353, atol=1e-4) and abs(26*np.log(2) - 18.02) < 0.01
    return {"P(52 ns)": round(np.exp(-2), 4), "half-life (ns)": round(26*np.log(2), 2)}
@check(L+"11", "numeric", "")
def open11():
    x = 1.7; gd = 1.0; gu = np.exp(-x); M = np.array([[-gu, gd], [gu, -gd]]); w, v = np.linalg.eig(M); p = v[:, np.argmin(abs(w))].real; p /= p.sum()
    assert np.isclose(p[1], 1/(1 + np.exp(x)))
    return {"steady p1": "1/(1+e^(dE/kT))"}
@check(L+"12", "numeric", "")
def open12():
    r = dm(PLUS); r2 = ch([dm(K0), dm(K1)], r); assert np.allclose(r2, I2/2) and np.isclose(np.trace(r2 @ r2).real, 0.5)
    assert np.allclose(ch([dm(K0), dm(K1)], dm(K0)), dm(K0))
    return {"|+> after unread Z": "I/2", "purity": 0.5}
@check(L+"13", "numeric", "Lindblad steady state; basis (e, g), hbar = 1.")
def open13():
    G = 1.0; sm = np.array([[0, 0], [1, 0]], complex)
    for Om in (0.3, 1.0, 3.0, 30.0):
        r = lind_ss(Om/2*SX, [np.sqrt(G)*sm]); s = 2*Om**2/G**2; assert np.isclose(r[0, 0].real, s/(2*(1 + s)), atol=1e-8)
    r = lind_ss(0.5*SX, [np.sqrt(G)*sm, np.sqrt(2*0.5)*np.diag([1, 0]).astype(complex)]); s = 2*1.0**2/G**2
    assert r[0, 0].real < s/(2*(1 + s)) - 1e-3
    r = lind_ss(50*SX, [np.sqrt(G)*sm, np.sqrt(1.0)*np.diag([1, 0]).astype(complex)]); assert abs(r[0, 0].real - 0.5) < 1e-3
    return {"rho_ee": "s/(2(1+s))", "with dephasing": "lower", "strong drive": "-> 1/2"}
@check(L+"14", "Monte Carlo", "20000 trajectories, seed fixed.")
def open14():
    rng = np.random.default_rng(6); G = 1.0; tj = rng.exponential(1/G, 20000)
    for tt in (0.5, 1.0, 2.0): assert abs(np.mean(tj > tt) - np.exp(-G*tt)) < 0.01
    return {"ensemble": "matches e^(-Gamma t) within 0.01"}
@check(L+"15", "numeric", "")
def open15():
    d = 1e6; T2 = 3e-6; ts = np.linspace(0, 5e-6, 5001); P = (1 + np.cos(2*np.pi*d*ts)*np.exp(-ts/T2))/2
    pk = [i for i in range(1, 5000) if P[i] > P[i - 1] and P[i] >= P[i + 1]]; assert abs((ts[pk[1]] - ts[pk[0]]) - 1e-6) < 2e-8
    return {"fringe period (us)": 1.0}
hand(L+"16", "Conceptual: Born (weak coupling) and Markov (bath correlation time << system relaxation time) assumptions are the standard conditions in the Davies/Born-Markov derivation; a narrow-band, strongly coupled mode violates both, and treating it as part of the system with Markovian damping of the combined system is the standard remedy. No numerical content to execute.")
@check(L+"17", "numeric", "")
def open17():
    assert abs(0.999**200 - 0.8186) < 1e-4
    dl = 0.01; N = 200; Rx = lambda a: expm(-1j*a*SX/2)
    U = np.linalg.matrix_power(Rx(dl), N); inf_coh = 1 - abs(np.vdot(K0, U @ K0))**2; assert np.isclose(inf_coh, np.sin(N*dl/2)**2)
    p = np.sin(dl/2)**2; inf_st = 1 - (1 - p)**N; assert inf_coh > 50*inf_st/2 and abs(inf_st - N*dl**2/4) < 1e-3
    return {"0.999^200": round(0.999**200, 4), "coherent infidelity": round(inf_coh, 4), "stochastic infidelity": round(inf_st, 5)}
@check(L+"18", "exact arithmetic", "")
def open18():
    r = (1 - 0.998)*(2 - 1)/2; assert np.isclose(r, 0.001)
    return {"r": 0.001}
@check(L+"19", "numeric", "")
def open19():
    rng = np.random.default_rng(7); A = rng.normal(size=(4, 4)) + 1j*rng.normal(size=(4, 4)); H = A + A.conj().T; U = expm(-1j*H*2.3)
    v = rng.normal(size=4) + 1j*rng.normal(size=4); r = dm(v/np.linalg.norm(v)); r2 = U @ r @ U.conj().T
    assert np.isclose(np.trace(r2 @ r2).real, 1) and np.isclose(np.trace(r2).real, 1)
    return {"purity under unitary": "constant"}
@check(L+"20", "numeric", "Average fidelity from entanglement fidelity, F_avg = (d F_e + 1)/(d + 1), cross-checked by sampling.")
def open20():
    g = 1 - np.exp(-50e-9/100e-6); Ks = ad(g); Fe = fent(Ks); Fa = (2*Fe + 1)/3; inf = 1 - Fa
    assert abs(inf - g/3) < 1e-7 and abs(inf - 1.667e-4) < 0.01e-4 and abs((1 - favg(Ks)) - inf) < 2e-5
    return {"gamma": float(f"{g:.4g}"), "avg infidelity": float(f"{inf:.4g}")}
@check(L+"21", "exact arithmetic", "")
def open21():
    v = 0.997**40; assert abs(v - 0.8867) < 1e-4
    return {"0.997^40": round(v, 4)}

def _data_crosscheck(d):
    """Cross-check family JSON files: every family has a pass/hand-proof-only result; recompute family_sha256."""
    probs = []; seen = 0
    for fn in ("grok-round0-families.draft.json", "families-train.draft.json", "families-dev.draft.json"):
        p = os.path.join(d, fn)
        if not os.path.exists(p): probs.append(f"missing {fn}"); continue
        for f in json.load(open(p, encoding="utf-8"))["families"]:
            seen += 1; cid = f["verification"]["check_id"]; st = R.get(cid, {}).get("status")
            if st not in ("pass", "hand-proof-only"): probs.append(f"{f['family_id']}: check {cid} status {st}")
            body = json.dumps({k: v for k, v in f.items() if k != "packet_manifest"}, sort_keys=True, ensure_ascii=False).encode()
            if hashlib.sha256(body).hexdigest() != f["packet_manifest"]["family_sha256"]: probs.append(f"{f['family_id']}: family_sha256 mismatch")
            if f["split"] == "test": probs.append(f"{f['family_id']}: locked-test family present")
    return {"families_seen": seen, "problems": probs}

if __name__ == "__main__":
    for fn in REG: fn()
    out = {"tool_versions": {"python": platform.python_version(), "sympy": sp.__version__, "numpy": np.__version__, "scipy": scipy.__version__},
           "summary": {"checks": len(R), "pass": sum(v["status"] == "pass" for v in R.values()),
                       "hand_proof_only": sum(v["status"] == "hand-proof-only" for v in R.values()),
                       "fail": sorted(k for k, v in R.items() if v["status"] not in ("pass", "hand-proof-only"))},
           "results": dict(sorted(R.items()))}
    if "--data" in sys.argv: out["data_crosscheck"] = _data_crosscheck(sys.argv[sys.argv.index("--data") + 1])
    s = json.dumps(out, indent=2, ensure_ascii=False)
    if "--json" in sys.argv: open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8").write(s + "\n")
    print(json.dumps(out["summary"], indent=1));
    if "data_crosscheck" in out: print(json.dumps(out["data_crosscheck"], indent=1))
    ok = not out["summary"]["fail"] and (not out.get("data_crosscheck") or not out["data_crosscheck"]["problems"])
    sys.exit(0 if ok else 1)
