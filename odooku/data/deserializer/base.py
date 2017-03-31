class BaseFieldDeserializer(object):

    def deserialize(self, values, context):
        raise NotImplementedError()
    
    @classmethod
    def factory(cls, field_name, field):
        raise NotImplementedError()
