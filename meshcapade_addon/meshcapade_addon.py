import bpy
from . import (
    properties,
    ui,
    operators,
)


def register():
    for prop_class in properties.PROPERTY_CLASSES:
        bpy.utils.register_class(prop_class)

    for ui_class in ui.UI_CLASSES:
        bpy.utils.register_class(ui_class)

    for operator in operators.OPERATORS:
        bpy.utils.register_class(operator)

    properties.define_props()


def unregister():
    properties.destroy_props()

    for operator in reversed(operators.OPERATORS):
        bpy.utils.unregister_class(operator)

    for ui_class in reversed(ui.UI_CLASSES):
        bpy.utils.unregister_class(ui_class)

    for prop_class in reversed(properties.PROPERTY_CLASSES):
        bpy.utils.unregister_class(prop_class)
