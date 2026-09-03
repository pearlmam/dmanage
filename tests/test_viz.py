# -*- coding: utf-8 -*-

import dmanage.viz as viz
from dmanage._compat import pd
import numpy as np
## generate data


np.random.seed(101)
n = 600

# Integers: Discrete experimental runs, hours, and replicate IDs
run_id = np.repeat(np.arange(101, 301), 3)  # 200 runs in triplicate
incubation_hours = np.random.choice([12, 24, 36, 48, 72], size=n)
replicate_num = np.tile([1, 2, 3], 200)

# Floats: Environmental conditions and kinetic assays
temperature_c = np.round(
    np.random.normal(loc=37.0, scale=0.7, size=n), 2
    )  # Normal distribution
ph_level = np.round(
    np.random.beta(a=5, b=2, size=n) * 2.5 + 5.8, 2
    )  # Skewed distribution

# Non-linear growth curve (Sigmoidal curve + noise)
base_rfu = 1000 / (1 + np.exp(-(incubation_hours - 30) / 8))
fluorescence_rfu = np.round(base_rfu * np.random.normal(1, 0.1, n), 1)

# Secondary metric with an exponential noise component
enzyme_activity = np.round(
    fluorescence_rfu * 0.045 + np.random.exponential(scale=1.5, size=n), 3
    )

# Booleans: Treatment groups, contamination anomalies, and pass/fail gates
inhibitor_added = np.random.choice([True, False], size=n, p=[0.5, 0.5])
is_contaminated = np.random.choice([True, False], size=n, p=[0.06, 0.94])

# Apply treatment impact (inhibitor dampens fluorescence)
fluorescence_rfu = np.where(
    inhibitor_added, fluorescence_rfu * 0.35, fluorescence_rfu
    )

# Derived pass gate based on multiple experimental tolerances
pass_quality_control = (
    (ph_level >= 6.5)
    & (ph_level <= 7.8)
    & (temperature_c >= 35.5)
    & (temperature_c <= 38.5)
    & (~is_contaminated)
    )

df = pd.DataFrame(
        {
            "run_id": run_id,
            "incubation_hours": incubation_hours,
            "replicate_num": replicate_num,
            "temperature_c": temperature_c,
            "ph_level": ph_level,
            "fluorescence_rfu": fluorescence_rfu,
            "enzyme_activity": enzyme_activity,
            "inhibitor_added": inhibitor_added,
            "is_contaminated": is_contaminated,
            "pass_quality_control": pass_quality_control,
        }
    )





