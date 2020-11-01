---
title: The last long
tags: long
---

# Simulation's Configuration
Once the geometry is fixed and properly meshed, we need to choose our CFD model, initial and boundary conditions. 

The wind velocity range ([10-30] $m/s$) shows that flow is incompressible ($Ma\approx 0.1$). Also the airfoil and the cylinder chord (respectively $c=300 mm$ and $c=50 mm$)  and the air kinematic viscosity ($\nu =1.655 \times 10^{-5} m^2/s$ ) imply that the flow is in buffer/turbulent regime ($Re_A \approx 1.8-5.4 \times 10^{5}$ and $Re_C \approx 3.0-9.1 \times 10^{4}$). Also thanks to the experimental data, we are confident that the separation is common. This leads us to the use of the $k-\omega$ SST model.

<!--more-->

---
## Initial Conditions (`0/`)
Choosing a good initial condition (IC), helps for a faster convergence. Here I briefly discuss the how the initial conditions for each study are chosen.
### 1st Study
This is a steady-state simulation. initial conditions are computed/set in the following manner:
- $U$: all the boundaries and domain cells are initialised with the input velocity
- $p$: all the domain is initialised with a zero (gauge) pressure
- $k$: all the domain is initialised with a turbulence energy associated to a turbulence intensity $I$ which can be provided by the user
- $\omega$: all the domain is initialised with a turbulence omega associated to a turbulence kinetic energy $k$ and turbulence length scale $l$ which can be provided by the user
- $\epsilon$: dissipation rate is computed (for estimating the turbulent viscosity) according to the $k-\epsilon$ [model](https://www.openfoam.com/documentation/guides/latest/doc/guide-turbulence-ras-k-epsilon.html) 
$$\epsilon=C^{3/4}k^{1/2}/l$$
- $\nu_t$: all the domain is initialised with a turbulence omega associated with the $k-\omega$ [model](https://www.openfoam.com/documentation/guides/latest/doc/guide-turbulence-ras-k-omega-sst.html) according to 
$$\nu_t=Ck^2/\epsilon$$


### 2nd-4th Studies
We use the steady state solution of first study as the initial state for this time-dependent simulations.

### 3D case
It is computationally better to start the first study of a 3D simulation from the the steady-state solution of its corresponding 2D case. `mapField` utility of OpenFOAM (OF) is desingned for the similar purpose. It handels much more complex cases than our problem. Yet, the very same capability, makes is non-optimum for our problem. As the 3D problem is simply an extrution of the 2D case, one can perform the mapping in a much more simpler way and cheaper way. The `Mapper.py` script is a custom-made utility to take care of this.


## Boundary Conditions in OF
Before diving into the boundary conditions (BC) for each quantity it worth to review  the boundary conditions defined by `openFOAM` (OF).

### Basics
 In OF one can define the Dirichlet BC as `fixedValue`,  Neumann BC as `fixedGradient` or `zeroGradient` if the gradient is zero. Also for Robin BC, one can use the `mixed` type. 

### Inlet-Outlet 
For less simple cases that flow reversal might occur, OF provides an special form of boundary condition that **switches** between inflow and outflow based on the flux: `inletOutlet`([source code]([https://www.openfoam.com/documentation/guides/latest/api/classFoam_1_1inletOutletFvPatchField.html#details](https://www.openfoam.com/documentation/guides/latest/api/classFoam_1_1inletOutletFvPatchField.html#details))) and `outletInlet`([source code]([https://www.openfoam.com/documentation/guides/latest/api/classFoam_1_1outletInletFvPatchField.html](https://www.openfoam.com/documentation/guides/latest/api/classFoam_1_1outletInletFvPatchField.html))).

For an inlet patch, by using `outletInlet` one can specify the inlet `fixedValue` if the flux is inward. If not, it automatically changes to a `zeroGradient` . On an outlet patch, similarly, via `inletOutlet`, a `fixedValue` for the quantity can be specified if the flow is outward. Otherwise, OF sets a `zeroGradient` BC for the cell.

> - An easy way to remember the order is by looking at the capitalisation. The one which is capital, shows where the patch should be used. In fact, in OF, the last capitalised word of each BC class, specify its application.  For example `pressureDirectedInletOutletVelocity` is an inlet-outlet BC type suitable for *Outlet* patches and *Velocity* fields.
> - The mechanic of `inletOutlet` and `outletInlet` is such that at each time, each cell is either a Dirichlet or Neumann (with zero gradient) but the type might change as the simulation continues.

### Freestream type
Here I exclusively mean the `freestreamPressure` and `freestreamVelocity` BCs and NOT the `freestream` which is simply a wrapper around Inlet-Outlet. Unlike the Inlet-Outlet conditions, these two are real mixed (Robin) BC as the value of the patch is defined by

$$p = w.p_f+(1-w)p_c\ \ \ \ \ \ ; \ \ \ \ \ \ \ \ w(\phi) = \frac{1}{2}(1+\frac{\textbf{U}.\textbf{n}_f}{|| \textbf{U}||})$$

in which the subscript $f$ shows the *face* quantities and $c$ stands for the cell centre. In plain english, if the velocity is fully orthogonal to the patch and moving outward, then OF treats it as a Dirichlet BC. If, one the other hand, it's fully inward it will be treated as fully zero-gradient (face value is equal to the cell value). For the intermediate situation, OF **blends** the weights based on the flux. In particular, a flux of 0, is equivalent to averaging between the specified value on the face and the cell value.
> Compared to the inlet-Outlet type, this BCs do not undergo jumps after the flux changes sign. This intuitively helps to the solution stability specially for the transient problems that the value of BCs are not exactly known. On a steady-state problems, where a time independent values must be reached, the Inlet-Oulet type converges faster. For instance, for pressure, Inlet-Outpet discovers very soon that $p_f = p_c$  whereas this can take some iteration for a `freestreamPressure` .

### Physical variants
The basic and Inlet-Oulet types, can be applied on any parameter, scalar or vector. Yet, there are some possible physical variation on the BC which can be very well be combined with the two types above.
1. **Total Pressure**: A variant of pressure defined as $p = p_s -\frac{1}{2}\rho U^2$ with $p_s$ as the static or stagnation pressure (usually the pressure for the atmosphere at rest). It's obvious that to the pressure value now is linked to the value of the velocity on the patch. 
	Note that setting the total pressure on the boundaries, roughly speaking, is equivalent to setting the energy head (at least in the case of small viscosity and no rotation on the boundaries - which *might* be the case). In our application, which is dissipative, the injected energy from input will be dissipated and therefore, the outlet energy head is surely less then the ones of input. Yet, since the dynamics is not steady-state, one cannot associate a fixed energy head to the outlet boundaries. On the other hand, setting the total pressure on the boundaries (while not knowing the velocity) may cause energy inflow from the outlet which is again undesirable in our application.
2. **Component-wise Velocity**: In some cases it makes sense to set restriction on patch-normal, patch-tangent components of velocity. It's also might be the case that one needs to limit the normal or tangential component with respect to a predefined direction. Also, it is not uncommon to see the normal component is computed based on the mass rate or flux. 
	Indeed this requirements are needed in some of the turbomachinary applications, not ours.

### Turbulent BC
OF [provides]([https://www.openfoam.com/documentation/guides/latest/doc/guide-bcs-derived-inlet.html#sec-bcs-derived-inlet-turbulence](https://www.openfoam.com/documentation/guides/latest/doc/guide-bcs-derived-inlet.html#sec-bcs-derived-inlet-turbulence)) specific inlet-outlet boundary conditions for turbulent flows based on the $k-\omega$ and $k-\epsilon$ models. They instead of taking the values of $k, \omega$ and $\epsilon$, get the mixing length $l$ and the turbulent intensity $I$ and compute the values in a simllar fashion that I explained before on Initial condition. 
Apart from the ease in providing engineering guesses, these BCs are also convenient due to the fact that they remember the interconnection between the parameters and if one changes, the other one will chage accordingly. For instance, let's assume that we provide a time dependent input velocity and a constant input turbulent intensity and input mixing length. Without these boundary conditions, one has to also provide a time dependent BC for $k, \epsilon,$ and $\omega$. On the contrary, with the OF's turbulent BCs, nothing more than specifying the mixing length and intensity is needed. Everything will be performed under the hood. 
> The combination of this turbulent types and `freestream`(`Velocity/Pressure`) adds some non-physical arfacts. Therefore, despite their ease of use we  prevent ourself from using them.
> TODO: add the picture of arficat made by turb type BC

### Problem specific BC
There are also some boundary conditions developed for specific problems such as fans, rotating geometries, atmospheric boundary conditions, etc. We omit further explanation as it is not pertinent to our project.

## Boundary Conditions  (`0/` and `constant/polyMesh/boundary`)
Here I discuss the main ideas concerning the BC for a 2D case  At the end, the value of boundary conditions are given. For a 3D case, For a 3D case, it suffices to change the value of the `Front` and `Back` patches to `cyclic/slip/symmertyPlane` with a `value` equal to `$internalField` (usually only as a place-holder).

**Note**: The boundaries in the `0` and `constant` folders must be consistent otherwise the OF complains and wont run.

### 1st study
The first case is a steady-state simulation and therefore, all the BCs are fixed. The boundary conditions for the airfoil surface are obvious (no slip velocity and zero gradient pressure). They are less trivial for the turbulent parameters. Follwoing the tutorials, we cas use wall functions for $k, \nu_t$ and $\omega$. All these wall functions are eventually inherited from the `fixedValue` BC type of OF which requires a `value` entry (look at the [documentation for $\nu_t$](https://www.openfoam.com/documentation/guides/latest/doc/guide-bcs-wall-turbulence-nutWallFunction.html) for instace). Although it deons't play any physical role, I equate this `value`  to zero for first two empheaize on the laminar sub-layer over the airfoil. For $\omega$, I simply use the as the initial value. 

 For the far-field, however, I have decided to use Inlet-Oulet (in face `freestream`) for the sake of performance. The same applies to other boundaries but the `Airfoil`.

Again note that an equivalent approach for the turbulence variables is using `turbulentIntensityKineticEnergyInlet, turbulentMixingLengthDissipationRateInlet` at inlet which I avoided because of the artifact they indeuce.

### 2nd study
The airfoil is pitching now. This means a moving wall BC on the airfoil. Also I'll relax the far-field boundary conditions to the  `freestreamPressure/Velocity`.  Since the simulation is transient, any sudden jump induced by the flux after changing its direction at boundary patches produces artificial waves that translate into the domain. As an extreme example, on can think of fixing the values on the boundary and propagating a wave inside the domain. As the wave reaches to the boundaries, it will be reflected in a similar way a wave in a rope with a fixed end will be reflected back. The main challenge is tuning the far-field BCs against the spurious reflecting waves that propagate back to the boundary (look at [here](ETH_review) for instance for some exact treatments for simple problems). This is usually solved approximately and through a hybrid modification of geometry (at far field), initial and bounday conditions Using the blending technique and a CH domain structure one can alleviate this. 

In principle this argument applies also on the turbulent variables at the boundary. Yet, as OF doesn't have this blending feature for the turbulent variables I keep using the previous ones which are inlet-oulet based and induce spurious reflecting waves.

>**Recommendation**:  As $k$ and $\omega$ are both scalar, one can inherit from the `freestreamPressure` and make a custom boundary layer that blends these two too.


### 3rd study
The convinience of `freestreamPressure/Velocity` is even more pronounced in the 3rd case with time-dependent and periodic boundary condition. Apart from the spurious reflections, yet, it is of high importance to have a proper model for the time-varying input. 

One can in principle apply the periodic BC either on velocity or pressure. In open air, the gust is caused by the pressure difference. Yet, it is much easier to synthesise a *neat* boundary condition (for academic purposes) on the velocity using a sinusoidal model at the inlet patches

$$\textbf{U}_f =\textbf{U}_0 + \textbf{U}_1 \sin (\omega_U t)$$

We can think of this velocity field being produced by an pressure gradient very far from the airfoil and the computational domain (such that the effects are being observed as plane waves). As these pressure and velocity wave fronts are planar, not every face on the inlet face senses them at the same time. In other words, there is a time lag caused by spacial separation of the inlet cells on the inlet patch.

I model this time lag as bellow:

$$\textbf{U}_f =\textbf{U}_0 + \textbf{U}_1 \sin (\omega_U \tilde t)\\
\tilde t = \max(0, t-\frac{\Delta\textbf{r}.\textbf{n}}{c})\\
\Delta\textbf{r} = \textbf{r}_f -\textbf{r}_*$$

in which $\textbf{r}_f$ is the location of the input face, $\textbf{r}_*$ is the location of the point on the computational domain that feels the incoming wave first, and $\textbf{n}$ stands for the direction of propagation of the wave. $c$ is the *wave speed* outside the computational domain which I set it to be the sound speed in the air.

**Note**: This model, implicitly is assuming that our computational and incompressible domain over which we solve naiver-stokes, is surrounded by a larger domain governed by a wave-equation, which immediately means 1. compressibility and 2. non-viscosity, both of which are different from the our assumptions in computational domain.  

>TODO: add the picture of domains.

### 4th study
It is simply the combination of the BC of the third and second cases. 


## Discretization (`system/fvSchemes`)
There is no general discretization scheme that works fine for all cases. Yet, The following seem to be rebust and accurate enough. It's mostly based on the [A Crash introduction on Finite Volume Method]() by Wolf Dynamics (WD) . The details of methods are in [Prof. Jasak's thesis]().[Fluid Mechanics 101]() youtube channel also have summerzied these in a few video.

### `ddtSchemes` 
I use (implicit) `Euler` for transient and `steadyState` for the fixed-IC/BC simulation.


### `gradSchemes`
As explainedin [ANSYS doc](https://www.afs.enea.it/project/neptunius/docs/fluent/html/th/node369.htm) *gradient limiting* is a technique to "*to invoke and enforce the monotonicity principle by prohibiting the linearly reconstructed field variable on the cell faces to exceed the maximum or minimum values of the neighboring cells*" and in consequence "*prevent spurious oscillations, which would otherwise appear in the solution flow field near shocks, discontinuities, or near rapid local changes in the flow field*".

I used a blending factor of 0.5 based on the following remarks of WD:
> Gradient limiters increase the stability of the method but add diffusion due to clipping.
> All of the gradient discretization schemes are at least second order accurate.
> If you set the blending factor to 0.5, you get the best of both worlds (accuracy and stability)

Also given the fact that for the in different direction the gradient (absolute) value has diffent scale (alongside the airfoil and prependicular), it makes more sense to use a multi-directional limiter. I used therefore `cellMDLimited Gauss linear 0.5`.

### `divSchemes`
For the convection term, it's important to have upwind. upwind is enough for rans. later for DES/transient we limit the grads. 

 [this](https://youtu.be/JVE0fNkc540?t=1568) video. 


### `laplacianSchemes` and `snGradSchemes`
>TODO: WHY? more understanding of what its doing

Our mesh is not (fully) structured and non-orthogonalities exist. Also we have grading in the mesh. So we can iether use  `corrected` or `limited` for surface normal gradients discretization. WD recommends that:

> For meshes with non-orthogonality less than 75, you can set the blending factor to 1.

Our mesh quality is high, with the maximum non-orthogonality of less than 50 degree. Therefore, I used a blending factor of 1. 


Note that the `snGradSchemes` must be consistent with the laplacian scheme. Therefore, a `limited corrected 1` is also apllied on surface normal gradient scheme.



## Convergence criteria (`system/fvSolutions`)
Here I present a aualitative approach to estimate a good stopping tolerance for the solver and the simulation. With a coarse mesh, it is impossible to resolve good resolution in the fluid field. As the mesh becomes finer, more and more structure will be resolved and therefore, lower convergence tolerance becomes necessary. This decraese in minimum meaningfull level of tolerance, however, reaches a plateau in a very fine meshes due to the numerical round-off errors. Before hitting this pateau, I estimate the best feasible tolerances (small enough for gaining accuracy and large enought to be computationally cheap) based on the following principle:

**For a steady-state solution the errors in qunatities shouldn't be convected to other cells. For a transient simulation, the criteria must be tighter than a steady-state.**

Let's see what does it mean in action. In a steady-state simulation, despite the lack of any dynamics, one can build the following time scale between two successive iteration in the solution:

$$\tilde t \sim U/c$$

 I denote the minimum characteristic mesh size as $L$ and use $\delta$ for the error (simulation - exact) in each qunatity.  The error $\delta U$ in each iteration shouldn't leave the cell. This means:

$$L \ge \delta U \tilde t = c\delta U/U  \rightarrow \Big|\frac{\delta U}{U}\Big| \le \Big|\frac{L}{c} \Big|$$

And recall that OpenFOAM computes the residuals based on the following form:

$$r = \frac{|| A  q -  b ||}{|| b||}=\frac{|| A  q -  A q_* ||}{|| A q_*||} = \frac{|| A(q - q_*) ||}{|| A q_*||}$$

in which $ A$ and $ b$ characterize the lienarized system of equation to be solved for qunatity $ q$ with the exact solution of $ q_*$. It's evident that if $\kappa_A =\lambda_{max} / \lambda_{min}$, then,

 $$ \frac{1}{\kappa_A} \Big|\Big|\frac{\delta  q}{ q} \Big|\Big| \le r \le \kappa_A \Big|\Big|\frac{\delta  q}{ q} \Big|\Big|.$$

If the system of equations we solve are well-posed and easily-invertible, then the $\kappa_A$ becomes small as the numerical solution tends to the exact solution. This means that to reach the our desired goal (preventing convection of errors whithin the cells), we can set  

$$r_U<|L/c|$$

and **expect that the solver to be able to reach that relative error**. Of course, there's no problem in setting larter relative errors as the stopping creteria except giving away the accesible accuracy that might be of need, in later steps or in the transient simulation. 

For the pressure (over density), we have $k \sim p/\rho \sim 0.5U^2$. Therefore, similarly we have:

$$r_k = r_p<2|\delta U/U| = 2|L/c|$$

Also since $\omega \sim 1/\tilde t=U/c$ we have:
$$r_{\omega}<|\delta U/U| = |L/c|$$

It's worse to mention that pressure equation is the stiffest equation among the others. Therefore, it's important to set it's tolerance low enough to capture the solution but high enough to lower down the computational cost. Solving others is relatively cheap.

>TODO: explain more


## Post-processing (`system/controlDict`)



# Setting: BC

#### Velocity $U$
If `internalField`  is the inlet (and initial) value of velocity vector, then the boundary conditions are based on the following table.
| Patch Name | type | value | freestreamValue
|--|--|--|--|
| `Front` | empty| |  |
| `Back` | empty | |  |
| `Inlet` | freestream 	| internalField | internalField |
| `Outlet` | freestream | internalField| internalField |
| `Top` | freestream 	| internalField | internalField |
| `Bottom` | freestream | internalField | internalField |
| `Airfoil` | movingWallVelocity| uniform (0 0 0)|  |
| `AMI1/AMI2` | cyclicAMI| internalField|  |


#### Pressure $p$
If  the scalar `internalField`  is the gauge pressure, then the boundary conditions are based on the following table.
| Patch Name | type | value | freestreamValue
|--|--|--|--|
| `Front` | empty| |  |
| `Back` | empty | |  |
| `Inlet` | freestream 	| internalField | internalField |
| `Outlet` | freestream | internalField| internalField |
| `Top` | freestream| internalField | internalField |
| `Bottom` | freestream | internalField | internalField |
| `Airfoil` | zeroGradient| |  |
| `AMI1/AMI2` | cyclicAMI| internalField|  |

#### Turbulent Kinetic Energy $k$
If  the scalar `internalField`  is the initial kinetic energy, then the boundary conditions are based on the following table.

| Patch Name | type | value | freestreamValue
|--|--|--|--|
| `Front` | empty| |  |
| `Back` | empty | |  |
| `Inlet` | freestream 	| internalField | internalField |
| `Outlet` | freestream | internalField| internalField |
| `Top` | freestream 	| internalField | internalField |
| `Bottom` | freestream | internalField | internalField |
| `Airfoil` | kqRWallFunction| uniform 0 |  |
| `AMI1/AMI2` | cyclicAMI| internalField|  |

#### Turbulent Vorticity $\omega$
If  the scalar `internalField`  is the initial vorticity, then the boundary conditions are based on the following table.

| Patch Name | type | value | freestreamValue
|--|--|--|--|
| `Front` | empty| |  |
| `Back` | empty | |  |
| `Inlet` | freestream 	| internalField | internalField |
| `Outlet` | freestream | internalField| internalField |
| `Top` | freestream 	| internalField | internalField |
| `Bottom` | freestream | internalField | internalField |
| `Airfoil` | omegaWallFunction| internalField |  |
| `AMI1/AMI2` | cyclicAMI| internalField|  |

#### Turbulent Viscosity $\nu_t$
If  the scalar `internalField`  is the initial turbulent vorticity energy, then the boundary conditions are based on the following table.

| Patch Name | type | value | freestreamValue
|--|--|--|--|
| `Front` | empty| |  |
| `Back` | empty | |  |
| `Inlet` | freestream 	| internalField | internalField |
| `Outlet` | freestream | internalField| internalField |
| `Top` | freestream 	| internalField | internalField |
| `Bottom` | freestream | internalField | internalField |
| `Airfoil` | nutkWallFunction| uniform 0 |  |
| `AMI1/AMI2` | cyclicAMI| internalField|  |


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


# References


# Appendix

## CaseMaker Example
Here, I discuss the best usage of the `CaseMaker` class. The prerequisites is a compiled mesh with the `.msh` format. In this example, I have compiled a 2D and a 3D mesh, both named AX2. (Airfoil geometry with 2 level of refinement). 

**Note**: As we will use both `python` and `openFoam` environments, it's better to start both environments side-by-side. If you are on the cluster, it is possible to have both in the same shell by sourcing OF and loading `cray-python` module. 

Here is the recipe:
  
- **Making OpenFoam-Friendly mesh** We need the content of `mesh_generator` folder. Here since I have 2 meshes, I duplicated the content of `/mesh_generator` in  `mesh_generator/2d/` and `mesh_generator/3d/`. The corresponding mesh files are also placed inside these sub-directories. 

- **`gmsh2Foam`**: Navigate to the directory in which the `.msh` files are located (in both python and OF environments). Execute `gmshTofoam` in the OF environment and wait till it finishes. The highlighted warning in figure (?) can be ignored safely.
**Note**: On the cluster, this might break! Do it locally.

>TODO: Pics 2,3


- **Correcting the patches**: Now we have to correct the patch types. In the python evnironment, execute `python patch_corrector.py <is_3d>` in whcih `<is_3d>` is a bool argument that indicated the geometry. Note that it has to respect python's grammar, (either `True` or `False` not `true`/`false`). If the mesh is 2D, the `Front` and `Back` patches will be set as `empty` type and `cyclic` otherwise. 

>TODO: pic 4

- **`AllMesh`**: Because of the existance of a rotating region, we need to baffle the mesh and then split the duplicate points. The`AllMesh` utility does that. It furthermore executes `renumberMesh` to reduce the bandwith of the adjacency matrix. Now the mesh is ready-to-use by OF.

>TODO: pic 5

**NOTE**: This utility, in fact can encompass the previous two steps. Because of the `gmsh2foam` error on the cluster, we have to perform the last two steps seperately (look at the commented parts on the `AllMesh`).

**NOTE**: The previous steps were perfomed for 2D mesh. In 3D, we get additional warnings which are also safe to ignore.

>TODO: pic 7,8


- **Making Case files**: In the python environment, navigate to the `CaseMaker` directory. Enter python and import the CaseMaker class by `from CaseMaker import *`. Now you have access to a high-level and flexible class that makes all the case files with your desired setting. It's very important to read exactly the `CaseMaker`'s doc (you can do it by tab in `IPython`) and understand the proper setting. This class is well documented and one can understand the functionality of each part by reading the doc strings in the beginning of each module. The output of `CaseMaker` is a folder with proper sub-directories named based on geometry and level of mesh refinement. 

In this example, I made a 2D case in RANS and a 3D DES model. Note the directory and the corresponding files in each case (2D RANS on left and 3D DES on right).

>TODO: pic 9-13

## Mapper Example
To use `Mapper` one has to prepare a 2D case as well as a 3D one whose mesh is simply a extruded version of the 2D mesh (otherwise chaos happens!). The preassumation is that a 2D steady-state simulation is already performed. 

Let's say we are in `./` which contains the `AX0_2d` and `AX0_3d` directories, `AllMap` executor and `Mapper.py` script. Also, let's assume the 2D case is located in `.../AX0_2d/study1/` and the 3D one in `.../AX0_3d/study1/`. Since the 2D simulation is finished the content of the two folders are same as the picture below:
>TODO: pci 14

The Mapping will be done by giving the address of 2D and 3D cases to the executor:

`./AllMap ./AX0_2d/study1/ ./AX0_3d/study1/`

It extracts the center of cells in 2D and 3D cases, and assigns the field values of the 3D case based on the (x,y) components. It also forces the velocity in z-direction to 0 (from machine epsilon). 

**Note**: If you intend to have another BC than `cyclic` for the `Back` and `Front` patches in 3D case, give it as the third argument to the `AllMap` like: `./AllMap ./AX0_2d/study1/ ./AX0_3d/study1/ 'symmetryPlane'`.

**Note**: To retrive the field values fast, I save them in dictionaries. This means that the keys - the (x,y) component of the cells' locations- must be precisely saved for a correect retrival of the field value. However, due to the round-off errors in computing the cell centeres, full accuracy is impossible. Hence, some keys will be currupted and information will be lost. In a somewhat interesting procedure, one can prove that this cannot happen more than 20% of the cases. Additionally, with a simple treatment, I have lowered this number down to less than 2%. In practice, in less than 0.1% of the cases this key corruption won't be handled correctly and even in these cases, one can subtitude the field values with a very good educational guess. Look at the comments in the `Mapper.py` for the details.
