bl_info = {
    "name": "SMPL-X and Meshcapade Utilities for Blender",
    "author": "Joachim Tesch, Max Planck Institute for Intelligent Systems; Tyler Parker, Meshcapade",
    "version": (2021, 8, 20),
    "blender": (2, 92, 0),
    "location": "Viewport > Right panel",
    "description": "SMPL-X and Meshcapade Utilities for Blender",
    "wiki_url": "https://smpl-x.is.tue.mpg.de/",
    "category": "SMPL-X",
}


def register():
    import bpy
    from . import (
        properties,
        ui,
        operators,
    )

    for prop_class in properties.PROPERTY_CLASSES:
        bpy.utils.register_class(prop_class)

    for ui_class in ui.UI_CLASSES:
        bpy.utils.register_class(ui_class)

    for operator in operators.OPERATORS:
        bpy.utils.register_class(operator)

    properties.define_props()


def unregister():
    import bpy
    from . import (
        properties,
        ui,
        operators,
    )

    properties.destroy_props()

    for operator in reversed(operators.OPERATORS):
        bpy.utils.unregister_class(operator)

    for ui_class in reversed(ui.UI_CLASSES):
        bpy.utils.unregister_class(ui_class)

    for prop_class in reversed(properties.PROPERTY_CLASSES):
        bpy.utils.unregister_class(prop_class)
