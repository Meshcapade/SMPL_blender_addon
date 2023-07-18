import bpy
from .globals import (
    FBX_TYPE,
    OBJ_TYPE,
)
from mathutils import Vector, Quaternion
import os

def get_uv_obj_path(uv_type, resolution):
    path = os.path.dirname(os.path.realpath(__file__))
    uv_obj_path = os.path.join(path, "data", "{}_{}.obj".format(uv_type, resolution))
    return uv_obj_path

def imported_object(func):
    '''Decorator that returns the imported object (Blender is lame and doesn't return from import).
        Assumes one imported object, and no return from the function
    '''

    def wrap(*args, **kwargs):
        active_collection = get_active_collection()
        old_objs = set(active_collection.objects)
        func(*args, **kwargs)
        imported_objs = set(active_collection.objects) - old_objs

        # Assumes one imported object
        return imported_objs.pop()
    return wrap


@imported_object
def import_obj(path, axis_forward='-Z', axis_up='Y'):
    bpy.ops.import_scene.obj(
        filepath=path,
        split_mode='OFF',
        axis_forward=axis_forward,
        axis_up=axis_up,
    )


@imported_object
def import_fbx(path):
    bpy.ops.import_scene.fbx(
        filepath=path,
        # Scale based on cm vs. m
        # global_scale=100.0,
        use_custom_normals=False,
        ignore_leaf_bones=True,
    )


def export_obj(path):
    bpy.ops.export_scene.obj(
        filepath=path,
        use_selection=True,
        keep_vertex_order=True,
    )


def export_fbx(path):
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        add_leaf_bones=False,
        mesh_smooth_type='FACE',
        use_mesh_modifiers=False,
        use_active_collection=True,
    )


def export_object(obj, export_type, path):
    deselect()
    select_object(obj, select_hierarchy=True)
    if export_type == OBJ_TYPE:
        export_obj(path=path)
    elif export_type == FBX_TYPE:
        export_fbx(path=path)


def set_active_object(obj):
    bpy.context.view_layer.objects.active = obj


def get_active_object():
    return bpy.context.view_layer.objects.active


def select_object(obj, select_hierarchy=False):
    if select_hierarchy:
        set_active_object(obj)
        bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE')
    obj.select_set(True)


def delete_object(obj):
    select_object(obj=obj, select_hierarchy=True)
    bpy.data.objects.remove(obj, do_unlink=True)


def get_selected_objects():
    collection = get_active_collection()
    return [obj for obj in collection.objects if obj.select_get()]


def deselect():
    bpy.ops.object.select_all(action='DESELECT')


def create_collection(name):
    collection = bpy.data.collections.new(name=name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_object_to_collection(obj, collection):
    obj_old_collections = obj.users_collection
    collection.objects.link(obj)
    for old_coll in obj_old_collections:
        old_coll.objects.unlink(obj)


def get_active_collection():
    return bpy.context.view_layer.active_layer_collection.collection


def change_active_collection(collection):
    layer_collection = bpy.context.view_layer.layer_collection.children[collection.name]
    bpy.context.view_layer.active_layer_collection = layer_collection


def destroy_collection(collection):
    for obj in collection.objects:
        delete_object(obj=obj)
    bpy.data.collections.remove(collection)


def rodrigues_from_pose(armature, bone_name):
    # Use quaternion mode for all bone rotations
    if armature.pose.bones[bone_name].rotation_mode != 'QUATERNION':
        armature.pose.bones[bone_name].rotation_mode = 'QUATERNION'

    quat = armature.pose.bones[bone_name].rotation_quaternion
    (axis, angle) = quat.to_axis_angle()
    rodrigues = axis
    rodrigues.normalize()
    rodrigues = rodrigues * angle
    return rodrigues


def update_corrective_poseshapes(self, context):
    if self.smplx_corrective_poseshapes:
        bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')
    else:
        bpy.ops.object.smplx_reset_poseshapes('EXEC_DEFAULT')


def set_pose_from_rodrigues(armature, bone_name, rodrigues, rodrigues_reference=None):
    rod = Vector((rodrigues[0], rodrigues[1], rodrigues[2]))
    angle_rad = rod.length
    axis = rod.normalized()

    if armature.pose.bones[bone_name].rotation_mode != 'QUATERNION':
        armature.pose.bones[bone_name].rotation_mode = 'QUATERNION'

    quat = Quaternion(axis, angle_rad)

    if rodrigues_reference is None:
        armature.pose.bones[bone_name].rotation_quaternion = quat
    else:
        # SMPL-X is adding the reference rodrigues rotation to the
        # relaxed hand rodrigues rotation, so we have to do the same here.
        # This means that pose values for relaxed hand model cannot be
        # interpreted as rotations in the local joint coordinate system of the relaxed hand.
        # https://github.com/vchoutas/smplx/blob/f4206853a4746139f61bdcf58571f2cea0cbebad/smplx/body_models.py#L1190
        #   full_pose += self.pose_mean
        rod_reference = Vector((rodrigues_reference[0], rodrigues_reference[1], rodrigues_reference[2]))
        rod_result = rod + rod_reference
        angle_rad_result = rod_result.length
        axis_result = rod_result.normalized()
        quat_result = Quaternion(axis_result, angle_rad_result)
        armature.pose.bones[bone_name].rotation_quaternion = quat_result

        """
        rod_reference = Vector((rodrigues_reference[0], rodrigues_reference[1], rodrigues_reference[2]))
        angle_rad_reference = rod_reference.length
        axis_reference = rod_reference.normalized()
        quat_reference = Quaternion(axis_reference, angle_rad_reference)

        # Rotate first into reference pose and then add the target pose
        armature.pose.bones[bone_name].rotation_quaternion = quat_reference @ quat
        """
    return


def transfer_uv(mesh_from, mesh_to):
    deselect()
    select_object(mesh_to)
    select_object(mesh_from)
    set_active_object(mesh_from)
    bpy.ops.object.join_uvs()
