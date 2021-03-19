# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "SMPL-X for Blender",
    "author": "Joachim Tesch, Max Planck Institute for Intelligent Systems",
    "version": (2021, 3, 19),
    "blender": (2, 80, 0),
    "location": "Viewport > Right panel",
    "description": "SMPL-X for Blender",
    "wiki_url": "https://smpl-x.is.tue.mpg.de/",
    "category": "SMPL-X"}

import bpy
import bmesh
from bpy_extras.io_utils import ExportHelper # ExportHelper is a helper class, defines filename and invoke() function which calls the file selector.

from mathutils import Vector
from math import radians
import numpy as np
import os
import pickle

from bpy.props import ( BoolProperty, EnumProperty, FloatProperty, PointerProperty )
from bpy.types import ( PropertyGroup )

# SMPL-X globals
SMPLX_MODELFILE = "smplx_model_20210319.blend"

SMPL_JOINT_NAMES = {
    0:  'Pelvis',
    1:  'L_Hip',        4:  'L_Knee',            7:  'L_Ankle',           10: 'L_Foot',
    2:  'R_Hip',        5:  'R_Knee',            8:  'R_Ankle',           11: 'R_Foot',
    3:  'Spine1',       6:  'Spine2',            9:  'Spine3',            12: 'Neck',            15: 'Head',
    13: 'L_Collar',     16: 'L_Shoulder',       18: 'L_Elbow',            20: 'L_Wrist',         22: 'L_Hand',
    14: 'R_Collar',     17: 'R_Shoulder',       19: 'R_Elbow',            21: 'R_Wrist',         23: 'R_Hand',
}
smplx_joints = len(SMPL_JOINT_NAMES) 
# End SMPL-X globals

def rodrigues_from_pose(armature, bone_name):
    # Ensure that rotation mode is AXIS_ANGLE so the we get a correct readout of current pose
    armature.pose.bones[bone_name].rotation_mode = 'AXIS_ANGLE'
    axis_angle = armature.pose.bones[bone_name].rotation_axis_angle

    angle = axis_angle[0]

    rodrigues = Vector((axis_angle[1], axis_angle[2], axis_angle[3]))
    rodrigues.normalize()
    rodrigues = rodrigues * angle
    return rodrigues

def update_corrective_poseshapes(self, context):
    if self.smplx_corrective_poseshapes:
        bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')
    else:
        bpy.ops.object.smplx_reset_poseshapes('EXEC_DEFAULT')

# Property groups for UI
class PG_SMPLXProperties(PropertyGroup):

    smplx_gender: EnumProperty(
        name = "Model",
        description = "SMPL-X model",
        items = [ ("female", "Female", ""), ("male", "Male", ""), ("neutral", "Neutral", "") ]
    )

    smplx_texture: EnumProperty(
        name = "",
        description = "SMPL-X model texture",
        items = [ ("NONE", "None", ""), ("UV_GRID", "UV Grid", ""), ("COLOR_GRID", "Color Grid", "") ]
    )

    smplx_corrective_poseshapes: BoolProperty(
        name = "Corrective Pose Shapes",
        description = "Enable/disable corrective pose shapes of SMPL-X model",
        update = update_corrective_poseshapes
    )

    smplx_export_setting_shape_keys: EnumProperty(
        name = "",
        description = "Blend shape export settings",
        items = [ ("SHAPE_POSE", "All: Shape + Posecorrectives", "Export shape keys for body shape and pose correctives"), ("SHAPE", "Reduced: Shape space only", "Export only shape keys for body shape"), ("NONE", "None: Apply shape space", "Do not export any shape keys, shape keys for body shape will be baked into mesh") ],
    )

