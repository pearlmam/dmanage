Standards
=========

This lists out the documentation standards for this project

.. _Standards-docstrings:

docstrings
----------

Docstrings are the comments imeadiatly following function or class definitions. These follow the numpy standard. Alternative options are google and sphinx standards, but numpy was chosen for this project. An example of the numpy docstring is `here`_. An excert from that link is given below. 

.. _here: https://www.sphinx-doc.org/en/master/usage/extensions/example_numpy.html

.. code-block:: python

   def function_with_types_in_docstring(param1, param2):
      """Example function with types documented in the docstring.

      :pep:`484` type annotations are supported. If attribute, parameter, and
      return types are annotated according to `PEP 484`_, they do not need to be
      included in the docstring:

      Parameters
      ----------
      param1 : int
          The first parameter.
      param2 : str
          The second parameter.

      Returns
      -------
      bool
          True if successful, False otherwise.
      """
      
This is how you describe methods!

Writing Documentation
---------------------

This project uses `sphinx`_ to generate documentation. This package follows the "documentation as code" philosophy, where your entire project, including documentation, should be code-like. This approach takes some time to learn, but offers automatic documentation, subversion support, easy generation of HTMLS, PDFs, and other format documentation in return.
 
.. _sphinx: https://www.sphinx-doc.org/en/master/

reStructuredText
^^^^^^^^^^^^^^^^

This is what many of the documents use, including this one.

Notebooks
^^^^^^^^^

Jupyter notebooks are excellent candidates for demonstration of code and its functions. Many of the tutorials use notebooks for this purpose. Sphinx has an extention `nbsphinx` to suport notbook integration. It will run your notebook and generate the documentation for it. Need link.

Markdown
^^^^^^^^

Markdown is an alternative for reStructuredText that basically serves the same purpose. Juypeter Notebooks can include markdown cells to add text to your code, so markdown is used in this project too.


Generate Documentation
----------------------

To generate the documentation, some setup is needed... I'll probably need to have pakages to be installed for development, separate from base package pakages... This will have to go here too. 

Autodoc
^^^^^^^

This scans your code for packages, modules and functions for docstrings for an automatic index of the project.

To generate the api documentation go to the 'docs' directory and execute the following command. If module names have been renamed, but the module imports havent, errors will occur. refactorization is the term used when changing module names and all the imports. There are tools used for this. If you don't refactor correctly, import erros will occur. However, even if you refactor correctly, this command might fail. Deleting the contents of the api folder might help, and then execute this command. This is similar to the 'make clean' command for generating the documents. There is probably an equivalent for the api command. I'll figure this out later. 

.. code-block:: console

   $ sphinx-apidoc -f -o source/api ../src/dmanage
   
HTML
^^^^

To generate HTML documentation, execute the following:

.. code-block:: console

   $ make clean
   $ make html
   
DONE!




