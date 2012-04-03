from __future__ import division
import numpy as np
from numpy.random import random
from numpy import newaxis as na
import scipy.stats as stats
import scipy.linalg

# TODO write testing code for all these
# TODO write cholesky versions

### Sampling functions

def sample_discrete(foo,size=[]):
    assert (foo >=0).all()
    cumvals = np.cumsum(foo)
    return np.sum(random(size)[...,na] * cumvals[-1] > cumvals, axis=-1)

def sample_discrete_from_log(p_log):
    '''
    Goal: sample from a multinomial distribution (like sample_discrete)
    The input probability is in log.
    To avoid numerical issues by doing exp() directly on these log probabilities,
    find the maximum value first, and then subtract this maximum value
    from the probability array before doing exp()

    If p_log is two-dimensional, samples from normalized columns.
    '''
    # TODO can this be given a general axis argument in a clean way?
    if p_log.ndim == 1:
        return sample_discrete(np.exp(p_log - p_log.max()))
    elif p_log.ndim == 2:
        cumvals = np.exp(p_log - p_log.max(0)).cumsum(0)
        return np.sum(random(p_log.shape[1]) * cumvals[-1] > cumvals,axis=0)
    else:
        assert False

def sample_niw(mu,lmbda,kappa,nu):
    '''
    Returns a sample from the normal/inverse-wishart distribution, conjugate
    prior for (simultaneously) unknown mean and unknown covariance in a
    Gaussian likelihood model. Returns covariance.
    '''
    # code is based on Matlab's method
    # reference: p. 87 in Gelman's Bayesian Data Analysis

    # first sample Sigma ~ IW(lmbda^-1,nu)
    lmbda = sample_invwishart(lmbda,nu) # lmbda = np.linalg.inv(sample_wishart(np.linalg.inv(lmbda),nu))
    # then sample mu | Lambda ~ N(mu, Lambda/kappa)
    mu = np.random.multivariate_normal(mu,lmbda / kappa)

    return mu, lmbda

def sample_invwishart(lmbda,dof):
    # TODO make a version that returns the cholesky
    # TODO allow passing in chol/cholinv of matrix parameter lmbda
    n = lmbda.shape[0]
    chol = np.linalg.cholesky(lmbda)

    if (dof <= 81+n) and (dof == np.round(dof)):
        x = np.random.randn(dof,n)
    else:
        x = np.diag(np.sqrt(stats.chi2.rvs(dof-(np.arange(n)))))
        x[np.triu_indices_from(x,1)] = np.random.randn(n*(n-1)/2)
    R = np.linalg.qr(x,'r')
    T = scipy.linalg.solve_triangular(R.T,chol.T,lower=True).T
    return np.dot(T,T.T)

def sample_wishart(sigma, dof):
    '''
    Returns a sample from the Wishart distn, conjugate prior for precision matrices.
    '''

    n = sigma.shape[0]
    chol = np.linalg.cholesky(sigma)

    # use matlab's heuristic for choosing between the two different sampling schemes
    if (dof <= 81+n) and (dof == round(dof)):
        # direct
        X = np.dot(chol,np.random.normal(size=(n,dof)))
    else:
        A = np.diag(np.sqrt(np.random.chisquare(dof - np.arange(0,n),size=n)))
        A[np.tri(n,k=-1,dtype=bool)] = np.random.normal(size=(n*(n-1)/2.))
        X = np.dot(chol,A)

    return np.dot(X,X.T)

### Predictive

def scalar_t_loglike(y,mu,sigmasq,dof):
    temp = (y-mu)/sigmasq
    r = dof*1.0
    lPx = scipy.special.gammaln((r+1)/2)-scipy.special.gammaln(r/2)
    lPx -= 0.5*np.log(r*np.pi) + (r+1)/2*np.log(1+(temp**2)/r)
    return lPx - np.log(sigmasq)
    #return stats.t.logpdf(y,dof,loc=mu,scale=sigmasq)
    #return stats.t._logpdf((y-mu)/sigmasq,dof) - np.log(sigmasq)

def multivariate_t_loglik(y,nu,mu,lmbda):
    # returns the log value
    # TODO check... gelman says lmbda but emily says nulmbda
    d = len(mu)
    yc = np.array(y-mu,ndmin=2)
    return scipy.special.gammaln((nu+d)/2.) - scipy.special.gammaln(nu/2.) - (d/2.)*np.log(nu*np.pi) - (1./2.)*np.log(np.linalg.det(lmbda)) - (nu+d)/2.*np.log1p(1./nu*np.dot(yc,np.linalg.solve(lmbda,yc.T)).diagonal())

def beta_predictive(priorcounts,newcounts):
    prior_nsuc, prior_nfail = priorcounts
    nsuc, nfail = newcounts

    numer = scipy.special.gammaln(np.array([nsuc+prior_nsuc, nfail+prior_nfail, prior_nsuc+prior_nfail])).sum()
    denom = scipy.special.gammaln(np.array([prior_nsuc, prior_nfail, prior_nsuc+prior_nfail+nsuc+nfail])).sum()
    return numer - denom


