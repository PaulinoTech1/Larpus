# Proposed correction: `grok-r1-opt-05/d` (PROPOSAL, pending owner approval)

Status: **proposal only. Pending owner approval and reviewer disposition.** Written 2026-10-22 (ET) by Grok Bot.
Codex corrected the proposed target's Hessian-norm wording on 2026-10-22;
that editorial correction is not an owner review or admission decision.
No family file was edited. `docs/finetune/families-dev.draft.json`, the owner-reviewed package
(`owner-signoff-20261022-092213`) and the rights copy (`owner-rights-20261022-094356`) still hold this variant
with `reviewed_target: null` and admission `hold`. Grok Bot's agreement with its own correction is not independent
review. The executed checks below test stated results on examples; they are not general proofs.

Family: `grok-r1-opt-05` (Mathematician, Continuous optimization, **dev** split). Variant `d`, kind `missing_assumption`.
Prompt (unchanged): "What step size should I use for gradient descent?"

## Defect

The held draft target says: "For an L-smooth function, any fixed step 0 < alpha < 2/L avoids divergence on
quadratics, and alpha = 1/L is the standard safe choice." This is false without convexity (or at least a lower
bound). Counterexample: `f(x) = -x^2` is L-smooth with `L = |f''| = 2`. With `alpha = 0.5`, which is inside
`(0, 2/L) = (0, 1)`, the update is `x_(k+1) = x_k - 0.5 * (-2 x_k) = 2 x_k`, so any nonzero start diverges.

## Correct scope (what each condition buys)

| Assumption | What a fixed step `0 < alpha < 2/L` gives |
| --- | --- |
| Convex quadratic, Hessian eigenvalues in `[mu, L]`, `mu > 0` | Linear convergence of the iterates to the unique minimizer; rate `max(abs(1 - alpha*mu), abs(1 - alpha*L)) < 1` |
| Convex quadratic, PSD Hessian with a zero eigenvalue (`mu = 0`) | Converges to a minimizer (not unique) when one exists (`b` in the range of `A`); if not, `f` is unbounded below and the iterates drift off |
| L-smooth and bounded below (convexity not needed) | `f` decreases monotonically and the gradient norm tends to zero (descent lemma). This does **not** give convergence of the iterates, or of `f` to a global minimum |
| L-smooth only (no lower bound) | No guarantee: `f(x) = -x^2` diverges |
| `alpha >= 2/L` on a quadratic with top eigenvalue `L` | Divergence (or non-decaying oscillation at exactly `2/L`) along the top eigenvector |

Even convex and bounded below is not enough for iterate convergence without a minimizer: for
`f(x) = log(1 + exp(-x))` (`L = 1/4`), gradient descent drives the gradient to zero while `x_k` grows without bound.
The unbounded growth uses a hand argument: `f' < 0` everywhere, so `x_k` increases. A bounded increasing sequence would converge to a stationary point, and none exists.

## Proposed `reviewed_target` for variant d

> It depends on your function, so I need two facts: a curvature bound L (the Lipschitz constant of the gradient,
> which for a quadratic is the largest absolute Hessian eigenvalue), and whether the objective is convex or at least bounded
> below. If f is L-smooth and bounded below, any fixed step 0 < alpha < 2/L makes f decrease every step and drives
> the gradient to zero, and alpha = 1/L is the standard safe choice. That alone does not guarantee that the
> iterates converge. For a convex quadratic whose Hessian eigenvalues lie in [mu, L] with mu > 0, the same range does
> converge to the unique minimizer. Without a lower bound it can blow up: f(x) = -x^2 has L = 2, and alpha = 0.5
> gives x_(k+1) = 2 x_k. What is your function, or can you bound its Hessian? If not, a backtracking line search
> avoids guessing. Checked by hand: the update factors and the counterexample.

Proposed `teacher_critique` update for variant d:
- `invalid_or_unsupported_step`: "Answers with a fixed number without asking for the smoothness constant or the objective's convexity or lower bound."
- `assumptions`: ["smoothness constant L not given", "convexity / lower bound of the objective not given"]
- `decisive_check`: "f(x) = -x^2, L = 2, alpha = 0.5: x_(k+1) = 2 x_k diverges, although alpha < 2/L. For a convex quadratic with eigenvalues in [mu, L], mu > 0, the factors abs(1 - alpha*lambda) < 1 iff 0 < alpha < 2/L."
- `uncertainty`: "Bounded-below L-smooth guarantees concern f-decrease and gradient norms, not iterate convergence."

