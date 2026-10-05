
Interactive Visualization Platforms
===================================


Interactive Visualization Platforms (IVPs) provide different ways to visualize and explore your data. Different disciplines have different needs for visualization so there are many different flavors of IVPs. IVPs use ``dmanage.explore`` module classes as a base to help manage threading and to integrate with data objects. So far, base classes are provided to work with hvplot, but in the future there will be support for plotly and others. Dmanage offers flavors of its own and community devloped flavors are shared here. Each flavor can be described by the primary level of visualization, dimensionality of the data, the number of simulatanious properties that can be visualized, and more as the project progresses. See :ref:`concepts/dataVisualization:Philosphy of Data Visualization` and  :ref:`concepts/dataExplorer:Data Exploration` for concepts and language used here to describe IVPs.


DataFrame Explorer
------------------

:primary level: group
:level traverse: query
:dimensionality: 1D
:simultanious properties: 3
:aggregation: yes
:stability: stable

.. note::
   The language/keywords used to describe IVPs is under development and subject to change as the language develops


This IVP flavor takes inspiration from hvplot explorer. This provides a way to visualize 1D group data properites. Up to 3 properties can be viewed simulataniously. This also supports simple aggregations. 


Example data::


              V1RMS     I1RMS      Power  ...  errorPUp      r2Up  O3dalpha
    0   2797.746247  0.036082  24.235529  ...  0.000822  0.999819  0.000412
    1   3086.517653  0.041402  30.854756  ...  0.001473  0.999525  0.000650
    2   3277.954251  0.044056  34.569045  ...  0.001852  0.999266  0.001290
    3   3435.219574  0.046402  37.240442  ...  0.002631  0.998907  0.001322
    4   3034.422256  0.040023  30.514193  ...  0.001870  0.999307  0.000884
    5   2997.660635  0.037917  24.892930  ...  0.006088  0.990347  0.000797
    6   2691.636754  0.033831  21.306578  ...  0.001895  0.999256  0.000709
    7   2935.227314  0.011750  13.487443  ...  0.000925  0.999842  0.000513
    8   3033.642746  0.017432  27.028280  ...  0.000861  0.999837  0.000914
    9   3238.111389  0.022076  37.727121  ...  0.001480  0.999574  0.001482
    10  3431.281242  0.025114  45.744299  ...  0.001568  0.999621  0.001606
    11  3040.705165  0.017832  29.970640  ...  0.001810  0.999417  0.001945
    12  2871.675240  0.016743  25.112758  ...  0.001805  0.999384  0.001945
    13  2891.863781  0.015266  21.529669  ...  0.001445  0.999710  0.002091
    14  2895.488837  0.014680  20.674114  ...  0.002047  0.999128  0.000042
    15  2888.433633  0.014737  20.872638  ...  0.002347  0.998886 -0.000358
    16  3512.786850  0.020069  39.091871  ...  0.001143  0.999719  0.003466
    17  3196.509336  0.017844  31.512076  ...  0.000761  0.999849  0.002523
    18  2979.309610  0.016270  26.083977  ...  0.000695  0.999871  0.002441
    19  2857.359822  0.015208  22.578390  ...  0.001304  0.999572  0.002498
    20  3532.289481  0.020240  39.599696  ...  0.001103  0.999709  0.003372
    21  2978.782792  0.016249  25.981507  ...  0.000933  0.999720  0.002136
    22  2814.919340  0.013391  16.232700  ...  0.001898  0.999105  0.001067

    [23 rows x 23 columns]


This example data is 1D with multple properties. A annotated screenshot of the visualization is shown below. On the left "Controls" tab, different properties can be chosen for x and y axes, the color by option chooses which property represents the color of the glyphs, the marker by option chooses which property represents the glyph shape. Marker by is limited to category like properties. The group by and aggregate options groups a property together and aggregates them to display the aggregated glyphs. Note that each property selected by x, color by and marker by options grouped separatly. The "Bin" tab can bin properties into N categories for use in the marker by option.


.. figure:: 
   /figures/IVP/dataframeExplorer_annotated.jpg


