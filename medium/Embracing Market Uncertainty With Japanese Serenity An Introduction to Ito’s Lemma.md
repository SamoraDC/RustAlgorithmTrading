Embracing Market Uncertainty With Japanese Serenity: An Introduction to Ito’s Lemma
Dimitrios Koulialias PhD
Dimitrios Koulialias PhD

Following
4 min read
·
Mar 24, 2025
13






In one of my previous stories (see link further below), I gave an overview on the stochastic nature of stock markets and provided an example in Python on how to simulate the evolution of a stock price Sₜ. The driving force behind this evolution is geometric Brownian Motion, that in its differential form writes as


where the greek letters μ and σ denote the average return (i.e., the drift) and the volatility, respectively. Moreover, {W(t) : t ≥ 0} is the notation for a Wiener process that is associated with the characteristics of a Brownian motion.

Riding the waves of randomness: using Brownian motion for stock price simulations in Python
Introduction
medium.com

In turn, I stated an explicit expression for Sₜ without going into the details. However, these are crucial for getting a deeper understanding on how to deal with the differentiation of stochastic process involving Brownian motion. This is where Ito’s Lemma comes into play.

Formulated by the Japanese mathematician Kyoshi Ito in 1951, this lemma can be considered as a cornerstone of modern financial mathematics, as well as many other areas associated with modeling under uncertainty. While there exist several versions of this lemma in the literature, here, I am presenting it in its simplest form based on the above stochastic differential equation for the stock price Sₜ

(Ito’s Lemma) Let g : R → R be a two-fold continuously differentiable function and let Sₜ further satisfy dSₜ = μSₜ dt + σSₜ dWₜ. Then:


Proof: Based on classic calculus, the change in g that occurs due to a small change dSₜ, can be written as a Taylor series:

Press enter or click to view image in full size

or equivalently, for the total differential dg = g(Sₜ + dSₜ) - g(Sₜ)


In contrast to classic calculus, where second order terms would be considered as negligible, this is no longer the case in stochastic calculus. Considering that dSₜ² is equal to dt (quadratic variation), this term should be also taken into account, whereas all other higher order terms vanish since: dt² = 0 and dSₜ * dt = 0. Given this, and plugging the above expression for dSₜ into the right-hand side of the equation, we get

Press enter or click to view image in full size

and by rearranging the terms for dt and dWₜ, we finally obtain

Press enter or click to view image in full size

Application of the lemma for calculating Sₜ
In the following, we will apply Ito’s Lemma for solving the differential equation in Sₜ. Since stock prices cannot attain negative values, we need to impose this constraint by applying the natural logarithm to the price beforehand, i.e., Xₜ = log(Sₜ), where in that case g(x) = log(x) for x > 0. Then, using Ito’s Lemma on g, and evaluating its derivatives, we have:

Press enter or click to view image in full size

By integrating the two terms in a time interval [0, T] and using W₀ = 0, we get


Finally, given that Sₜ = exp(Xₜ), with exp denoting the exponential function, the expression for Sₜ writes


which gives the expression of the stock price evolution associated with geometric Brownian motion.

Conclusion
In summary, it is almost impossible to imagine modern financial mathematics without the use of Ito’s lemma. Beyond the use presented here in the context of geometric Brownian motion, this lemma has also contributed to the development of various theoretical models, such as the one of Black-Scholes with regard to the price evolution of financial derivatives. Other fields also include stochastic portfolio theory, as well as the simulation of different economic conditions, to name a few. In retrospect, it is interesting to see how a mere extension of the chain rule to stochastic processes could have such a far-reaching impact.