Related wording to review (not held, not changed here): variant `c`'s approved target says "constant steps below 2/L work
for convex problems". That is right for f-decrease, gradient norm and (with a minimizer) convergence. The logistic example
shows it does not ensure iterate convergence when no minimizer exists. The reviewer may want the same qualification there.

## Executable check

Script: `data/evals/tuning/round0-20261022-0940/check_opt05d.py` (git-ignored run folder; sha256
`61cfde75388182d7bfb1f4bdedd712c2b42eb1e839782090ea6d7e9f4c4894df`). It ran locally on the PC on 2026-10-22 from
09:45:58 to 09:46:00 ET. It used the isolated `Larpus` WSL train venv (`/home/larpus/train-venv/bin/python`, read from stdin), with
Python 3.12.3, numpy 2.5.4 and sympy 1.14.0. It finished with exit 0 and printed "ALL CHECKS PASS". The full output is in `check_opt05d.output.txt` next to it.

Core snippet (the full script adds the randomized convex trials, PSD-singular, nonconvex and logistic cases):

```python
import numpy as np, sympy as sp
x, a = sp.symbols("x alpha", real=True); Lp = sp.symbols("L_pos", positive=True)
f = -x**2
print(sp.simplify(x - sp.Rational(1, 2) * sp.diff(f, x)), sp.Abs(sp.diff(f, x, 2)))   # 2*x, L = 2
print(sp.reduce_inequalities([1 - a*Lp < 1, 1 - a*Lp > -1], a))                      # 0 < alpha < 2/L
z = 1.0
for _ in range(10): z = z - 0.5 * (-2 * z)
print(z)                                                                              # 1024.0: diverges
```

Results:

| Check | Result |
| --- | --- |
| `f=-x^2`, `L=2`, `alpha=1/2` | update `2*x`; `alpha` in `(0, 2/L)`; `x_10 = 1024` from `x_0 = 1`, `f = -1,048,576`: **diverges** |
| Contraction condition on a curvature-`L` direction | `(alpha > 0) & (alpha < 2/L)` |
| 200 random convex quadratics, n = 5, eigenvalues in [0.1, 10], `alpha` in (0.02, 1.98)/L | all had `rho < 1` and an error at most `rho^300 * e0` (max rho 0.9974; worst error/bound 0.93) |
| `alpha = 2.05/L` on diag(1, 10) | `abs(x2)` = 17,292.6 after 200 steps: diverges |
| PSD singular, `b` in range | converges to `(1, 5)`, a non-unique minimizer (null-space part unchanged) |
| PSD singular, `b` not in range | `x2 = 500`, `f = -500` after 500 steps: unbounded below, iterates diverge |
| Nonconvex `x^2/2 + 3 sin x` (f'' in [-2, 4], L = 4, bounded below), 41 starts x 3 steps | monotone decrease in every run; max final abs(grad) 4.4e-15 |
| Logistic `log(1+e^-x)`, `L = 1/4`, `alpha = 1/L` | after 1e5 steps x = 12.90, abs(grad) = 2.5e-6: gradient tends to 0 while x keeps growing (unbounded by the hand argument above) |

Limits: these are numerical and symbolic checks of specific instances and of the one-dimensional contraction condition.
The general statements (the descent lemma and linear convergence for strongly convex quadratics) are standard results
that these checks illustrate but do not prove.

## To admit (owner/reviewer)

1. Approve or edit the target and critique above.
2. Apply them to a **new versioned copy** of the reviewed package (not to the drafts), set the reviewer, date and
   disposition, and recompute the `grok-r1-opt-05` family hash.
3. Decide whether variant c needs the same iterate-convergence qualification.
4. Because opt-05 is a **dev** family, this edit changes a dev reference. Record it before the dev baseline is officially scored.
   The round-zero baseline excluded `dev/grok-r1-opt-05/d` from target-based scoring.
