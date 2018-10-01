"""Weighted low rank approximation

Here, we implement the EM algorithm of [SJ03]_, and use it as the basis for
finding low rank approximations maximizing non-Gaussian likelihoods.

.. [SJ03] `Srebro and Jaakkola 2003 <https://www.aaai.org/Papers/ICML/2003/ICML03-094.pdf>`_

Author: Abhishek Sarkar <aksarkar@alum.mit.edu>

"""

import numpy as np
import scipy.special as sp
import scipy.stats as st
import sklearn.decomposition as skd

def lra(x, rank):
  """Return the unweighted low rank approximation of x

  The solution is given by truncated SVD. This implementation automatically
  chooses a randomized algorithm if x is big enough.

  :param x: ndarray (n, p)
  :param rank: rank of the approximation

  :returns low_rank: ndarray (n, p)

  """
  u, d, vt = skd.PCA(n_components=rank)._fit(x)
  if d.shape[0] > rank:
    # It was faster to perform full SVD, so we need to truncate ourselves
    u = u[:,:rank]
    d = d[:rank]
    vt = vt[:rank]
  return np.einsum('ij,j,jk->ik', u, d, vt)

def wlra(x, w, rank, max_iters=1000, atol=1e-3, verbose=False):
  """Return the weighted low rank approximation of x

  Minimize the weighted Frobenius norm between x and the approximation z using
  EM [SJ03]_.

  Raises RuntimeError on convergence failure.

  :param x: input data (n, p)
  :param w: input weights (n, p)
  :param rank: - rank of the approximation (non-negative)
  :param max_iters: - maximum number of EM iterations
  :param atol: - minimum absolute difference in objective function for convergence
  :param verbose: - print objective function updates

  :returns low_rank: - ndarray (n, p)

  """
  n, p = x.shape
  # Important: WLRA requires weights 0 <= w <= 1
  w = np.array(w, dtype='float')
  w /= w.max()
  # Important: the procedure is deterministic, so initialization
  # matters.
  #
  # Srebro and Jaakkola suggest the best strategy is to initialize
  # from zero, but go from a full rank down to a rank k approximation in
  # the first iterations
  #
  # For now, take the simpler strategy of just initializing to zero. Srebro and
  # Jaakkola suggest this can underfit.
  z = np.zeros(x.shape)
  obj = (w * np.square(x)).mean()
  if verbose:
    print(f'wsvd [0] = {obj}')
  for i in range(max_iters):
    z1 = lra(w * x + (1 - w) * z, rank)
    update = (w * np.square(x - z1)).mean()
    if verbose:
      print(f'wsvd [{i + 1}] = {update}')
    if update > obj:
      raise RuntimeError('objective increased')
    elif np.isclose(update, obj, atol=atol):
      return z1
    else:
      z = z1
      obj = update
  raise RuntimeError('failed to converge')

def safe_exp(x):
  """Numerically safe exp"""
  x = np.array(x)
  return np.where(x > 100, x, np.exp(x))

def pois_llik(y, eta):
  """Return ln p(y | eta) assuming y ~ Poisson(exp(eta))

  This implementation supports broadcasting eta (i.e., sharing parameters
  across observations).

  :param y: scalar or ndarray
  :param eta: scalar or ndarray

  :returns llik: ndarray (y.shape)

  """
  return y * eta - safe_exp(eta) - sp.gammaln(y + 1)

def pois_lra(x, rank, init=None, max_outer_iters=10, max_iters=1000, atol=1e-3, verbose=False):
  """Return the low rank approximation of x assuming Poisson data

  Assume x_ij ~ Poisson(exp(eta_ij)), eta_ij = L_ik F_kj

  Maximize the log likelihood by using Taylor approximation to rewrite the
  problem as WLRA.

  This implementation supports early stopping by setting max_outer_iters.

  :param x: input data (n, p)
  :param rank: rank of the approximation
  :param max_outer_iters: maximum number of calls to WLRA
  :param max_iters: maximum number of EM iterations in WLRA
  :param verbose: print objective function updates

  :returns eta: low rank approximation (n, p)

  """
  n, p = x.shape
  if init is not None:
    eta = init
  else:
    eta = np.ones(x.shape) * np.log(x.mean())
  obj = pois_llik(x, eta).mean()
  if verbose:
    print(f'pois_lra [0]: {obj}')
  for i in range(max_outer_iters):
    lam = safe_exp(eta)
    w = lam
    target = eta + x / lam - 1
    if np.ma.is_masked(x):
      # Mark missing data with weight 0
      w *= (~x.mask).astype(float)
      # Now we can go ahead and fill in the missing values with something
      # computationally convenient, because the WLRA EM update will ignore the
      # value for weight zero.
      target = target.filled(0)
    eta1 = wlra(target, w, rank, max_iters=max_iters, atol=atol, verbose=verbose)
    update = pois_llik(x, eta1).mean()
    if verbose:
      print(f'pois_lra [{i + 1}]: {update}')
    if np.isclose(update, obj, atol=atol):
      return eta1
    else:
      eta = eta1
      obj = update
  return eta
