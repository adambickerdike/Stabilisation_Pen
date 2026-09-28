"""A small Gaussian-process regressor in PyTorch (ARD squared-exponential kernel, linear mean, Gaussian noise),
fitted by maximising the log marginal likelihood with Adam.  Used for the drop-stress surrogate and for the
Bayesian-optimisation global check.  Predictions are differentiable with respect to the inputs."""
from __future__ import annotations

import math

import torch

DT = torch.float64


class GP:
    def __init__(self, Z, y, noise_floor=1e-6):
        self.Z = torch.as_tensor(Z, dtype=DT)
        self.y = torch.as_tensor(y, dtype=DT)
        n, d = self.Z.shape
        self.log_ls = torch.zeros(d, dtype=DT)
        self.log_sf = torch.tensor(math.log(max(float(self.y.std()), 1e-3)), dtype=DT)
        self.log_sn = torch.tensor(math.log(0.05 * max(float(self.y.std()), 1e-3)), dtype=DT)
        self.beta = torch.zeros(d + 1, dtype=DT)
        self.noise_floor = noise_floor

    @staticmethod
    def _A(Z):
        return torch.cat([torch.ones(Z.shape[:-1] + (1,), dtype=DT), Z], -1)

    def _K(self, Z1, Z2, log_ls, log_sf):
        ls = torch.exp(log_ls)
        d2 = (((Z1[:, None, :] - Z2[None, :, :]) / ls) ** 2).sum(-1)
        return torch.exp(2 * log_sf) * torch.exp(-0.5 * d2)

    def nll(self, log_ls, log_sf, log_sn, beta):
        n = self.Z.shape[0]
        K = self._K(self.Z, self.Z, log_ls, log_sf) + (torch.exp(2 * log_sn) + self.noise_floor) * torch.eye(n, dtype=DT)
        L = torch.linalg.cholesky(K)
        r = (self.y - self._A(self.Z) @ beta)[:, None]
        a = torch.cholesky_solve(r, L)
        return 0.5 * (r * a).sum() + torch.log(torch.diagonal(L)).sum() + 0.5 * n * math.log(2 * math.pi)

    def fit(self, iters=400, lr=0.05, verbose=False):
        A = self._A(self.Z)
        self.beta = torch.linalg.lstsq(A, self.y[:, None]).solution[:, 0]
        params = [p.clone().requires_grad_(True) for p in (self.log_ls, self.log_sf, self.log_sn, self.beta)]
        opt = torch.optim.Adam(params, lr=lr)
        for i in range(iters):
            opt.zero_grad()
            loss = self.nll(*params)
            loss.backward()
            opt.step()
            with torch.no_grad():
                params[0].clamp_(-4.0, 4.0)
                params[2].clamp_(-12.0, 2.0)
            if verbose and i % 100 == 0:
                print(i, float(loss))
        self.log_ls, self.log_sf, self.log_sn, self.beta = [p.detach() for p in params]
        self._cache()
        return self

    def _cache(self):
        n = self.Z.shape[0]
        K = self._K(self.Z, self.Z, self.log_ls, self.log_sf) + \
            (torch.exp(2 * self.log_sn) + self.noise_floor) * torch.eye(n, dtype=DT)
        self.L = torch.linalg.cholesky(K)
        r = (self.y - self._A(self.Z) @ self.beta)[:, None]
        self.alpha = torch.cholesky_solve(r, self.L)[:, 0]

    def predict(self, Zs, return_std=False):
        Zs = torch.as_tensor(Zs, dtype=DT)
        shp = Zs.shape[:-1]
        Zf = Zs.reshape(-1, Zs.shape[-1])
        Ks = self._K(Zf, self.Z, self.log_ls, self.log_sf)
        mu = self._A(Zf) @ self.beta + Ks @ self.alpha
        if not return_std:
            return mu.reshape(shp)
        v = torch.cholesky_solve(Ks.T, self.L)
        var = torch.exp(2 * self.log_sf) - (Ks * v.T).sum(-1)
        return mu.reshape(shp), torch.sqrt(torch.clamp(var, min=1e-12)).reshape(shp)

    def state(self):
        return {"Z": self.Z.tolist(), "y": self.y.tolist(), "log_ls": self.log_ls.tolist(), "log_sf": float(self.log_sf),
                "log_sn": float(self.log_sn), "beta": self.beta.tolist(), "noise_floor": self.noise_floor}

    @classmethod
    def from_state(cls, s):
        g = cls(s["Z"], s["y"], s.get("noise_floor", 1e-6))
        g.log_ls = torch.tensor(s["log_ls"], dtype=DT)
        g.log_sf = torch.tensor(s["log_sf"], dtype=DT)
        g.log_sn = torch.tensor(s["log_sn"], dtype=DT)
        g.beta = torch.tensor(s["beta"], dtype=DT)
        g._cache()
        return g
