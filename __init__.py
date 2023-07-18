bl_info = {
    "name": "SMPL Blender Addon",
    "blender": (2, 80, 0),
    "category": "Object",
}

if "bpy" in locals():
    import importlib
    if "smplx_blender" in locals():
        importlib.reload(smplx_blender)
    else:
        from .smplx_blender import smplx_blender
else:
    import bpy
    from .smplx_blender import smplx_blender

def register():
    smplx_blender.register()

def unregister():
    smplx_blender.unregister()