""" Helper utilities. """

# ---------------------------------------------------------------------

def to_bool( val ):
    """Interpret a value as a boolean."""
    if val is None:
        return None
    val = str( val ).lower()
    if val in ["yes","true","enabled","1"]:
        return True
    if val in ["no","false","disabled","0"]:
        return False
    return None
