import bpy

from mathutils import Vector, Quaternion
from math import radians
import os

def setup_bone(bone, SMPL_version):
    # TODO add SMPLH support
    if SMPL_version in ['SMPLX', 'SUPR']:
        bone.head = (0.0, 0.0, 0.0)
        bone.tail = (0.0, 10, 0)


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


def key_all_pose_correctives(obj, index):
    for key_block in obj.data.shape_keys.key_blocks:
        if key_block.name.startswith("Pose"):
            key_block.keyframe_insert("value", frame=index)


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
    if export_type == EXPORT_TYPE.OBJ.value:
        export_obj(path=path)
    elif export_type == EXPORT_TYPE.FBX.value:
        export_fbx(path=path)
    else:
        print ("ERROR, export type is not set to FBX or OBJ")
    

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
    armature.pose.bones[bone_name].rotation_mode = 'QUATERNION'

    quat = armature.pose.bones[bone_name].rotation_quaternion
    (axis, angle) = quat.to_axis_angle()
    rodrigues = axis
    rodrigues.normalize()
    rodrigues = rodrigues * angle
    return rodrigues


def correct_for_anim_format(anim_format, armature):
    if anim_format == "AMASS":
        # AMASS target floor is XY ground plane for template in OpenGL Y-up space (XZ ground plane).
        # Since the Blender model is Z-up (and not Y-up) for rest/template pose, we need to adjust root node rotation to ensure that the resulting animated body is on Blender XY ground plane.
        bone_name = "root"
        armature.pose.bones[bone_name].rotation_mode = 'QUATERNION'
        armature.pose.bones[bone_name].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), radians(-90))
        armature.pose.bones[bone_name].keyframe_insert('rotation_quaternion', frame=bpy.data.scenes[0].frame_current)
        armature.pose.bones[bone_name].keyframe_insert(data_path="location", frame=bpy.data.scenes[0].frame_current)


def set_pose_from_rodrigues(armature, bone_name, rodrigues, rodrigues_reference=None, frame=1):  # I wish frame=bpy.data.scenes[0].frame_current worked here, but it doesn't
    rod = Vector((rodrigues[0], rodrigues[1], rodrigues[2]))
    angle_rad = rod.length
    axis = rod.normalized()

    pbone = armature.pose.bones[bone_name]
    pbone.rotation_mode = 'QUATERNION'
    quat = Quaternion(axis, angle_rad)

    if rodrigues_reference is None:
        pbone.rotation_quaternion = quat
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
        pbone.rotation_quaternion = quat_result

    pbone.keyframe_insert(data_path="rotation_quaternion", frame=frame)

    if bone_name == 'pelvis':
        pbone.keyframe_insert('location', frame=frame)
        
        
    return


def transfer_uv(mesh_from, mesh_to):
    deselect()
    select_object(mesh_to)
    select_object(mesh_from)
    set_active_object(mesh_from)
    bpy.ops.object.join_uvs()
