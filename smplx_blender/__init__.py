bl_info = {
    "name": "smplx_blender",
    "author": "Joachim Tesch, Max Planck Institute for Intelligent Systems; Tyler Parker, Meshcapade",
    "version": (2021, 8, 20),
    "blender": (3, 5, 1),
    "location": "Viewport > Right panel",
    "description": "SMPL-X and Meshcapade Utilities for Blender",
    "wiki_url": "https://smpl-x.is.tue.mpg.de/",
    "category": "SMPL",
}


if "bpy" in locals():
    import importlib
    if "smplx_blender" in locals():
        importlib.reload(smplx_blender)
    else:
        from . import smplx_blender
else:
    import bpy
    from . import smplx_blender

def register():
    smplx_blender.register()

def unregister():
    smplx_blender.unregister()