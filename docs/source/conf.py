# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'D-Manage'
copyright = '2025, Marcus Pearlman'
author = 'Marcus Pearlman'
release = '1.00'

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here.
#import sys
import os
#from pathlib import Path
#path = str(Path(__file__).resolve().parents[2]) + 'notebooks/'
#path = os.path.abspath("..")
#sys.path.insert(0, path)


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
   'sphinx.ext.napoleon',     # for parsin numpy and Google style docstrings
   'sphinx.ext.autodoc',      # Automatic code documentation
   'sphinx.ext.doctest',      # for traditional documentation and code
   'nbsphinx',                # for notebooks
   'sphinx_rtd_dark_mode',    # Dark mode toggle for sphinx_rtd_theme
]

templates_path = ['_templates']
exclude_patterns = []
primary_domain = 'py'


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_logo = './logo/dmanage-logo-inkscape.svg'
html_static_path = ['_static']

# -- Options for nbsphinx -----------------------------------------------------
nbsphinx_execute = "auto"   # run notebooks at build time
# Other options: "auto", "never", "inline"

# Tell Sphinx where notebooks are located
nbsphinx_allow_errors = True
nbsphinx_input_path = os.path.abspath("./notebooks")

# -- Options for napoleon -------------------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# -- Options for sphinx_rtd_dark_mode -------------------------------------------------
default_dark_mode = False     # user starts in light mode


# -- General options ----------------------------------------------------------
exclude_patterns = ['_build', '**.ipynb_checkpoints']


# Here are some universal hyperlinks
rst_epilog = """
.. _pandas: https://pandas.pydata.org/
.. _Pandas: https://pandas.pydata.org/
.. _scipy: https://scipy.org/
.. _Scipy: https://scipy.org/
.. _numpy: https://numpy.org/
.. _Numpy: https://numpy.org/
.. _matplotlib: https://matplotlib.org/
.. _Matplotlib: https://matplotlib.org/
.. _dmanage: https://github.com/pearlmam/dmanage
"""
# .. |dmanage| replace:: :ref:`dmanage` 

