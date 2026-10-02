
Philosphy of Data Visualization 
===============================

The philosophy of data visualization starts with the language to describe data and the visualization. Here are a list of terms. 

blah, blah blah.


Describing Data
---------------

Data can be categorized by it's *dimensionality* and the *properties* it represents. In philosophy speak, properties are an attribute, quality, or characteristic that can be predicated of or instantiated by an object. In other words, it is the measured characteristic of an object. The dimensionality represents the number of independent coordinates, degrees of freedom, or structural parameters needed to specify an object. Often dimensions are spatial locations, but they can also be properties or some other variable. We describe the dimensionality of date using a number followed by a 'D'; common dimensionalities are: 0D (scalars), 1D (lines), 2D (planes), 3D (boxes), and ND where N is an integer. 

The separation between what constitues a dimension or a property can be blurry sometimes. For example a 3D array can consist of two dimensions and the third can represent different properties occupying the same spatial location. Examples of this are vector fields, a vector describes direction via the x, y, and z magnetudes at spatial locations; we consider the x, y, and z magnetudes as properties in this context and the spatial locations are the dimensions.

Topographical maps are another example where the distinction might be blurry. These consist of two dimensions and the property is height. While spatial coordinates like hieght, are generally considered dimensions, in this case height is being used as a property of a 2D spatial location. 


Visualization of Data Properties
--------------------------------

Visualizations of ND data requires at least N spatial/time dimensions and the property can be represented by an additional spatial/time dimension or by a *glyph*. A glyph is visual symbol, mark, or character that represents a data property. For example, 1D data can be plotted as a line graph on the x-y (2D) plane, where x corresponds dimensional index and y corresponds to the data property. The same 1D data can be plotted in one horizontal line, whose x coordinate represents the dimensional index and color represents the data property; the glyph in this case is only color. 

Glyphs can have multiple *visual properties* to represent multiple data properties simultaneously. Visual properties refers to the properties of the glyph itself, like color, opacity, marker shape, marker size, etc. Visualization properties are used to represent data properties in a way we can see. All visualization properties can represent analog or discrete properties; however some are better suited analog or discrete representations. For example, while there are infinite marker shapes to choose from, plotting software often as limited options of shapes to choose from; marker shapes should generally be limited to discrete values [#f4]_. Deciding which visualization properties to use for analog and discrete data is based on the human perception to differentiate between the mapped property.


Visualization Limitations to Dimensionality
-------------------------------------------

The real limitation to the highest dimensionality we can visualize is 4D, limited by human experience: we live in a 3D world with the fourth dimension time. Generally we view data on 2D screens; however that does NOT limit the dimensionality because 3D representations are possible by mathematically projecting three-dimensional coordinates (X, Y, Z) into a two-dimensional pixel grid (X, Y) and using visual cues like perspective and lighting to simulate depth in a way humans can comprehend.  Technically, even higher dimensions can be projected onto lower dimensions, but practically this difficult for humans because of our experience. *Static visualizations* [#f2]_ are limited to 3D because time cannot be used; these are used in manuscripts. *Dynamic visualizations* allow visualization of 4D data because this allows On 2D screens and paper.

Visualization Limitations of Properties
---------------------------------------

The limitation to the number of properties that can be used in a visualization is in the number of available spatial/time dimensions and *distinct* and *observable* visualization properties. Again, spatial/time dimensions or visualization properties can be used to represent a data property. Visualization properties must by observable, for example color is readily observable for humans but color saturation might be difficult for humans to differentiate. Visualization properties must be distinct, meaning that visualization properties cannot override other visualization properties; for example single color glyph cannot use multiple colormaps to represent two data properties because one color overrides the other [#f3]_. In static visualizations, the upper limit in the number of simultaneous visualization properties is not a hard limit, but we can estimate the practical limit at around 4: color, marker shape, marker size, and opacity. 

Viewing >4D Data
----------------

Given the limitations discussed `Visualization Limitations to Dimensionality`_, how can we view higher dimensionality? One way is to project higher dimensions onto the lower ones; I don't know anything about this. Another way is to reshape the data into a lower dimension; this essentially takes the higher dimensions and stacks them into a lower dimension. The utility of this is questionable, but maybe it can be useful.

Viewing More Properties
-----------------------

As discussed in `Visualization Limitations of Properties`_, the number of simultaneous visualization properties is limited to perception. Ways to increase this limit involve *spatial or temporal expansion of glyphs*. Visualization properties cannot occupy the pixel, so we give the glyph depth so that glyphs can represent multiple visualization properties. The true limit to the simultaneous number of properties that can be viewed is only limited by your imagination and your ability to differentiate between glyph visual properties. "Time" also allows for viewing more properties; time in this sense does not necessarily imply a video, but it implies user interaction. Users can interact with the visualization to toggle data property glyph representations. 


Visualization Types
-------------------

There a many different types of `data visualizations`_ . The difference between the visualization types is in the way glyphs and spatial/temporal extents are used to represent the data dimensionality and properties. Which visualization type to use depends on the goal. 



.. rubric:: Footnotes


.. [#f2] Static visualizations are ones that do not change in time. These are used in manuscripts.

.. [#f3] To bypass this limitation, one can expand the glyph spatially to allow for multiple colors. For dynamic visualizations, one can separate the properties in time by generating two plots that occupy the same glyph locations and toggling between the plots to visualize one property at a time. See blah for more created ways.

.. [#f4] One way to use shape as an analog-ish property is to use the number of sides of a polygon, or the number of points of a star as property values. However, differentiating between 20 and 21 sides or points would be difficult for a human.


.. _data visualizations: https://datavizproject.com/

