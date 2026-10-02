
cache
-----

This module provides a convienent API to 'cache' data within your data object. This can store data in RAM (:term:`soft cache`) or on the disk (:term:`hard cache`). The advantage of the cache over just using attributes of the data object is that your object can be :term:`order agnostic` so that methods can be called whenever the result is needed and no redundant calculations will be performed. The :term:`hard cache` also provides an efficient way to store high computational cost results to the disk for use anytime.