class SMPLXAddGender(bpy.types.Operator):
    bl_idname = "scene.smplx_add_gender"
    bl_label = "Add"
    bl_description = ("Add SMPL-X model of selected gender to scene")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in Object Mode
            if (context.active_object is None) or (context.active_object.mode == 'OBJECT'):
                return True
            else: 
                return False
        except: return False

    def execute(self, context):
        gender = context.window_manager.smplx_tool.smplx_gender
        print("Adding gender: " + gender)

        path = os.path.dirname(os.path.realpath(__file__))
        objects_path = os.path.join(path, "data", SMPLX_MODELFILE, "Object")
        object_name = "SMPLX-mesh-" + gender

        bpy.ops.wm.append(filename=object_name, directory=str(objects_path))

        # Select imported mesh
        object_name = context.selected_objects[0].name
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = bpy.data.objects[object_name]
        bpy.data.objects[object_name].select_set(True)

        return {'FINISHED'}

class SMPLXSetTexture(bpy.types.Operator):
    bl_idname = "scene.smplx_set_texture"
    bl_label = "Set"
    bl_description = ("Set selected texture")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in active object is mesh
            if (context.object.type == 'MESH'):
                return True
            else:
                return False
        except: return False

    def execute(self, context):
        texture = context.window_manager.smplx_tool.smplx_texture
        print("Setting texture: " + texture)

        obj = bpy.context.object
        if (len(obj.data.materials) == 0) or (obj.data.materials[0] is None):
            self.report({'WARNING'}, "Selected mesh has no material: %s" % obj.name)
            return {'CANCELLED'}

        mat = obj.data.materials[0]
        links = mat.node_tree.links
        nodes = mat.node_tree.nodes

        # Find texture node
        node_texture = None
        for node in nodes:
            if node.type == 'TEX_IMAGE':
                node_texture = node
                break

        # Find shader node
        node_shader = None
        for node in nodes:
            if node.type.startswith('BSDF'):
                node_shader = node
                break

        if texture == 'NONE':
            # Unlink texture node
            if node_texture is not None:
                for link in node_texture.outputs[0].links:
                    links.remove(link)

                nodes.remove(node_texture)

                # 3D Viewport still shows previous texture when texture link is removed via script.
                # As a workaround we trigger desired viewport update by setting color value.
                node_shader.inputs[0].default_value = node_shader.inputs[0].default_value
        else:
            if node_texture is None:
                node_texture = nodes.new(type="ShaderNodeTexImage")

            if texture == 'UV_GRID':
                if texture not in bpy.data.images:
                    bpy.ops.image.new(name=texture, generated_type='UV_GRID')

                image = bpy.data.images[texture]
            else:
                if texture not in bpy.data.images:
                    bpy.ops.image.new(name=texture, generated_type='COLOR_GRID')

                image = bpy.data.images[texture]

            node_texture.image = image

            # Link texture node to shader node if not already linked
            if len(node_texture.outputs[0].links) == 0:
                links.new(node_texture.outputs[0], node_shader.inputs[0])

        return {'FINISHED'}

class SMPLXRandomShapes(bpy.types.Operator):
    bl_idname = "object.smplx_random_shapes"
    bl_label = "Random Shapes"
    bl_description = ("Sets all shape blend shape keys to a random value")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return context.object.type == 'MESH'
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Shape"):
                key_block.value = np.random.normal(0.0, 1.0)

        bpy.ops.object.smplx_update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}

class SMPLXResetShapes(bpy.types.Operator):
    bl_idname = "object.smplx_reset_shapes"
    bl_label = "Reset"
    bl_description = ("Resets all blend shape keys for shape")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return context.object.type == 'MESH'
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Shape"):
                key_block.value = 0.0

        bpy.ops.object.smplx_update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}

