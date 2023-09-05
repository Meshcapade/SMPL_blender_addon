import bpy
from . import (
    properties,
    ui,
    operators,
)


handle_shape_key_change=object()
def shape_key_change(*args):
    bpy.ops.object.update_joint_locations('EXEC_DEFAULT')


def register():
    for prop_class in properties.PROPERTY_CLASSES:
        bpy.utils.register_class(prop_class)

    for ui_class in ui.UI_CLASSES:
        bpy.utils.register_class(ui_class)

    for operator in operators.OPERATORS:
        bpy.utils.register_class(operator)

    properties.define_props()


    #subscribe to changes of the shape keys and call the function to update the joint locations
    bpy.msgbus.subscribe_rna(
        key =  bpy.types.ShapeKey, #will check for all the properties changes in ShapeKeys. We are mostly interested in .value and .mute
        owner=handle_shape_key_change,
        args=(1, 2, 3),
        notify=shape_key_change
    )



def unregister():
    properties.destroy_props()

    for operator in reversed(operators.OPERATORS):
        bpy.utils.unregister_class(operator)

    for ui_class in reversed(ui.UI_CLASSES):
        bpy.utils.unregister_class(ui_class)

    for prop_class in reversed(properties.PROPERTY_CLASSES):
        bpy.utils.unregister_class(prop_class)

    bpy.msgbus.clear_by_owner(handle_shape_key_change)

