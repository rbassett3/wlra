import numpy as np
import pytest
import sklearn.decomposition as skd
import wlra

def test_wlra_shape():
  x = np.zeros((100, 200))
  w = np.ones((100, 200))
  res = wlra.wlra(x, w, rank=1)
  assert res.shape == (100, 200)

def test_wlra_unit_weight():
  np.random.seed(0)
  x = np.random.normal(size=(100, 200))
  res = wlra.wlra(x, w=1, rank=1)
  u0, d0, v0 = skd.PCA(n_components=1)._fit(x)
  res0 = np.einsum('ij,j,jk->ik', u0, d0, v0)
  assert np.isclose(res, res0).all()

def test_wlra_rank_2():
  np.random.seed(0)
  x = np.random.normal(size=(100, 200))
  res = wlra.wlra(x, w=1, rank=2)
  u0, d0, v0 = skd.PCA(n_components=2)._fit(x)
  res0 = np.einsum('ij,j,jk->ik', u0, d0, v0)
  assert np.isclose(res, res0).all()

def test_pois_lra_shape():
  x = np.zeros((100, 200))
  res = wlra.pois_lra(x, 1, verbose=True)
  assert res.shape == (100, 200)