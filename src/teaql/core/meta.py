class PropertyDescriptor:
    def __init__(self, name: str, property_type: str = "String"):
        self.name = name
        self.property_type = property_type
        self.column_name_val = name
        self._is_id = False
        self._is_version = False
    def column_name(self, name): 
        self.column_name_val = name
        return self
    def is_id(self): 
        self._is_id = True
        return self
    def is_version(self): 
        self._is_version = True
        return self

class EntityDescriptor:
    def __init__(self, name: str):
        self._name = name
        self.table_name_val = name
        self.properties = []
    def table_name(self, name): 
        self.table_name_val = name
        return self
    def property(self, prop): 
        self.properties.append(prop)
        return self
