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

class RelationDescriptor:
    def __init__(self, name: str, target_entity: str):
        self.name = name
        self.target_entity = target_entity
        self.local_key = "id"
        self.foreign_key = ""
        self.is_many = False

    def local(self, field_name: str):
        self.local_key = field_name
        return self

    def foreign(self, field_name: str):
        self.foreign_key = field_name
        return self

    def many(self):
        self.is_many = True
        return self

class EntityDescriptor:
    def __init__(self, name: str):
        self._name = name
        self.table_name_val = name
        self.properties = []
        self.relations = []
        self.audit_mask_fields_val = []
        self.audit_value_max_len_val = None
    def table_name(self, name): 
        self.table_name_val = name
        return self
    def property(self, prop): 
        self.properties.append(prop)
        return self

    def relation(self, relation):
        self.relations.append(relation)
        return self

    def relation_by_name(self, name):
        return next((relation for relation in self.relations if relation.name == name), None)

    def property_by_name(self, name):
        return next((prop for prop in self.properties if prop.name == name), None)

    def audit_mask_fields(self, fields):
        self.audit_mask_fields_val = list(fields)
        return self

    def audit_value_max_len(self, max_len):
        if max_len is not None and max_len < 0:
            raise ValueError("audit value max length cannot be negative")
        self.audit_value_max_len_val = max_len
        return self
