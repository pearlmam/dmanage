# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import dmanage.explore as explore

if __name__ == "__main__":
    # Create sample CSV datasets
    file_a = "sensors_location_a.csv"
    pd.DataFrame({
        "Timestamp": np.arange(100),
        "Temp_C": np.sin(np.linspace(0, 10, 100)) * 10 + 20,
        "Humidity_Pct": np.cos(np.linspace(0, 10, 100)) * 20 + 50,
    }).to_csv(file_a, index=False)

    file_b = "financial_summary.csv"
    pd.DataFrame({
        "Quarter": [1, 2, 3, 4],
        "Revenue_USD": [120000, 150000, 140000, 190000],
        "Expenses_USD": [80000, 95000, 90000, 110000],
        "Profit_USD": [40000, 55000, 50000, 80000],
    }).to_csv(file_b, index=False)
    
    file_c = "sensors_location_b.csv"
    pd.DataFrame({
        "Timestamp": np.arange(100),
        "Temp_C": np.sin(np.linspace(0, 10, 100)) * 10,
        "Humidity_Pct": np.cos(np.linspace(0, 10, 100)) * 20 + 20,
    }).to_csv(file_c, index=False)
    

    explorer = explore.HvColumnExplorer(paths=[file_a, file_b,file_c])
    server = explore.launch_server(explorer, port=5006)

