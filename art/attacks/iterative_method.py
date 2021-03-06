# MIT License
#
# Copyright (C) IBM Corporation 2018
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import numpy as np

from art.attacks import FastGradientMethod
from art.utils import compute_success, get_labels_np_array

logger = logging.getLogger(__name__)


class BasicIterativeMethod(FastGradientMethod):
    """
    The Basic Iterative Method is the iterative version of FGM and FGSM.
    Paper link: https://arxiv.org/abs/1607.02533
    """
    attack_params = FastGradientMethod.attack_params + ['eps_step', 'max_iter', 'batch_size']

    def __init__(self, classifier, norm=np.inf, eps=.3, eps_step=0.1, max_iter=20, targeted=False, num_random_init=0,
                 batch_size=128):
        """
        Create a :class:`.BasicIterativeMethod` instance.

        :param classifier: A trained model.
        :type classifier: :class:`.Classifier`
        :param norm: Order of the norm. Possible values: np.inf, 1 or 2.
        :type norm: `int`
        :param eps: Maximum perturbation that the attacker can introduce.
        :type eps: `float`
        :param eps_step: Attack step size (input variation) at each iteration.
        :type eps_step: `float`
        :param max_iter: The maximum number of iterations.
        :type max_iter: `int`
        :param targeted: Should the attack target one specific class
        :type targeted: `bool`
        :param num_random_init: Number of random initialisations within the epsilon ball. For num_random_init=0
            starting at the original input.
        :type num_random_init: `int`
        :param batch_size: Batch size
        :type batch_size: `int`
        """
        super(BasicIterativeMethod, self).__init__(classifier, norm=norm, eps=eps, targeted=targeted,
                                                   num_random_init=num_random_init, batch_size=batch_size)

        if eps_step > eps:
            raise ValueError('The iteration step `eps_step` has to be smaller than the total attack `eps`.')
        self.eps_step = eps_step

        if max_iter <= 0:
            raise ValueError('The number of iterations `max_iter` has to be a positive integer.')
        self.max_iter = int(max_iter)

        self._project = False

    def generate(self, x, **kwargs):
        """
        Generate adversarial samples and return them in an array.

        :param x: An array with the original inputs.
        :type x: `np.ndarray`
        :param norm: Order of the norm. Possible values: np.inf, 1 or 2.
        :type norm: `int`
        :param eps: Maximum perturbation that the attacker can introduce.
        :type eps: `float`
        :param eps_step: Attack step size (input variation) at each iteration.
        :type eps_step: `float`
        :param y: The labels for the data `x`. Only provide this parameter if you'd like to use true
                  labels when crafting adversarial samples. Otherwise, model predictions are used as labels to avoid the
                  "label leaking" effect (explained in this paper: https://arxiv.org/abs/1611.01236). Default is `None`.
                  Labels should be one-hot-encoded.
        :type y: `np.ndarray`
        :param num_random_init: Number of random initialisations within the epsilon ball. For num_random_init=0
            starting at the original input.
        :type num_random_init: `int`
        :param batch_size: Batch size
        :type batch_size: `int`
        :return: An array holding the adversarial examples.
        :rtype: `np.ndarray`
        """
        from art.utils import projection

        self.set_params(**kwargs)

        if 'y' not in kwargs or kwargs[str('y')] is None:
            # Throw error if attack is targeted, but no targets are provided
            if self.targeted:
                raise ValueError('Target labels `y` need to be provided for a targeted attack.')

            # Use model predictions as correct outputs
            targets = get_labels_np_array(self.classifier.predict(x))
        else:
            targets = kwargs['y']

        adv_x_best = None
        rate_best = 0.0

        for i_random_init in range(max(1, self.num_random_init)):
            adv_x = x.copy()

            for i_max_iter in range(self.max_iter):

                adv_x = self._compute(adv_x, targets, self.eps, self.eps_step,
                                      self.num_random_init > 0 and i_max_iter == 0)

                if self._project:
                    noise = projection(adv_x - x, self.eps, self.norm)
                    adv_x = x + noise

            rate = 100 * compute_success(self.classifier, x, targets, adv_x, self.targeted)

            if rate > rate_best or adv_x_best is None:
                rate_best = rate
                adv_x_best = adv_x

        logger.info('Success rate of BIM attack: %.2f%%', rate_best)

        return adv_x_best

    def set_params(self, **kwargs):
        """
        Take in a dictionary of parameters and applies attack-specific checks before saving them as attributes.

        :param norm: Order of the norm. Possible values: np.inf, 1 or 2.
        :type norm: `int`
        :param eps: Maximum perturbation that the attacker can introduce.
        :type eps: `float`
        :param eps_step: Attack step size (input variation) at each iteration.
        :type eps_step: `float`
        :param num_random_init: Number of random initialisations within the epsilon ball. For num_random_init=0
            starting at the original input.
        :type num_random_init: `int`
        :param batch_size: Batch size
        :type batch_size: `int`
        """
        # Save attack-specific parameters
        super(BasicIterativeMethod, self).set_params(**kwargs)

        if self.eps_step > self.eps:
            raise ValueError('The iteration step `eps_step` has to be smaller than the total attack `eps`.')

        if self.max_iter <= 0:
            raise ValueError('The number of iterations `max_iter` has to be a positive integer.')

        return True
