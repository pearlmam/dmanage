# -*- coding: utf-8 -*-



import dmanage.dfmethods as dfm
from dmanage.server.basic import Server

def make_database(base):
    class DataBase(base):
        """
        dataBases is a dict containing server and folder entries
        {'local':{'dataCollections':collectionList,'user':userName},'ipAddress':folderList}
        """
        def __init__(self,computers={}):
            if 'local' in computers.keys():
                super().__init__(computers['local']['dataGroups'][0])
                pass
            else:
                #load components from the server?
                pass
            # connections needs to be setup
            servers = []
            for computer,info in computers.items():
                servers = servers + [Server(computer=computer,user=info['user'])]
            # then I need set up the components
            # super().__init__()
            self.servers = servers
        
        def inheritance_level():
            """qualifer to determine the hierarchy level for wrapping methods"""
            return 'DB'
        
        
        
        def connection_setup(self):
            pass
        
    return DataBase


