---
title: Another long
tags: long
excerpt: true
article_type: normal
show_excerpt: true
---
Hello. I try to be excerpt.
<!--more-->

# Sense-dynamics: Drone navigation project

This report outlines the progress I had at MCSS on the project starting from March 2020 
till the end of August 2020. The outputs are uploaded in a [gitlab repository](https://gitlab.epfl.ch/sense-dynamics-collaboration/cfd-simulation)
and are accessible to the internal user of EPFL through their Gaspar credentials. 

# Non-dimensional Similarities
The equations we solve are [[OF doc](https://www.openfoam.com/documentation/guides/latest/doc/guide-turbulence-ras-k-omega-sst.html)), [NASA_page](https://turbmodels.larc.nasa.gov/sst.html), [paper](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.460.2814&rep=rep1&type=pdf) ]:

$$ \partial  U/\partial t + \textbf{U} . \nabla \textbf{U} = -\nabla p/\rho + \nu \nabla^2 \textbf{U} \\
 \nabla. \textbf{U}= 0\\
\partial k/\partial t + \textbf{U} . \nabla k = \tilde P_k - \beta^* k\omega + \nabla.[(\nu + \sigma_k \nu_T) \nabla k]\\
\partial \omega/\partial t + \textbf{U} . \nabla  \omega = \alpha \tilde P_k / \nu_t - \beta \omega ^2+ \nabla.[(\nu + \sigma_{\omega} \nu_T) \nabla \omega] + 2(1-F_1) \frac{\sigma_{\omega2}}{\omega} \nabla k . \nabla \omega$$

in which (using the Einstien summation rule and $\partial/\partial x_i := \partial_i$) 
$$\tilde P_k = \min \{P_k, 10 \beta^* k \omega\} \hspace{1cm} P_k = \nu_t \partial_jU_i(\partial_iU_j + \partial_jU_i)\\
S = \sqrt{2S_{ij} S_{ij}} \hspace{2cm} S_{ij} = \partial_jU_i + \partial_i U_j\\
\nu_t = \frac{a_1k}{\max(a_1\omega, F_2S)}$$

and the following variables are non-dimentional parameters that are either fixed or updated on-the-fly:

- $0 \le F_1, F_2 \le 1$: adaptively updated at each iteration
- $\beta^*, a_1, \sigma_{w2}$: constant
- $\alpha, \beta, \sigma_k, \sigma_{\omega}$: adaptively updated at each iteration based on the value of $F_1$ 

The boundary conditions can be expressed as following. If if we partition the boundairy of the domain $\Omega$ as the union of the boundary on the airfoil, far-field and the inlet 
$$\partial \Omega = \partial_A \Omega \cup \partial_{ff} \Omega \cup \partial_{I} \Omega$$
then:

$${U}\Big|_{ \partial_A \Omega}= U_{Airfoil} \hspace{2cm} {U}\Big|_{\partial_{ff} \Omega} = {U}\Big|_{\partial_{I} \Omega}\hspace{2cm}{U}\Big|_{\partial_{I} \Omega} = B_U \\
\nabla p\Big|_{ \partial_A \Omega}=0\hspace{2.7cm} p\Big|_{\partial_{ff} \Omega} = p\Big|_{\partial_{I} \Omega}\hspace{2cm}p\Big|_{\partial_{I} \Omega} = 0\\
k\Big|_{ \partial_A \Omega}=k_{wall\  k-\omega}\hspace{2cm} k\Big|_{\partial_{ff} \Omega} =k\Big|_{\partial_{I} \Omega}\hspace{2cm}k\Big|_{\partial_{I} \Omega} = \frac{3}{2}I_{turb}| U_0|^2\\
\omega\Big|_{ \partial_A \Omega}=\omega_{wall\  k-\omega}\hspace{2cm} \omega\Big|_{\partial_{ff} \Omega} = \omega\Big|_{\partial_{I} \Omega}\hspace{2cm}\omega\Big|_{\partial_{I} \Omega} = \sqrt{\frac{k\big|_{\partial_{I} \Omega}}{\sqrt {0.09}c^2}}\\
\nu_t\Big|_{ \partial_A \Omega}=\nu _{t, wall\  k-\omega} \hspace{2cm} \nu_t\Big|_{\partial_{ff} \Omega} = \nu_t\Big|_{\partial_{I} \Omega}\hspace{2cm}\nu_t\Big|_{\partial_{I} \Omega} = 0.09^{1/4}c\sqrt {k\big|_{\partial_{I} \Omega}}\\
$$ 
The Airfoil moves. Also the input is time-dependent. So, using the same notation introduced in the begining, we can parametrize the boundary condition variation as: 

$$\partial_A \Omega = B_A(t; \alpha_0, \alpha_1, f_{\alpha})\\
B_U= B_U( r, t; | U_0|, | U_1|, f_g)$$

Therefore, the solution $\mathcal S$ is a function of all these parameters $( U_0,  U_1, \alpha_0 \alpha_1, f_\alpha, f_g, \nu)$. To ellaborate more clearly the dependence of the solution and the parameter space, one can non-dimentionalize the (possibly vectorial) variable $ q$ based on the scaling transformaiton $ q' =  q / z_q$ and rewite the equations above. I define the following scaling factors:

$$z_U = U_0 \hspace{1cm} z_r =  c \hspace{1cm} z_t = c/U_0\\
  z_{\omega} = 1/z_t \hspace{1cm} z_k = U_0^2 \hspace{1cm} z_P = \rho U^2_0$$

by which one drive the following identities:

$$\nabla = \nabla'/z_r\hspace{1cm} \tilde P'_k = \tilde P_k z_k z_\omega \hspace{1cm}S = S'z_\omega$$

that all together read:

$$ \partial'  U'/\partial t' + \textbf{U}' . \nabla' \textbf{U}' = -\nabla' p' + \frac{1}{Re} \nabla^2 \textbf{U}'\\
 \nabla'. \textbf{U}'= 0\\
\partial k'/\partial t' + \textbf{U}' . \nabla' k' = \tilde P_k' - \beta^* k'\omega' + \frac{1}{Re}(1+ Re.\sigma_k.M) \nabla'^2 k'\\
\partial \omega'/\partial t' + \textbf{U}' . \nabla ' \omega' = \alpha \tilde P_k' /M- \beta \omega'^2+ \frac{1}{Re}(1+Re.\sigma_{\omega}.M)\nabla'^2\omega' + 2(1-F_1) \sigma_{\omega2} \frac{\nabla' k' . \nabla' \omega'}{\omega'}$$

with $M$ defined as:

$$M:=\frac{k' \omega'^{-1}}{\max(1,F_2S'/a_1 \omega')}$$

for convinience in notation. The boundary conditions can be similarly scaled. Note that in the (dimension-less) governing equations, when it comes to the problem's parameters, it is only the Reynolds number $Re=\frac{\rho U c}{\mu}=\frac{ U c}{\nu}$ - a specific combination - that plays a role. Density, chord length, inlet velocity and the other parameters do not apear - if they apear at all - in the eqautions independently. This means, for example, the normalized solution $\mathcal S'$, won't be affected if both inlet velocity and viscosity double.
Indeed, the boundary conditions also affect the solution and it's imporant to investigate their parametrization form too. Both inlet velocity and angle of attack undergo a 

Since it is always possible to remap the non-dimensional solution to the physical one, given the parametrization of the boundary conditions (and most imprantly the sinusoidal variation which can be easily describled by its mean value, amplitude and frequency. Equivalently, one can express these changes in a non-dimensionalized manner by scaling the mean and amplitude by the corrisponding $z$ and frequency by $1/z_t$. 

As it is always possible to map back the non-dimensional solution to its physical counterpart, based on the studies configuration, one can clame - by assuming the uniqueness of solution if it exists - that the solution of one can be expressed as:
-  $\mathcal S_1 = \mathcal S_1(Re, \alpha_0)$
- $\mathcal S_2 = \mathcal S_2(Re, \alpha_0, \alpha_1, \frac{f_{\alpha}c}{U_0})$
- $\mathcal S_3 = \mathcal S_3(Re, \alpha_0, \frac{U_1}{U_0}, \frac{f_{g}c}{U_0} )$
- $\mathcal S_4 = \mathcal S_4(Re,  \alpha_0, \alpha_1, \frac{U_1}{U_0}, \frac{f_{\alpha}c}{U_0}, \frac{f_{g}c}{U_0} )$

which in turn implies that 
- Exploring the solution space of study 1 requres only samples from different angle of attacks and different $Re$s.
- Exploring the solution space of study 2 requres only samples from different mean angle of attacks, different pitching amplitude and frequency as well as different $Re$s.
- Exploring the solution space of study 3 requres only samples from different mean inlet velocity, different gust amplitude and frequency as well as different $Re$s
- Finally, for exploring the solution space of study 4, sampling must be done over all the previous parameters.

# Sampling
The previous section suggest a natural hierarchical samling strategy: *Use the samples of previous study for the next study.* Let's say for study 1, we sample $N_1$ pairs of $(Re, \alpha_0)$. For the second study, we use the same sample set and augment it with $N_2$ pairs of $(\alpha_1, \frac{f_{\alpha}c}{U_0})$. In a similiar fashion, we can construct the parameters of the third study by adding the $N_1$ pairs of study 1 with $N_3$ sample pairs of $(\frac{U_1}{U_0}, \frac{f_{g}c}{U_0})$. Finally, for study 4, we can use all these samples (no additional sampling) and build our configuration (initial/boundary condition and material properties).

This method is computationally desireable. As we initialize of each transient study from its steady-state solution which is basically the solution of a case under the 1st study, using different sample points means extra steady-state simulations. This step may be prevented by using this hierarchical samling strategy.

The total number of cases is therefore equal to 
$$N_{tot} = N_1 + N_1 N_2 + N_1 N_3 + N_1 N_2 N_3 $$


# Uncertainty Quantification
MC vs DES

# Simulaiton Validation
asd
