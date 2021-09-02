import os


def get_uv_obj_path(uv_type, resolution):
    path = os.path.dirname(os.path.realpath(__file__))
    uv_obj_path = os.path.join(path, "data", "{}_{}.obj".format(uv_type, resolution))
    return uv_obj_path