class SMPLXSnapGroundPlane(bpy.types.Operator):
    bl_idname = "object.smplx_snap_ground_plane"
    bl_label = "Snap To Ground Plane"
    bl_description = ("Snaps mesh to the XY ground plane")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return ((context.object.type == 'MESH') or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')

        obj = bpy.context.object
        if obj.type == 'ARMATURE':
                    armature = obj
                    obj = bpy.context.object.children[0]
        else:
            armature = obj.parent

        # Get vertices with applied skin modifier in object coordinates
        depsgraph = context.evaluated_depsgraph_get()
        object_eval = obj.evaluated_get(depsgraph)
        mesh_from_eval = object_eval.to_mesh()

        # Get vertices in world coordinates
        matrix_world = obj.matrix_world
        vertices_world = [matrix_world @ vertex.co for vertex in mesh_from_eval.vertices]
        z_min = (min(vertices_world, key=lambda item: item.z)).z
        object_eval.to_mesh_clear() # Remove temporary mesh

        # Translate armature edit bones
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        for edit_bone in armature.data.edit_bones:
            if edit_bone.name != "root":
                edit_bone.translate(Vector((0.0, 0.0, -z_min)))

        # Translate skinned mesh and apply translation
        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = obj
        obj.location = (0.0, 0.0, -z_min)

        bpy.ops.object.transform_apply(location = True)

        return {'FINISHED'}

class SMPLXUpdateJointLocations(bpy.types.Operator):
    bl_idname = "object.smplx_update_joint_locations"
    bl_label = "Update Joint Locations"
    bl_description = ("Update joint locations after shape/expression changes")
    bl_options = {'REGISTER', 'UNDO'}

    j_regressor_male = None
    j_regressor_female = None

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')


        if self.j_regressor_female is None:
            path = os.path.dirname(os.path.realpath(__file__))
            regressor_path = os.path.join(path, "data", "smplx_joint_regressor_female.npz")
            with np.load(regressor_path) as data:
                self.j_regressor_female = data['joint_regressor']

        if self.j_regressor_male is None:
            path = os.path.dirname(os.path.realpath(__file__))
            regressor_path = os.path.join(path, "data", "smplx_joint_regressor_male.npz")
            with np.load(regressor_path) as data:
                self.j_regressor_male = data['joint_regressor']

        if "female" in obj.name:
            j_regressor = self.j_regressor_female
        else:
            j_regressor = self.j_regressor_male

        # Store current bone rotations
        armature = obj.parent

        bone_rotations = {}
        for pose_bone in armature.pose.bones:
            pose_bone.rotation_mode = 'AXIS_ANGLE'
            axis_angle = pose_bone.rotation_axis_angle
            bone_rotations[pose_bone.name] = (axis_angle[0], axis_angle[1], axis_angle[2], axis_angle[3])

        # Set model in default pose
        for bone in armature.pose.bones:
            bpy.ops.object.smplx_reset_poseshapes('EXEC_DEFAULT')
            bone.rotation_mode = 'AXIS_ANGLE'
            bone.rotation_axis_angle = (0, 0, 1, 0)

        # Reset corrective poseshapes if used
        if context.window_manager.smplx_tool.smplx_corrective_poseshapes:
            bpy.ops.object.smplx_reset_poseshapes('EXEC_DEFAULT')

        # Get vertices with applied skin modifier
        depsgraph = context.evaluated_depsgraph_get()
        object_eval = obj.evaluated_get(depsgraph)
        mesh_from_eval = object_eval.to_mesh()

        # Get Blender vertices as numpy matrix
        vertices_np = np.zeros((len(mesh_from_eval.vertices)*3), dtype=np.float)
        mesh_from_eval.vertices.foreach_get("co", vertices_np)
        vertices_matrix = np.reshape(vertices_np, (len(mesh_from_eval.vertices), 3))
        object_eval.to_mesh_clear() # Remove temporary mesh

        # Note: Current joint regressor uses 6890 vertices as input which is slow numpy operation
        joint_locations = j_regressor @ vertices_matrix

        # Set new bone joint locations
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')

        for index in range(smplx_joints):
            bone = armature.data.edit_bones[SMPLX_JOINT_NAMES[index]]
            bone.head = (0.0, 0.0, 0.0)
            bone.tail = (0.0, 0.0, 0.1)

            bone_start = Vector(joint_locations[index])
            bone.translate(bone_start)

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = obj

        # Restore pose
        for pose_bone in armature.pose.bones:
            pose_bone.rotation_mode = 'AXIS_ANGLE'
            pose_bone.rotation_axis_angle = bone_rotations[pose_bone.name]

        # Restore corrective poseshapes if used
        if context.window_manager.smplx_tool.smplx_corrective_poseshapes:
            bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')

        return {'FINISHED'}

class SMPLXSetPoseshapes(bpy.types.Operator):
    bl_idname = "object.smplx_set_poseshapes"
    bl_label = "Set Pose Shapes"
    bl_description = ("Sets corrective poseshapes for current pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object and parent is armature
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    # https://github.com/gulvarol/surreal/blob/master/datageneration/main_part1.py
    # Computes rotation matrix through Rodrigues formula as in cv2.Rodrigues
    def rodrigues_to_mat(self, rotvec):
        theta = np.linalg.norm(rotvec)
        r = (rotvec/theta).reshape(3, 1) if theta > 0. else rotvec
        cost = np.cos(theta)
        mat = np.asarray([[0, -r[2], r[1]],
                        [r[2], 0, -r[0]],
                        [-r[1], r[0], 0]])
        return(cost*np.eye(3) + (1-cost)*r.dot(r.T) + np.sin(theta)*mat)

    # https://github.com/gulvarol/surreal/blob/master/datageneration/main_part1.py
    # Calculate weights of pose corrective blend shapes
    # Input is pose of all 24 joints, output is weights for all joints except pelvis (23)
    def rodrigues_to_posecorrective_weight(self, pose):
        joints_posecorrective = smplx_joints
        rod_rots = np.asarray(pose).reshape(joints_posecorrective, 3)
        mat_rots = [self.rodrigues_to_mat(rod_rot) for rod_rot in rod_rots]
        bshapes = np.concatenate([(mat_rot - np.eye(3)).ravel() for mat_rot in mat_rots[1:]])
        return(bshapes)

    def execute(self, context):
        obj = bpy.context.object

        # Get armature pose in rodrigues representation
        if obj.type == 'ARMATURE':
            armature = obj
            obj = bpy.context.object.children[0]
        else:
            armature = obj.parent

        pose = [0.0] * (smplx_joints * 3)

        for index in range(smplx_joints):
            joint_name = SMPLX_JOINT_NAMES[index]
            joint_pose = rodrigues_from_pose(armature, joint_name)
            pose[index*3 + 0] = joint_pose[0]
            pose[index*3 + 1] = joint_pose[1]
            pose[index*3 + 2] = joint_pose[2]

        # print("Current pose: " + str(pose))

        poseweights = self.rodrigues_to_posecorrective_weight(pose)

        # Set weights for pose corrective shape keys
        for index, weight in enumerate(poseweights):
            obj.data.shape_keys.key_blocks["Pose%03d" % index].value = weight

        # Set checkbox without triggering update function
        context.window_manager.smplx_tool["smplx_corrective_poseshapes"] = True

        return {'FINISHED'}

class SMPLXResetPoseshapes(bpy.types.Operator):
    bl_idname = "object.smplx_reset_poseshapes"
    bl_label = "Reset"
    bl_description = ("Resets corrective poseshapes for current pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object and parent is armature
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'ARMATURE':
            obj = bpy.context.object.children[0]

        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Pose"):
                key_block.value = 0.0

        return {'FINISHED'}

class SMPLXWritePose(bpy.types.Operator):
    bl_idname = "object.smplx_write_pose"
    bl_label = "Write Pose"
    bl_description = ("Writes SMPL-X pose thetas to console window")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return (context.object.type == 'MESH') or (context.object.type == 'ARMATURE')
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        # Get armature pose in rodrigues representation
        pose = [0.0] * (len(SMPLX_JOINT_NAMES) * 3)

        for index in range(len(SMPLX_JOINT_NAMES)):
            joint_name = SMPLX_JOINT_NAMES[index]
            joint_pose = rodrigues_from_pose(armature, joint_name)
            pose[index*3 + 0] = joint_pose[0]
            pose[index*3 + 1] = joint_pose[1]
            pose[index*3 + 2] = joint_pose[2]

        print("pose = " + str(pose))

        return {'FINISHED'}

class SMPLXResetPose(bpy.types.Operator):
    bl_idname = "object.smplx_reset_pose"
    bl_label = "Reset Pose"
    bl_description = ("Resets pose to default zero pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        for bone in armature.pose.bones:
            bone.rotation_mode = 'AXIS_ANGLE'
            bone.rotation_axis_angle = (0, 0, 1, 0)

        # Reset corrective pose shapes
        bpy.ops.object.smplx_reset_poseshapes('EXEC_DEFAULT')

        return {'FINISHED'}

class SMPLXExportUnityFBX(bpy.types.Operator, ExportHelper):
    bl_idname = "object.smplx_export_unity_fbx"
    bl_label = "Export Unity FBX"
    bl_description = ("Export skinned mesh to Unity in FBX format")
    bl_options = {'REGISTER', 'UNDO'}

    # ExportHelper mixin class uses this
    filename_ext = ".fbx"

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return (context.object.type == 'MESH')
        except: return False

    def execute(self, context):

        obj = bpy.context.object
        export_shape_keys = context.window_manager.smplx_tool.smplx_export_setting_shape_keys

        armature_original = obj.parent
        skinned_mesh_original = obj

        # Operate on temporary copy of skinned mesh and armature
        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh_original.select_set(True)
        armature_original.select_set(True)
        bpy.context.view_layer.objects.active = skinned_mesh_original
        bpy.ops.object.duplicate()
        skinned_mesh = bpy.context.object
        armature = skinned_mesh.parent

        # Reset pose
        bpy.ops.object.smplx_reset_pose('EXEC_DEFAULT')

        if export_shape_keys != 'SHAPE_POSE':
            # Remove pose corrective shape keys
            print('Removing pose corrective shape keys')
            num_shape_keys = len(skinned_mesh.data.shape_keys.key_blocks.keys())

            current_shape_key_index = 0
            for index in range(0, num_shape_keys):
                bpy.context.object.active_shape_key_index = current_shape_key_index

                if bpy.context.object.active_shape_key is not None:
                    if bpy.context.object.active_shape_key.name.startswith('Pose'):
                        bpy.ops.object.shape_key_remove(all=False)
                    else:
                        current_shape_key_index = current_shape_key_index + 1        

        if export_shape_keys == 'NONE':
            # Bake and remove shape keys
            print("Baking shape and removing shape keys for shape")

            # Create shape mix for current shape
            bpy.ops.object.shape_key_add(from_mix=True)
            num_shape_keys = len(skinned_mesh.data.shape_keys.key_blocks.keys())

            # Remove all shape keys except newly added one
            bpy.context.object.active_shape_key_index = 0
            for count in range(0, num_shape_keys):
                bpy.ops.object.shape_key_remove(all=False)

        # Model (skeleton and skinned mesh) needs to have rotation of (90, 0, 0) when exporting so that it will have rotation (0, 0, 0) when imported into Unity
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh.select_set(True)
        skinned_mesh.rotation_euler = (radians(-90), 0, 0)
        bpy.context.view_layer.objects.active = skinned_mesh
        bpy.ops.object.transform_apply(rotation = True)
        skinned_mesh.rotation_euler = (radians(90), 0, 0)
        skinned_mesh.select_set(False)

        armature.select_set(True)
        armature.rotation_euler = (radians(-90), 0, 0)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.transform_apply(rotation = True)
        armature.rotation_euler = (radians(90), 0, 0)

        # Select armature and skinned mesh for export
        skinned_mesh.select_set(True)

        # Rename armature and skinned mesh to not contain Blender copy suffix
        if "female" in skinned_mesh.name:
            gender = "female"
        else:
            gender = "male"

        target_mesh_name = "SMPLX-mesh-%s" % gender
        target_armature_name = "SMPLX-%s" % gender

        if target_mesh_name in bpy.data.objects:
            bpy.data.objects[target_mesh_name].name = "SMPLX-temp-mesh"
        skinned_mesh.name = target_mesh_name

        if target_armature_name in bpy.data.objects:
            bpy.data.objects[target_armature_name].name = "SMPLX-temp-armature"
        armature.name = target_armature_name

        bpy.ops.export_scene.fbx(filepath=self.filepath, use_selection=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False)

        print("Exported: " + self.filepath)

        # Remove temporary copies of armature and skinned mesh
        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh.select_set(True)
        armature.select_set(True)
        bpy.ops.object.delete()

        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh_original.select_set(True)
        bpy.context.view_layer.objects.active = skinned_mesh_original

        if "SMPLX-temp-mesh" in bpy.data.objects:
            bpy.data.objects["SMPLX-temp-mesh"].name = target_mesh_name

        if "SMPLX-temp-armature" in bpy.data.objects:
            bpy.data.objects["SMPLX-temp-armature"].name = target_armature_name

        return {'FINISHED'}

class SMPLX_PT_Model(bpy.types.Panel):
    bl_label = "SMPL-X Model"
    bl_category = "SMPLX"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):

        layout = self.layout
        col = layout.column(align=True)
        
        row = col.row(align=True)
        col.prop(context.window_manager.smplx_tool, "smplx_gender")
        col.operator("scene.smplx_add_gender", text="Add")

        col.separator()
        col.label(text="Texture:")
        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.prop(context.window_manager.smplx_tool, "smplx_texture")
        split.operator("scene.smplx_set_texture", text="Set")

class SMPLX_PT_Shape(bpy.types.Panel):
    bl_label = "Shape"
    bl_category = "SMPLX"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.operator("object.smplx_random_shapes")
        split.operator("object.smplx_reset_shapes")
        col.separator()

        col.operator("object.smplx_snap_ground_plane")
        col.separator()

        col.operator("object.smplx_update_joint_locations")

class SMPLX_PT_Pose(bpy.types.Panel):
    bl_label = "Pose"
    bl_category = "SMPLX"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.prop(context.window_manager.smplx_tool, "smplx_corrective_poseshapes")
        col.separator()
        col.operator("object.smplx_set_poseshapes")
        col.separator()
        col.operator("object.smplx_write_pose")
        col.separator()

class SMPLX_PT_Export(bpy.types.Panel):
    bl_label = "Export"
    bl_category = "SMPLX"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.label(text="Shape Keys (Blend Shapes):")
        col.prop(context.window_manager.smplx_tool, "smplx_export_setting_shape_keys")
        col.separator()
        col.separator()

        col.operator("object.smplx_export_unity_fbx")
        col.separator()

#        export_button = col.operator("export_scene.obj", text="Export OBJ [m]", icon='EXPORT')
#        export_button.global_scale = 1.0
#        export_button.use_selection = True
#        col.separator()

        row = col.row(align=True)
        row.operator("ed.undo", icon='LOOP_BACK')
        row.operator("ed.redo", icon='LOOP_FORWARDS')
        col.separator()

        (year, month, day) = bl_info["version"]
        col.label(text="Version: %s-%s-%s" % (year, month, day))

classes = [
    PG_SMPLXProperties,
    SMPLXAddGender,
    SMPLXSetTexture,
    SMPLXRandomShapes,
    SMPLXResetShapes,
    SMPLXSnapGroundPlane,
    SMPLXUpdateJointLocations,
    SMPLXSetPoseshapes,
    SMPLXResetPoseshapes,
    SMPLXWritePose,
    SMPLXResetPose,
    SMPLXExportUnityFBX,
    SMPLX_PT_Model,
    SMPLX_PT_Shape,
    SMPLX_PT_Pose,
    SMPLX_PT_Export
]

def register():
    from bpy.utils import register_class
    for cls in classes:
        bpy.utils.register_class(cls)

    # Store properties under WindowManager (not Scene) so that they are not saved in .blend files and always show default values after loading
    bpy.types.WindowManager.smplx_tool = PointerProperty(type=PG_SMPLXProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.WindowManager.smplx_tool

if __name__ == "__main__":
    register()
