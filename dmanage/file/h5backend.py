# -*- coding: utf-8 -*-

__all__ = ["H5File","HDFBackend"]

class HDFBackend:
    def open(self, path):
        raise NotImplementedError

    def get_node(self, h5, path):
        raise NotImplementedError

    def get_attrs(self, node):
        raise NotImplementedError

    def shape(self, node):
        raise NotImplementedError

    def read(self, node):
        raise NotImplementedError

    def keys(self, node):
        raise NotImplementedError

    def parent(self, node):
        raise NotImplementedError

class H5pyBackend(HDFBackend):
    def __init__(self):
        import h5py
        self._h5py = h5py
        
    def open(self, path):
        return self._h5py.File(path, "r")

    def get_node(self, h5, path):
        return h5[path]

    def get_attrs(self, node):
        return node.attrs

    def shape(self, node):
        return getattr(node, "shape", None)

    def read(self, node):
        return node[...]   # old: np.array(node)

    def keys(self, node):
        return list(node.keys())

    def parent(self, node):
        return node.parent
    
class TablesBackend(HDFBackend):
    def __init__(self):
        import tables
        self._tables = tables
    def open(self, path):
        return self._tables.open_file(path, "r")

    def get_node(self, h5_or_node, path):
        # h5["/group/child"]     # works
        # h5["/group"]["child"] # works
        # Absolute path -> resolve from file
        if isinstance(h5_or_node, self._tables.file.File):
            path = self._norm(path)   # I think these should start with '/'
            return h5_or_node.get_node(path)
        
        # Relative path -> child lookup
        if path.startswith("/"):
            # Need file to resolve absolute path
            return h5_or_node._v_file.get_node(path)

        return h5_or_node._v_children[path]

    def get_attrs(self, node):
        """ 
        option for returning actual tables object: return node._v_attrs
        Here we return a dict to look like h5py
        """
        return {
            name: node._v_attrs[name]
            for name in node._v_attrs._v_attrnames
        }

    def shape(self, node):
        return getattr(node, "shape", None)

    def read(self, node):
        return node.read()

    def keys(self, node):
        if hasattr(node, "_v_children"):
            return list(node._v_children.keys())
        return []

    def parent(self, node):
        return node._v_parent
    
    def _norm(self,path):
        return path if path.startswith("/") else "/" + path
    
class H5File:
    def __init__(self, path, backend: HDFBackend):
        self.backend = backend
        self._h5 = backend.open(path)

    def __getitem__(self, path):
        node = self.backend.get_node(self._h5, path)
        return H5Node(node, self.backend)

    def keys(self):
        return self["/"].keys()

    def close(self):
        self._h5.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
    
    
class H5Node:
    def __init__(self, node, backend: HDFBackend):
        self._node = node
        self._backend = backend

    def __getitem__(self, key):
        return H5Node(
            self._backend.get_node(self._node, key),
            self._backend,
        )

    @property
    def parent(self):
        return H5Node(self._backend.parent(self._node), self._backend)

    @property
    def attrs(self):
        return self._backend.get_attrs(self._node)

    @property
    def shape(self):
        return self._backend.shape(self._node)

    def read(self):
        return self._backend.read(self._node)

    def keys(self):
        return self._backend.keys(self._node)

    def __getattr__(self, name):
        # Delegate everything else to underlying node
        return getattr(self._node, name)
    
 