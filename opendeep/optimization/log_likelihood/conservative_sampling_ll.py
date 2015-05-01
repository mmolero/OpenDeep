'''
.. module:: conservative_sampling_ll

Implements the Conservative Sampling-based Log-likelihood estimator. This is useful for generative model comparison.
"Bounding the Test Log-Likelihood of Generative Models"
Yoshua Bengio, Li Yao, Kyunghyun Cho
http://arxiv.org/pdf/1311.6184v4.pdf
'''
__authors__ = "Markus Beissinger"
__copyright__ = "Copyright 2015, Vitruvian Science"
__credits__ = ["Li Yao, Markus Beissinger"]
__license__ = "Apache"
__maintainer__ = "OpenDeep"
__email__ = "opendeep-dev@googlegroups.com"

# standard libraries
import logging
import time
# third party
import numpy
import theano.tensor as T
# internal
from opendeep import function, as_floatX
from opendeep.utils.misc import make_time_units_string

log = logging.getLogger(__name__)


def log_sum_exp_theano(x, axis):
    max_x = T.max(x, axis)
    return max_x + T.log(T.sum(T.exp(x - T.shape_padright(max_x, 1)), axis))

"""
Conservative Sampling-based Log-likelihood estimator.

From Li Yao:
The idea of CSL is simple:
log p(x) = log Eh p(x|h) >= Eh log p(x|h) where h are sampled from GSN you have trained.

So when you have a trained GSN, p_theta (x|h) is parameterized by theta. So given one particular test example x0,
and sampled h, you can easily compute p_theta (x0|h).

In order for CSL to work well, samples of h must come from the true p(h).
However, this is never the case with limited number of h taken from a Markov chain.
What I did in the paper is to take one h every K steps. The assumption being made here is that samples
of h from higher layers mix much faster then x, which is what we usually observed in practice.
"""
def _compile_csl_fn():
    '''
    BUG HERE, not doing properly by chains (still has the bug, I don't see it)
    This is taking too much GPU mem

    mean: N(# of chains)*K(samples per chain)*D(data dim)
    minibatch: M(# of examples)*D (data dim)

    return: M * N matrix where each element is LL of one example against
    one chain.

    '''
    # when means is a 3D tensor (N, K, D)
    # When there are N chains, each chain having K samples of dimension D
    log.debug('building theano fn for Bernoulli CSL')
    means = T.tensor3('chains')
    minibatch = T.matrix('inputs')

    # how many chains CSL average over
    N = 5
    # minibatch size
    M = 10
    # data dim
    D = 784
    minibatch.tag.test_value = numpy.random.binomial(1, 0.5, size=(M, D)).astype('float32')
    # chain length
    K = 100
    means.tag.test_value = numpy.random.uniform(size=(N, K, D)).astype('float32')

    # computing LL

    # the length of each chain
    sample_size = means.shape[1]

    _minibatch = minibatch.dimshuffle(0, 'x', 'x', 1)
    _means = means.dimshuffle('x', 0, 1, 2)

    A = T.log(sample_size)
    B = _minibatch * T.log(_means) + (as_floatX(1) - _minibatch) * T.log(as_floatX(1) - _means)
    C = B.sum(axis=3)
    D = log_sum_exp_theano(C, axis=2)
    E = D - A
    # G = E.mean(axis=1)
    f = function(
        inputs=[minibatch, means],
        outputs=E,
        name='CSL_independent_bernoulli_fn'
    )

    return f


def _compile_csl_fn_v2(mu):
    '''
     mu is (N,D) numpy array
    p(x) = sum_h p(x|h)p(h) where p(x|h) is independent Bernoulli with
    a vector mu, mu_i for dim_i
    '''
    #
    log.debug('building theano fn for Bernoulli CSL')
    x = T.fmatrix('inputs')
    x.tag.test_value = numpy.random.uniform(size=(10, 784)).astype('float32')
    mu = numpy.clip(mu, 1e-10, (1 - (1e-5)))
    mu = mu[None, :, :]
    inner_1 = numpy.log(mu)
    inner_2 = numpy.log(numpy.float32(1) - mu)

    k = mu.shape[1]
    D = mu.shape[2]

    # there are two terms in the log(p(x|mu))

    term_1 = -T.log(k)
    c = T.sum(x.dimshuffle(0, 'x', 1) * inner_1 +
              (numpy.float32(1) - x.dimshuffle(0, 'x', 1)) * inner_2,
              axis=2)
    debug = c.sum(axis=1)
    term_2 = log_sum_exp_theano(c, axis=1)

    log_likelihood = term_1 + term_2
    f = function([x], log_likelihood, name='CSL_independent_bernoulli_fn')
    return f


def compute_CSL_with_minibatches_one_chain(fn, minibatches):
    LLs = []
    t = time.time()
    for i, minibatch in enumerate(minibatches):
        # loop through one minibatch
        LL = fn(minibatch)
        LLs.append(LL)
        mean = numpy.mean(LLs)
        log.info('%d  /  %d batches, LL mean so far %.4f' % (i + 1, minibatches.shape[0], mean))
    log.info('mean LL %s' % numpy.mean(LLs))
    log.info('--- took %s ---' % make_time_units_string(time.time() - t))


def compute_CSL_with_minibatches(fn, minibatches, chains):
    # fn is the compiled theano fn
    LLs = []
    t = time.time()
    for i, minibatch in enumerate(minibatches):
        # loop through one minibatch
        LL_minibatch_all_chains = []
        for chain_minibatch in chains:
            # loop through a minibatch of chains
            LL = fn(minibatch, chain_minibatch)
            LL_minibatch_all_chains.append(LL)
        LL_minibatch_all_chains = numpy.concatenate(LL_minibatch_all_chains, axis=1)
        # import ipdb; ipdb.set_trace()
        LLs.append(LL_minibatch_all_chains)
        mean = numpy.mean(LLs)
        log.info('%d  /  %d batches, LL mean so far %.4f' % (i + 1, minibatches.shape[0], mean))
    LLs = numpy.concatenate(LLs, axis=0)
    log.info('mean LL %s' % str(LLs.mean()))
    log.info('--- took %s ---' % make_time_units_string(time.time() - t))