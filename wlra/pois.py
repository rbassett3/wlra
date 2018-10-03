import numpy as np
import torch

class PoissonFA(torch.nn.Module):
  """Poisson factor analysis via first order optimization"""
  def __init__(self, n_samples, n_features, n_components):
    """Initialize the loadings and factors. 

    The shapes need to be specified here to build the computation graph.

    :param n_samples: number of input samples
    :param n_features: number of input features
    :param n_components: rank of the factorization
    """
    super().__init__()
    self.l = torch.randn([n_samples, n_components], requires_grad=True)
    self.f = torch.randn([n_components, n_features], requires_grad=True)

  def forward(self, x):
    """Return the log likelihood of x assuming x_ij ~ Pois(exp(l_ik f_kj))"""
    log_lam = torch.matmul(self.l, self.f)
    return -torch.mean(x * log_lam - torch.exp(log_lam) + sp.gammaln(x + 1))

  def fit(self, x, max_epochs=1000, atol=1e-3, verbose=False, **kwargs):
    """Fit the model and return self.

    :param x: data (n_samples, n_features)
    :param max_epochs: maximum number of iterations of gradient descent
    :param verbose: print objective function updates
    :param atol: absolute tolerance for convergence
    :param **kwargs*: keyword arguments to torch.optim.Adam

    :returns: self

    """
    x = torch.tensor(x, dtype=torch.float)
    opt = torch.optim.Adam([self.l, self.f], **kwargs)
    self.obj = np.inf
    for i in range(max_epochs):
      opt.zero_grad()
      loss = self.forward(x)
      if verbose and not i % 100:
        print(f'Epoch {i} = {loss}')
      if np.isclose(loss, self.obj, atol=atol):
        return self
      else:
        self.obj = loss
        loss.backward()
        opt.step()
    return self
