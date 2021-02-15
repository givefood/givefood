
def clone_entity(entity, new_key):
    """ Return a clone of the given entity with the key changed to the given key. """
    # TODO: can this be better or less weird?
    # Entity doesn't implement copy()
    entity_as_protobuff = entity.ToPb()
    new_entity = entity.__class__.FromPb(entity_as_protobuff)
    # __key is a protected attribute, so we have to set _Entity__key
    new_entity.__key = new_key
    new_entity._Entity__key = new_key
    return new_entity
