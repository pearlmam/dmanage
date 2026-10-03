
Data Exploration
================

Visualization of data is essential to interpreting and understanding data. In order to properly visualize data, a *data exploration environment* is helpful. A data exploration environment is an interactive visualization environment where users can plot the data and interact with the plot in such a way as to visualize different properties in an intuitive way. Here the focus is not on the visualizations themselves, but on ways to easily explore your data. Data exploration involves interactive visualizations of all levels in the hierarchy in one application. 

The type of visualiziation used for each level depends on the degrees of freedom and the property to visualize.  See BLAH for more information on how to choose the visualization type. The key to data exploration is the ability to visualize different properties of each level and the ability to traverse and visualize each level. The levels here mirror the data hieararchy, but are somewhat arbitrary and the stacking of levels is possible as well. 

Group Explorer
--------------

This level provides the overview of your entire dataset. The most common visualization is a 2D scatter plot with glyphs representing the properties of interest. Generally, the properties of interest are scalers or scalar representations of higher dimension data; however, glyphs can also plot higher dimensional data if that is useful. 

A key aspect of the group explorer is that the user can interact with glyphs to find out additional info about that unit. Ideally, clicking on a glyph can display a summary of the unit data and/or launch the unit explorer. In this way the user can visualize the entire dataset and query specific units of interest to find out what is going on.

Unit Explorer
-------------

This level provides the overview of a single data unit. Comparisons between multiple component data can be performed here. The user can interact with glyphs to find out additional info about that component and traverse down to the component explorer. 

Component Explorer
------------------

This basically plots the component data. Different filters can be applied to the data. Information about each datapoint, aggregations, and other information can be queried about the component.


Hybrid Explorers
----------------

Hybrid explorers provide a way to mix and match different levels for different agendas. For example one might want to view 1D data from a component for the entire group. We can create a component explorer to plot a line graph, the interact with the component itself, and apply filtering operations on the component data. This explorer could add a group toggle to apply the same operations to each data unit in the group and generate an interactive visualization type appropriate for the dimensionality and number of properties. In a sense this is just a component viewer where the group toggle traverses up to a group explorer. Again, the levels are somewhat arbitrary, but are helpful to convey the purpose of the visualizations.

Explorer Tools
--------------

There are many different tools to explore your data. Most tools are excellent for visualizing the data itself and the often provide simple operation and query methods; however, traversing data levels and unconventional operations and queries are challenging to implement with these tools. User friendly tools often use a GUI first approach, which limits or makes low level data access challenging. This is why dmanage pushes a code first approach; data objects created using the dmanage methodology provides the low level access, and the dmanage data exploration flavor modules automatically provides the high level visualization and integration with common commercial and open-source visualization tools for common applications. See here for a list of dmanage exploration flavors and how to contribute your own flavors to the community.






.. _data visualizations: https://datavizproject.com/
