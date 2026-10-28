"""Executable checks for the 12 Grok Bot round-zero synthetic families (DRAFT).

Re-run owner-side in a dedicated dev environment (python + sympy + numpy + scipy).
Each check asserts the facts the draft target answers rely on and prints a JSON
result. A passing numeric check tests a stated result; it is not a general proof.
Usage: python verify_round0_families.py [--json out.json]
"""
import json, sys, platform
import numpy as np, scipy, sympy as sp
from scipy.linalg import expm

R = {}
def check(fid, kind, limits):
    def deco(fn):
        def run():
            try:
                facts = fn(); R[fid] = {"status": "pass", "kind": kind, "facts": facts, "limits": limits}
            except AssertionError as e:
                R[fid] = {"status": "FAIL", "kind": kind, "error": str(e), "limits": limits}
        run.__name__ = fn.__name__; return run
    return deco

x, y, n, t, c = sp.symbols('x y n t c', real=True)

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

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if callable(fn) and name[:1] in "mq" and name[1:].isdigit(): fn()
    out = {"tool_versions": {"python": platform.python_version(), "sympy": sp.__version__, "numpy": np.__version__, "scipy": scipy.__version__},
           "results": dict(sorted(R.items()))}
    s = json.dumps(out, indent=2)
    if "--json" in sys.argv: open(sys.argv[sys.argv.index("--json") + 1], "w").write(s + "\n")
    print(s); sys.exit(0 if all(v["status"] == "pass" for v in R.values()) and len(R) == 12 else 1)
