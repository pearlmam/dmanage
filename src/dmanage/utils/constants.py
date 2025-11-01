#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 10 11:36:35 2021
Constants
@author: marcus
"""

class Constants():
    def __init__(self):
        self.pi = 3.1415926535              # [rad]
        self.c = 299792458.0                # [m/s] speed of light
        self.mu0 = 4*self.pi*1e-7           # permeability
        self.eps0 = 1/self.c**2/self.mu0    # permitivity
        self.me = 9.109383e-31              # [kg] mass of electron
        self.qe = 1.602176e-19              # [C] charge of electron
        
        
        
pi = 3.1415926535               # [rad]
c = 299792458.0                 # [m/s] speed of light
mu0 = 4*pi*1e-7                 # permeability
eps0 = 1/c**2/mu0               # permitivity
me = 9.109383e-31               # [kg] mass of electron
qe = 1.602176e-19               # [C] charge of electron
meev = c**2*me/qe               # mass of electron in  [eV/c**2] 
eV2J = 1.602176e-19             # eV in [J]
mp = 1.6726e-27                 # mass of proton [kg]
k = 1.3807e-23                  # Boltzmann constant [J/K]
h = 6.6262e-34                  # Planck constant [J*s]
hbar = h/2/pi                   # Planck constant [J*s]
NA = 6.0220e23                  # Avagadro number [molecules/mole]
R = k*NA                        # Gas constant [J/kg/mol]
a0 = 4*pi*eps0*hbar**2/qe**2/me # Bohr radius [m]

