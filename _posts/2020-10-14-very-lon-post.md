---
title: Obi-One Kenobi
key: obiwan
permalink: /page/obione.html
tags: long
---

# Sense-dynamics: Drone navigation project

This report outlines the progress I had at MCSS on the project starting from March 2020 
till the end of August 2020. The outputs are uploaded in a [gitlab repository](https://gitlab.epfl.ch/sense-dynamics-collaboration/cfd-simulation)
and are accessible to the internal user of EPFL through their Gaspar credentials. 

<!--more-->

---

## Main Goal
The goal is to set up a CFD configuration and simulate the flow time evolution and build a 
proper database for training a machine learning (ML) algorithm or any other analysis. To begin, we simplify the problem to 2D simulating an airfoil rather than the whole drone.
Indeed, this simulation must be validated first with experimental results.

There are four different configurations that has to be studied:

1. A non-pitching airfoil in the constant velocity field
2. A (harmonic) pitching airfoil in the constant velocity field
3. A non-pitching airfoil in the harmonic velocity field
4. A (harmonic) pitching airfoil in the harmonic velocity field

The configuration space consists of 6 parameters (the geometry is constant): 

- $U_0$: mean velocity field
- $U_1$: amplitude of velocity field (or the *gust intensity*)
- $f_g$:  frequency of the harmonic velocity field (or *gust velocity*)
- $\alpha_0$: mean angle of attack
- $\alpha_1$: amplitude of angle of attack (or the *pitching amplitude*)
- $f_{\alpha}$:  pitching frequency of the airfoil

Note some of the four studies above impose specific value to some of the parameters, i.e.,  the steady-state case in study 1 means all the frequencies and amplitudes are zero. 


## Quantities of Interest
We are trying to capture the following quantities:

1. Aerodynamic coefficients: $C_l,  C_d$, and  $C_m$ (lift, drag and pitching moment)
2. pressure coefficients on the wing surface: $C_p$ (grid size resolution)
3. leading edge stagnation point
4. Velocity field over a certain field of view with some spatial resolution and temporal step. 
 
 look at [List of Outputs](https://gitlab.epfl.ch/sense-dynamics-collaboration/cfd-simulation/-/blob/master/Experimental_Results/OutputListAndCorrectedData.txt) for more info or contact [Guosheng He](https://people.epfl.ch/guosheng.he) from the [UNFoLD](https://www.epfl.ch/labs/unfold/) group.

## Experimental Data
We already have the experimental data from an experiment done by UNFoLD group using a pitching NACA0015 airfoil associated to study 1 and 2. The raw, as well as the processed data, are available (have a look at [VariableDescription.txt](...) for the details). Another series of experiments on a cylindrical geometry is also planned and we expect to receive its results in the near future (contact [Iordan Doytchinov](https://people.epfl.ch/iordan.doytchinov?lang=en)  who is leading the project too).
 

# Softwares and Infrastructure
We used the following systems and HPC facilities:

- Local Machine (MATHCSE computer) - no HPC
- [SCITAS](https://www.epfl.ch/research/facilities/scitas/) - helvetios and fidis clusters
- [CSCS](https://www.cscs.ch/) - daint cluster

as well as the following open-source softwares:

- gmsh (v4.6.0)
- [openfoam.com](https://www.openfoam.com/) distribution of openFOAM v1812 (on SCITAS), v1912 (on the Local Machine nad MATHCSE), and v2006 (on CSCS) 
- python (+3.5)

# The Structrue of Report
I discuss the deatails of meshing, case setup (and the utilities I made), and the postprocessing. Also I comment on the sampling method and it's relateion with the postptocessing. 

For a step-by-step desciption of case construction, look at the appendix.

# Meshing
I have to prepare to set of meshes for two geometry: 

- Airfoil (or `A`): with a chord of 300 mm length
- Cylinder (or `C`): with a chord (diameter) of 50 mm 

Also, to check the mesh independence, for each mesh, I defined a *mesh refinement level* 
, `X`, which scales the characteristic size of mesh elements globally with $lc_x = 2^{-X} lc_0$, 
where $lc$ is the characteristic length.

Indeed, to detect flow separation, eddies, etc., I need to refine the mesh locally on some
parts of the domain. This section, explains how and why these refinements are carried out.
 

## Domain geometry
First, I started simulation with a domain with square boundaries but turned out this setup
makes some boundary artifacts that severely impact the simulation results. Therefore, I used
the CH-mesh technique since then [1](src1: On Mesh Convergence and Accuracy Behaviour
for CFD Applications).

>TODO: add a couple of images that show the border effect

The domain dimensions are scaled by the chord length of $c$. The 2D geometry is shown below.

>TODO: add the geometry


### Regions:

- Rotating region: The interior region (6c-circle); This region rotates with the airfoil. This makes us needless to remesh at every timestep. 
- Stationary region: The rest of the domain.

### Boundaries name

- Inlet: The half-circle on the left side of the Domain
- Outlet: The patch on the right side of the Domain
- Top: The patch on the top 
- Bottom: The patch on the Bottom
- Front: The Front patch of the Domain. 
- Back: The back patch of the Domain.
- AMI: The sliding interface between the two regions (it is not a physical boundary condition)
- Airfoil: Irrespective of the geometry, the walls in the center of the domains will be refered as airfoil.

**Note**: The Back and Front boundaries extend to both rotating and stationary regions.


## Meshing Strategy
Generally, we have to have a more refined mesh on the downstream. Also, a good practice is
to keep the size of the mesh elements similar from one zone to another. By these, I
propose the following procedure to control the mesh size.

### Stationary Zone
Most of the interesting events, take place inside the rotating zone. So there's no need to have a very refined mesh in the stationary region. I decided to mesh this region
in a structured manner to avoid unnecessary corrections due to non-orthogonality. this, 
however, doesn't mean a uniform mesh all over the stationary region.

I control it by choosing the number of elements and the ratio between each two consecutive 
elements, on the domain border as well as the sliding interface (AMI). 

**Note**: In `gmsh` (or any reasonable meshing software which makes a conformal structured 
mesh), the number of elements in the opposite lines must be equal.

Let's say there are $n$ elements on the AMI circumstance. Then, if the number of element sizes
where uniform, the number of elements on each piece of the AMI's circumstance would be 
proportional to its length:

>TODO: the value of n34 depends if I add the trailing line or not

$$
n_{12} = n/4 \\
n_{23} = n/8 \\
n_{34} = n/4
$$
 
I want more elements in the outlet part. therefore, I introduce the $f$ coefficients to
overweight and underweight each part:

>TODO: it might be wrong if f34 is associated with more than half of the outlet port

$$
n_{12} = f_{12}n/4 \\ n_{23} = f_{23}n/8 \\ n_{34} = f_{34}n/4 \\
$$

with $f_{12}, f_{23} < 1$ and $f_{34} = 3 - f_{12} - f_{23}$. 
