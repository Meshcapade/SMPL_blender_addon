import bpy
import os
import numpy as np
import json
import copy
import pickle

from bpy.props import (
    BoolProperty,
    StringProperty,
    EnumProperty,
    IntProperty
)
from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
)
from .globals import (
    SMPLX_MODELFILE,
    SMPLH_MODELFILE,
    SUPR_MODELFILE,
    PATH,
    LEFT_HAND_RELAXED,
    RIGHT_HAND_RELAXED,
    MODEL_JOINT_NAMES,
    MODEL_BODY_JOINTS,
    MODEL_HAND_JOINTS,
)
from .blender import (
    set_pose_from_rodrigues,
    rodrigues_from_pose,
    setup_bone,
    correct_for_anim_format,
    key_all_pose_correctives,
)

from mathutils import Vector, Quaternion
from math import radians

class OP_LoadAvatar(bpy.types.Operator, ImportHelper):
    bl_idname = "object.load_avatar"
    bl_label = "Load Avatar"
    bl_description = ("Load a file that contains all the parameters for a SMPL family body")
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.npz",
        options={'HIDDEN'}
    )

    anim_format: EnumProperty(
        name="Format",
        items=(
            ("AMASS", "AMASS (Y-up)", ""),
            ("blender", "Blender (Z-up)", ""),
        ),
    )

    SMPL_version: EnumProperty(
        name="SMPL Version",
        items=(
            #("guess", "Guess", ""),
            ("SMPLX", "SMPL-X", ""),
            ("SMPLH", "SMPL-H", ""),
            ("SUPR", "SUPR", ""),
        ),
    )

    gender_override: EnumProperty(
        name="Gender Override",
        items=(
            ("disabled", "Disabled", ""),
            ("female", "Female", ""),
            ("male", "Male", ""),
            ("neutral", "Neutral", ""),
        ),
    )

    hand_pose: EnumProperty(
        name="Hand Pose Override",
        items=[
            ("disabled", "Disabled", ""),
            ("relaxed", "Relaxed", ""),
            ("flat", "Flat", ""),
        ]
    )

    keyframe_corrective_pose_weights: BoolProperty(
        name="Use keyframed corrective pose weights",
        description="Keyframe the weights of the corrective pose shapes for each frame. This increases animation load time and slows down editor real-time playback.",
        default=False
    )

    target_framerate: IntProperty(
        name="Target framerate [fps]",
        description="Target framerate for animation in frames-per-second. Lower values will speed up import time.",
        default=30,
        min = 1,
        max = 120
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        target_framerate = self.target_framerate

        # Load .npz file
        print("Loading: " + self.filepath)
        with np.load(self.filepath) as data:
            # Check for valid AMASS file
            error_string = ""
            if "trans" not in data:
                error_string += "\n -trans"

            if "gender" not in data:
                error_string += "\n -gender"

            if "mocap_frame_rate" in data:
                fps_key = "mocap_frame_rate"
            elif "mocap_framerate" in data:
                fps_key = "mocap_framerate"
            elif "fps" in data:
                fps_key = "fps"

            if not fps_key:
                error_string += "\n -fps or mocap_framerate or mocap_frame_rate"
            else: 
                fps = int(data[fps_key])

            if "betas" not in data:
                error_string += "\n -betas"

            if "poses" not in data:
                error_string += "\n -poses"
        
            if error_string:
                self.report({"ERROR"}, "the following keys are missing from the .npz: " + error_string)
                return {"CANCELLED"}

            trans = data["trans"]

            if self.gender_override != "disabled":
                gender = self.gender_override
            else:
                gender = str(data["gender"])

            betas = data["betas"]
            poses = data["poses"]

            if fps < target_framerate:
                self.report({"ERROR"}, f"Mocap framerate ({fps}) below target framerate ({target_framerate})")
                return {"CANCELLED"}
            
            SMPL_version = self.SMPL_version

        if context.active_object is not None:
            bpy.ops.object.mode_set(mode='OBJECT')

        print ("gender: " + gender)
        print ("fps: " + str(fps))

        # Add gender specific model
        context.window_manager.smpl_tool.gender = gender
        context.window_manager.smpl_tool.SMPL_version = SMPL_version

        if self.hand_pose != 'disabled':
            context.window_manager.smpl_tool.hand_pose = self.hand_pose

        bpy.ops.scene.create_avatar()

        obj = context.view_layer.objects.active
        armature = obj.parent

        # Append animation name to armature name
        armature.name = armature.name + "_" + os.path.basename(self.filepath).replace(".npz", "")

        context.scene.render.fps = target_framerate
        context.scene.frame_start = 1

        # Set shape and update joint locations
        # TODO once we have the regressor for SMPLH, we can remove this condition
        if SMPL_version != 'SMPLH':
            bpy.ops.object.mode_set(mode='OBJECT')
            for index, beta in enumerate(betas):
                key_block_name = f"Shape{index:03}"

                if key_block_name in obj.data.shape_keys.key_blocks:
                    obj.data.shape_keys.key_blocks[key_block_name].value = beta
                else:
                    print(f"ERROR: No key block for: {key_block_name}")

        bpy.ops.object.update_joint_locations('EXEC_DEFAULT')

        # Keyframe poses
        step_size = int(fps / target_framerate)

        num_frames = trans.shape[0]
        num_keyframes = int(num_frames / step_size)

        if self.keyframe_corrective_pose_weights:
            print(f"Adding pose keyframes with keyframed corrective pose weights: {num_keyframes}")
        else:
            print(f"Adding pose keyframes: {num_keyframes}")

        # Set end frame if we don't have any previous animations in the scene
        if (len(bpy.data.actions) == 0) or (num_keyframes > context.scene.frame_end):
            context.scene.frame_end = num_keyframes

        joints_to_use = MODEL_JOINT_NAMES[SMPL_version].value

        # override hand pose if it's selected
        # don't pose the hands every frame if we're overriding it
        if self.hand_pose != 'disabled':
            bpy.ops.object.set_hand_pose('EXEC_DEFAULT')

            if SMPL_version == 'SMPLH':
                joints_to_use = joints_to_use[:22]
            else:
                joints_to_use = joints_to_use[:25]

        for index, frame in enumerate(range(0, num_frames, step_size)):
            if (index % 100) == 0:
                print(f"  {index}/{num_keyframes}")
            current_pose = poses[frame].reshape(-1, 3)
            current_trans = trans[frame]

            for bone_index, bone_name in enumerate(joints_to_use):
                if bone_name == "pelvis":
                    # there's a scale mismatch somewhere and the global translation is off by a factor of 100
                    armature.pose.bones[bone_name].location = current_trans*100
                    armature.pose.bones[bone_name].keyframe_insert('location', frame=index+1)

                # Keyframe bone rotation
                set_pose_from_rodrigues(armature, bone_name, current_pose[bone_index], frame=index+1)

            if self.keyframe_corrective_pose_weights:
                # Calculate corrective poseshape weights for current pose and keyframe them.
                # Note: This significantly increases animation load time and also reduces real-time playback speed in Blender viewport.
                bpy.ops.object.set_pose_correctives('EXEC_DEFAULT')
                key_all_pose_correctives(obj=obj, index=index+1)

        print(f"  {num_keyframes}/{num_keyframes}")
        context.scene.frame_set(1)

        correct_for_anim_format(self.anim_format, armature)
        bpy.ops.object.snap_to_ground_plane('EXEC_DEFAULT')
        armature.keyframe_insert(data_path="location", frame=bpy.data.scenes[0].frame_current)

        return {'FINISHED'}


class OP_CreateAvatar(bpy.types.Operator):
    bl_idname = "scene.create_avatar"
    bl_label = "Create Avatar"
    bl_description = ("Create a SMPL family avatar at the scene origin.  \nnote: SMPLH is missing the joint regressor so you can't modify it's shape")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in Object Mode
            return (context.active_object is None) or (context.active_object.mode == 'OBJECT')
        except: return False

    def execute(self, context):
        gender = context.window_manager.smpl_tool.gender
        SMPL_version = context.window_manager.smpl_tool.SMPL_version

        if SMPL_version == 'SMPLX':
            # Use 300 shape model by default if available
            model_file = SMPLX_MODELFILE

        elif SMPL_version == 'SUPR':
            model_file = SUPR_MODELFILE

        # for now, the SMPLH option has been removed from the properties because we don't have regressors for it, 
        # so afm and a bunch of other stuff doesn't work
        elif SMPL_version == "SMPLH":
            model_file = SMPLH_MODELFILE

        else:
            model_file = "error bad SMPL_version"

        objects_path = os.path.join(PATH, "data", model_file, "Object")
        object_name = SMPL_version + "-mesh-" + gender

        bpy.ops.wm.append(filename=object_name, directory=str(objects_path))

        # Select imported mesh
        object_name = context.selected_objects[0].name
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = bpy.data.objects[object_name]
        bpy.data.objects[object_name].select_set(True)

        #define custom properties on the avatar itself to store this kind of data so we can use it whenever we need to
        bpy.context.object['gender'] = gender
        bpy.context.object['SMPL_version'] = SMPL_version

        # add a texture and change the texture option based on the gender
        # male texture if it's a male, female texture if it's female or neutral
        if gender == 'male':
            context.window_manager.smpl_tool.texture = "m"
        else:
            context.window_manager.smpl_tool.texture = "f"

        bpy.ops.object.set_texture()
        bpy.ops.object.reset_body_shape('EXEC_DEFAULT')

        return {'FINISHED'}


class OP_SetTexture(bpy.types.Operator):
    bl_idname = "object.set_texture"
    bl_label = "Set"
    bl_description = ("Set selected texture")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in active object is mesh
            return context.object.type == 'MESH'
        except: return False

    def execute(self, context):
        selection = context.window_manager.smpl_tool.texture
        obj = bpy.context.object

        # if there's no material, add one
        if len(obj.data.materials) == 0:
            # the incoming name of the selected object is in the format of "SUPR-mesh-male"
            # this line turns "SUPR-mesh-male" into "SUPR-male", which is the naming format of the materials
            split_name = obj.name.split("-")
            new_material_name = split_name[0] + "-" + split_name[2]
            material = bpy.data.materials.new(name=new_material_name)
            bpy.context.object.data.materials.append(material)

        else: 
            material = obj.data.materials[0]

        # Enable the use of nodes for the material
        material.use_nodes = True
        node_tree = material.node_tree
        nodes = node_tree.nodes

        # if they selected the male or female texture, we add the normal map and roughness map as well
        if selection in ('m', 'f'):
            # Set the path to the texture files
            albedo_map_path = os.path.join(PATH, "data", selection + "_albedo.png")
            normal_map_path = os.path.join(PATH, "data", selection + "_normal.png")
            roughness_map_path = os.path.join(PATH, "data", selection + "_roughness.png")
            ao_map_path = os.path.join(PATH, "data", "ao.png")
            thickness_map_path = os.path.join(PATH, "data", "thickness.png")

            # Clear default nodes
            for node in nodes:
                nodes.remove(node)

            # Create a new Principled BSDF node
            principled_node = nodes.new(type="ShaderNodeBsdfPrincipled")
            principled_node.location = 0, 0

            # Add a texture node for the albedo map
            albedo_map_node = nodes.new(type="ShaderNodeTexImage")
            albedo_map_node.location = -400, 200
            albedo_map_node.image = bpy.data.images.load(albedo_map_path)
            albedo_map_node.image.colorspace_settings.name = 'sRGB'
            node_tree.links.new(albedo_map_node.outputs["Color"], principled_node.inputs["Base Color"])

            # Add a texture node for the roughness map
            roughness_map_node = nodes.new(type="ShaderNodeTexImage")
            roughness_map_node.location = -400, -200
            roughness_map_node.image = bpy.data.images.load(roughness_map_path)
            roughness_map_node.image.colorspace_settings.name = 'Non-Color'
            node_tree.links.new(roughness_map_node.outputs["Color"], principled_node.inputs["Roughness"])

            # Add a texture node for the normal map
            normal_map_node = nodes.new(type="ShaderNodeTexImage")
            normal_map_node.location = -800, -600
            normal_map_node.image = bpy.data.images.load(normal_map_path)
            normal_map_node.image.colorspace_settings.name = 'Non-Color'
            noamel_map_adjustment = material.node_tree.nodes.new('ShaderNodeNormalMap')
            noamel_map_adjustment.location = -400, -600
            node_tree.links.new(normal_map_node.outputs["Color"], noamel_map_adjustment.inputs["Color"])
            node_tree.links.new(noamel_map_adjustment.outputs["Normal"], principled_node.inputs["Normal"])

            '''
            # TODO add AO
            # Add a texture node for the ambient occlusion map
            ambient_occlusion_node = nodes.new(type="ShaderNodeTexImage")
            ambient_occlusion_node.location = -400, 200
            ambient_occlusion_node.image = bpy.data.images.load(ao_map_path)
            ambient_occlusion_node.image.colorspace_settings.name = 'Non-Color'
            node_tree.links.new(ambient_occlusion_node.outputs["Color"], principled_node.inputs["Ambient Occlusion"])
            #'''
            
            '''
            # TODO add thickness
            # Add a texture node for the thickness map
            thickness_map_node = nodes.new(type="ShaderNodeTexImage")
            thickness_map_node.location = -400, -200
            thickness_map_node.image = bpy.data.images.load(thickness_map_path)
            thickness_map_node.image.colorspace_settings.name = 'Non-Color'
            node_tree.links.new(thickness_map_node.outputs["Color"], principled_node.inputs["Transmission"])
            #'''

            # Set the subsurface properties
            principled_node.inputs["Subsurface"].default_value = 0.001
            principled_node.inputs["Subsurface Color"].default_value = (1, 0, 0, 1)

            # Link the output of the Principled BSDF node to the material output
            output_node = nodes.new(type="ShaderNodeOutputMaterial")
            output_node.location = 400, 0
            node_tree.links.new(principled_node.outputs["BSDF"], output_node.inputs["Surface"])

        else:
            texture_name = context.window_manager.smpl_tool.texture

            if (len(obj.data.materials) == 0) or (obj.data.materials[0] is None):
                self.report({'WARNING'}, "Selected mesh has no material: %s" % obj.name)
                return {'CANCELLED'}

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

            if texture_name == 'NONE':
                # Unlink texture node
                if node_texture is not None:
                    for link in node_texture.outputs[0].links:
                        node_tree.links.remove(link)

                    nodes.remove(node_texture)

                    # 3D Viewport still shows previous texture when texture link is removed via script.
                    # As a workaround we trigger desired viewport update by setting color value.
                    node_shader.inputs[0].default_value = node_shader.inputs[0].default_value
            else:
                if node_texture is None:
                    node_texture = nodes.new(type="ShaderNodeTexImage")

                if (texture_name == 'UV_GRID') or (texture_name == 'COLOR_GRID'):
                    if texture_name not in bpy.data.images:
                        bpy.ops.image.new(name=texture_name, generated_type=texture_name)
                    image = bpy.data.images[texture_name]
                else:
                    if texture_name not in bpy.data.images:
                        texture_path = os.path.join(PATH, "data", texture_name)
                        image = bpy.data.images.load(texture_path)
                    else:
                        image = bpy.data.images[texture_name]

                node_texture.image = image

                # Link texture node to shader node if not already linked
                if len(node_texture.outputs[0].links) == 0:
                    node_tree.links.new(node_texture.outputs[0], node_shader.inputs[0])

        # Switch viewport shading to Material Preview to show texture
        if bpy.context.space_data:
            if bpy.context.space_data.type == 'VIEW_3D':
                bpy.context.space_data.shading.type = 'MATERIAL'

        return {'FINISHED'}


class OP_MeasurementsToShape(bpy.types.Operator):
    bl_idname = "object.measurements_to_shape"
    bl_label = "Measurements To Shape"
    bl_description = ("Calculate and set shape parameters for specified measurements")
    bl_options = {'REGISTER', 'UNDO'}

    betas_regressor_female = None
    betas_regressor_male = None
    betas_regressor_neutral = None

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')

        if self.betas_regressor_female is None:
            regressor_path = os.path.join(PATH, "data", "measurements_to_betas_female.json")
            with open(regressor_path) as f:
                data = json.load(f)
                self.betas_regressor_female = (
                    np.asarray(data["A"]).reshape(-1, 2), 
                    np.asarray(data["B"]).reshape(-1, 1)
                )

        if self.betas_regressor_male is None:
            regressor_path = os.path.join(PATH, "data", "measurements_to_betas_male.json")
            with open(regressor_path) as f:
                data = json.load(f)
                self.betas_regressor_male = (
                    np.asarray(data["A"]).reshape(-1, 2),
                    np.asarray(data["B"]).reshape(-1, 1)
                )

        if self.betas_regressor_neutral is None:
            regressor_path = os.path.join(PATH, "data", "measurements_to_betas_neutral.json")
            with open(regressor_path) as f:
                data = json.load(f)
                self.betas_regressor_neutral = (
                    np.asarray(data["A"]).reshape(-1, 2), 
                    np.asarray(data["B"]).reshape(-1, 1)
                )

        if "female" in obj.name.lower():
            (A, B) = self.betas_regressor_female
        elif "male" in obj.name.lower():
            (A, B) = self.betas_regressor_male
        elif "neutral" in obj.name.lower():
            (A, B) = self.betas_regressor_neutral
        else:
            self.report({"ERROR"}, f"Cannot derive gender from mesh object name: {obj.name}")
            return {"CANCELLED"}

        # Calculate beta values from measurements
        height_cm = context.window_manager.smpl_tool.height
        weight_kg = context.window_manager.smpl_tool.weight

        v_root = pow(weight_kg, 1.0/3.0)
        measurements = np.asarray([[height_cm], [v_root]])
        betas = A @ measurements + B

        num_betas = betas.shape[0]
        for i in range(num_betas):
            name = f"Shape{i:03d}"
            key_block = obj.data.shape_keys.key_blocks[name]
            value = betas[i, 0]

            # Adjust key block min/max range to value
            if value < key_block.slider_min:
                key_block.slider_min = value
            elif value > key_block.slider_max:
                key_block.slider_max = value

            key_block.value = value

        bpy.ops.object.update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}


class OP_RandomBodyShape(bpy.types.Operator):
    bl_idname = "object.random_body_shape"
    bl_label = "Random Body Shape"
    bl_description = ("Sets all shape blendshape keys to a random value")
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

        for i in range(0, 10):
            key_name = f"Shape{'%0.3d' % i}"
            key_block = obj.data.shape_keys.key_blocks.get(key_name)
            beta = np.random.normal(0.0, 1.0) * .75 * context.window_manager.smpl_tool.random_body_mult
            key_block.value = beta

        bpy.ops.object.update_joint_locations('EXEC_DEFAULT')

        context.window_manager.smpl_tool.alert = True

        return {'FINISHED'}
    
    def draw(self, context):
        context.window_manager.smpl_tool.alert = True
    

class OP_RandomFaceShape(bpy.types.Operator):
    bl_idname = "object.random_face_shape"
    bl_label = "Random Face Shape"
    bl_description = ("Sets all shape blendshape keys to a random value")
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

        for i in range(10,299):
            key_name = f"Shape{'%0.3d' % i}"
            key_block = obj.data.shape_keys.key_blocks.get(key_name)
            beta = np.random.normal(0.0, 1.0) * .75 * context.window_manager.smpl_tool.random_face_mult
            key_block.value = beta

        bpy.ops.object.update_joint_locations('EXEC_DEFAULT')
        
        return {'FINISHED'}


class OP_ResetBodyShape(bpy.types.Operator):
    bl_idname = "object.reset_body_shape"
    bl_label = "Reset Body Shape"
    bl_description = ("Resets all blendshape keys for shape")
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

        gender = bpy.context.object['gender']

        # These are the default height and weight values for the three different templates.
        # There is some rounding error that makes applying these numbers not give you exactly 0.0 on the shape keys,
        # but they're so close that you can't tell unless if you look at the numbers. 
        # There are cases where you really want all the shape keys to be 0.0, 
        # so my workaround here is to first apply these height and weight values, then afterwards, manually 0 out the shape keys.
        # This results in a mismatch between the shape keys and the height and weight sliders, 
        # but the shape keys at 0.0 is what's actually being represented in the model, and when you slide the sliders, you can't tell.
        # I think this is the right way to do it.  
        if gender == "male":
            context.window_manager.smpl_tool.height = 178.40813305675982
            context.window_manager.smpl_tool.weight = 84.48267403991704
        elif gender == "female":
            context.window_manager.smpl_tool.height = 165.58187348544598
            context.window_manager.smpl_tool.weight = 69.80320278887571
        elif gender == "neutral":
            context.window_manager.smpl_tool.height = 172.05153398364783
            context.window_manager.smpl_tool.weight = 77.51340327590397

        # this is the step that manually 0's out the shape keys
        for i in range(0,10):
            key_name = f"Shape{'%0.3d' % i}"
            key_block = obj.data.shape_keys.key_blocks.get(key_name)
            key_block.value = 0

        bpy.ops.object.update_joint_locations('EXEC_DEFAULT')
        context.window_manager.smpl_tool.alert = False

        return {'FINISHED'}
    
    def draw(self, context):
        context.window_manager.smpl_tool.alert = False


class OP_ResetFaceShape(bpy.types.Operator):
    bl_idname = "object.reset_face_shape"
    bl_label = "Reset Face Shape"
    bl_description = ("Resets all blendshape keys for shape")
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

        for i in range(10,299):
            key_name = f"Shape{'%0.3d' % i}"
            key_block = obj.data.shape_keys.key_blocks.get(key_name)
            key_block.value = 0

        bpy.ops.object.update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}


class OP_RandomExpressionShape(bpy.types.Operator):
    bl_idname = "object.random_expression_shape"
    bl_label = "Random Facial Expression"
    bl_description = ("Sets all face expression blendshape keys to a random value")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ((context.object.type == 'MESH') and (bpy.context.object['SMPL_version'] != "SMPLH"))
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')

        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith('Exp'):
                key_block.value = np.random.uniform(-1.5, 1.5)

        return {'FINISHED'}


class OP_ResetExpressionShape(bpy.types.Operator):
    bl_idname = "object.reset_expression_shape"
    bl_label = "Reset"
    bl_description = ("Resets all blendshape keys for face expression")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ((context.object.type == 'MESH') and (bpy.context.object['SMPL_version'] != "SMPLH"))
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')

        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith('Exp'):
                key_block.value = 0.0

        return {'FINISHED'}


class OP_SnapToGroundPlane(bpy.types.Operator):
    bl_idname = "object.snap_to_ground_plane"
    bl_label = "Snap To Ground Plane"
    bl_description = ("Snaps mesh to the XY ground plane")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return context.object.type in ('MESH', 'ARMATURE')
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

        # Adjust height of armature so that lowest vertex is on ground plane.
        # Do not apply new armature location transform so that we are later able to show loaded poses at their desired height.
        armature.location.z = armature.location.z - z_min

        return {'FINISHED'}


class OP_UpdateJointLocations(bpy.types.Operator):
    bl_idname = "object.update_joint_locations"
    bl_label = "Update Joint Locations"
    bl_description = ("You only need to click this button if you change the shape keys from the object data tab (not using the plugin)")
    bl_options = {'REGISTER', 'UNDO'}

    j_regressor_female = {}
    j_regressor_male = {}
    j_regressor_neutral = {}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE'))
        except Exception: 
            return False

    def load_regressor(self, gender, betas, SMPL_version):
        # TODO recreate the SUPR joint regressor so that it doesn't include the 100 expression shape keys.  There are two `if SMPL_version == 'supr'` that we will be able to get rid of as a result
        if betas == 10:
            suffix = ""
        elif betas == 300:
            suffix = "_300"
        elif betas == 400:
            suffix = "_400"
        else:
            print(f"ERROR: No betas-to-joints regressor for desired beta shapes [{betas}]")
            return (None, None)

        regressor_path = os.path.join(PATH, "data", f"{SMPL_version}_betas_to_joints_{gender}{suffix}.json")
        with open(regressor_path) as f:
            data = json.load(f)
            return (np.asarray(data["betasJ_regr"]), np.asarray(data["template_J"]))

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')

        SMPL_version = bpy.context.object['SMPL_version']

        # SMPLH is missing the joint regressor so we just want to exit
        if SMPL_version == 'SMPLH':
            return {'CANCELLED'}

        gender = bpy.context.object['gender']
        joint_names = MODEL_JOINT_NAMES[SMPL_version].value
        num_joints = len(joint_names)

        # Get beta shapes
        betas = []
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Shape"):
                betas.append(key_block.value)

        num_betas = len(betas)
        betas = np.array(betas)

        # "Cache regressor files"
        # I think whoever wrote this thought they were caching everything, but they're really just doing it every time this is used, which is bad.
        # TODO we need to actually cache all the files
        self.j_regressor = { num_betas: None }
        self.j_regressor[num_betas] = self.load_regressor(gender, num_betas, SMPL_version.lower())
        (betas_to_joints, template_j) = self.j_regressor[num_betas]
        joint_locations = betas_to_joints @ betas + template_j

        # Set new bone joint locations
        armature = obj.parent
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')

        for index in range(num_joints):
            bone = armature.data.edit_bones[joint_names[index]]
            setup_bone(bone, SMPL_version)

            # Convert joint locations to Blender joint locations
            joint_location = joint_locations[index]

            if SMPL_version in ['SMPLX', 'SUPR']:
                bone_start = Vector((joint_location[0]*100, joint_location[1]*100, joint_location[2]*100))

            bone.translate(bone_start)

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = obj

        return {'FINISHED'}


class OP_CalculatePoseCorrectives(bpy.types.Operator):
    bl_idname = "object.set_pose_correctives"
    bl_label = "Calculate Pose Correctives"
    bl_description = ("Computes pose correctives for the current frame")
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
                        [-r[1], r[0], 0]], dtype=object)
        return(cost*np.eye(3) + (1-cost)*r.dot(r.T) + np.sin(theta)*mat)
    
    def rodrigues_to_quat(self, rotvec):
        theta = np.linalg.norm(rotvec)
        r = (rotvec/theta).reshape(3, 1) if theta > 0. else rotvec
        return(Quaternion(r, theta))

    # https://github.com/gulvarol/surreal/blob/master/datageneration/main_part1.py
    # Calculate weights of pose corrective blendshapes
    # Input is pose of all 55 joints, output is weights for all joints except pelvis
    def rodrigues_to_posecorrective_weight(self, context, pose):
        SMPL_version = bpy.context.object['SMPL_version']
        joint_names = MODEL_JOINT_NAMES[SMPL_version].value
        num_joints = len(joint_names)
        
        if SMPL_version in ('SMPLX', 'SMPLH'):
            rod_rots = np.asarray(pose).reshape(num_joints, 3)
            mat_rots = [self.rodrigues_to_mat(rod_rot) for rod_rot in rod_rots]
            bshapes = np.concatenate([(mat_rot - np.eye(3)).ravel() for mat_rot in mat_rots[1:]])
            return(bshapes)

        elif SMPL_version == 'SUPR':
            rod_rots = np.asarray(pose).reshape(num_joints, 3)
            quats = [self.rodrigues_to_quat(rod_rot) for rod_rot in rod_rots]
            for q in quats:
                qcopy = copy.deepcopy(q)
                q.w = qcopy.x
                q.x = qcopy.y
                q.y = qcopy.z
                q.z = qcopy.w - 1 # same as (1 - qcopy.w) * -1
            bshapes = np.concatenate([quat for quat in quats[0:]])

            return(bshapes)
            
        else:
            return("error")


    def execute(self, context):
        obj = bpy.context.object
        SMPL_version = bpy.context.object['SMPL_version']
        joint_names = MODEL_JOINT_NAMES[SMPL_version].value
        num_joints = len(joint_names)

        # Get armature pose in rodrigues representation
        if obj.type == 'ARMATURE':
            armature = obj
            obj = bpy.context.object.children[0]
        else:
            armature = obj.parent

        pose = [0.0] * (num_joints * 3)

        for index in range(num_joints):
            joint_name = joint_names[index]
            joint_pose = rodrigues_from_pose(armature, joint_name)
            pose[index*3 + 0] = joint_pose[0]
            pose[index*3 + 1] = joint_pose[1]
            pose[index*3 + 2] = joint_pose[2]

        poseweights = self.rodrigues_to_posecorrective_weight(context, pose)

        # TODO for the time being, the SMPLX pose correctives only go to 0-206.  
        # It should be 0-485, but we're not sure why the fingers aren't being written out of the blender-worker  
        if SMPL_version in ['SMPLH', 'SMPLX']:
            poseweights_to_use = poseweights[0:207]
        else:
            poseweights_to_use = poseweights

        # Set weights for pose corrective shape keys
        for index, weight in enumerate(poseweights_to_use):
            obj.data.shape_keys.key_blocks["Pose%03d" % index].value = weight

        return {'FINISHED'}


class OP_CalculatePoseCorrectivesForSequence(bpy.types.Operator):
    bl_idname = "object.set_pose_correctives_for_sequence"
    bl_label = "Calculate Pose Correctives for Entire Sequence"
    bl_description = ("Computes pose correctives for the current time slider range")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object and parent is armature
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False
    
    def execute(self, context):
         # Get the start and end frames from the scene's render settings
        start_frame = bpy.context.scene.frame_start
        end_frame = bpy.context.scene.frame_end

        # Get the object you want to animate
        obj = bpy.context.object

        # Iterate over each frame
        for frame in range(start_frame, end_frame + 1):
            # Set the current frame
            bpy.context.scene.frame_set(frame)
            
            # Update pose shapes
            bpy.ops.object.set_pose_correctives('EXEC_DEFAULT')
            
            # Insert a keyframe
            obj.keyframe_insert(data_path="location", frame=frame)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
            obj.keyframe_insert(data_path="scale", frame=frame)

        return {"FINISHED"}


class OP_ZeroOutPoseCorrectives(bpy.types.Operator):
    bl_idname = "object.zero_out_pose_correctives"
    bl_label = "Zero Out Pose Correctives"
    bl_description = ("Removes pose correctives for current frame")
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


class OP_SetHandpose(bpy.types.Operator):
    bl_idname = "object.set_hand_pose"
    bl_label = "Set"
    bl_description = ("Set selected hand pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return (
                ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or
                (context.object.type == 'ARMATURE')
            )
        except Exception:
            return False

    def execute(self, context):
        obj = bpy.context.object
        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        hand_pose_name = context.window_manager.smpl_tool.hand_pose

        # flat is just an array of 45 0's so we don't want to load it from a file 
        if hand_pose_name == 'flat':
            left_hand_pose = np.zeros(45)
            right_hand_pose = np.zeros(45)
        
        elif hand_pose_name == 'relaxed':
            left_hand_pose = LEFT_HAND_RELAXED
            right_hand_pose = RIGHT_HAND_RELAXED

        else:
            self.report({"ERROR"}, f"Desired hand pose not existing: {hand_pose_name}")
            return {"CANCELLED"}
        
        hand_pose = np.concatenate((left_hand_pose, right_hand_pose)).reshape(-1, 3)

        SMPL_version = bpy.context.object['SMPL_version']
        joint_names = MODEL_JOINT_NAMES[SMPL_version].value
        num_body_joints = MODEL_BODY_JOINTS[SMPL_version].value
        num_hand_joints = MODEL_HAND_JOINTS[SMPL_version].value

        hand_joint_start_index = 1 + num_body_joints

        # SMPLH doesn't have the jaw and eyes, so we leave it alone
        # we +3 for SUPR and SMPLX because they do
        if (SMPL_version == "SUPR" or SMPL_version == "SMPLX"):
            hand_joint_start_index += 3

        for index in range(2 * num_hand_joints):
            pose_rodrigues = hand_pose[index]
            bone_name = joint_names[index + hand_joint_start_index]
            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)

        return {'FINISHED'}


class OP_WritePoseToConsole(bpy.types.Operator):
    bl_idname = "object.write_pose_to_console"
    bl_label = "Write Pose To Console"
    bl_description = ("Writes pose to console window")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return context.object.type in ('MESH', 'ARMATURE')
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        SMPL_version = bpy.context.object['SMPL_version']
        joint_names = MODEL_JOINT_NAMES[SMPL_version].value
        num_joints = len(joint_names)

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        # Get armature pose in rodrigues representation
        pose = [0.0] * (num_joints * 3)

        for index in range(num_joints):
            joint_name = joint_names[index]
            joint_pose = rodrigues_from_pose(armature, joint_name)
            pose[index*3 + 0] = joint_pose[0]
            pose[index*3 + 1] = joint_pose[1]
            pose[index*3 + 2] = joint_pose[2]

        print("\npose = ")
        pose_by_joint = [pose[i:i+3] for i in range(0,len(pose),3)]
        print (*pose_by_joint, sep="\n")

        print ("\npose = " + str(pose))

        print ("\npose = ")
        print (*pose, sep="\n")

        return {'FINISHED'}


class OP_WritePoseToJSON(bpy.types.Operator, ExportHelper):
    bl_idname = "object.write_pose_to_json"
    bl_label = "Write Pose To .json File"
    bl_description = ("Writes pose to a .json file")
    bl_options = {'REGISTER', 'UNDO'}

    # ExportHelper mixin class uses this
    filename_ext = ".json"

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return context.object.type in ('MESH', 'ARMATURE')
        except Exception:
            return False

    def execute(self, context):
        obj = bpy.context.object
        SMPL_version = bpy.context.object['SMPL_version']
        joint_names = MODEL_JOINT_NAMES[SMPL_version].value
        num_joints = len(joint_names)

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        # Get armature pose in rodrigues representation
        pose = [0.0] * (num_joints * 3)

        for index in range(num_joints):
            joint_name = joint_names[index]
            joint_pose = rodrigues_from_pose(armature, joint_name)
            pose[index*3 + 0] = joint_pose[0]
            pose[index*3 + 1] = joint_pose[1]
            pose[index*3 + 2] = joint_pose[2]

        pose_data = {
            "pose": pose,
        }

        with open(self.filepath, "w") as f:
            json.dump(pose_data, f)

        return {'FINISHED'}


class OP_ResetPose(bpy.types.Operator):
    bl_idname = "object.reset_pose"
    bl_label = "Reset Pose"
    bl_description = ("Resets pose to default zero pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return (
                ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or
                (context.object.type == 'ARMATURE')
            )
        except Exception:
            return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        for bone in armature.pose.bones:
            if bone.rotation_mode != 'QUATERNION':
                bone.rotation_mode = 'QUATERNION'
            bone.rotation_quaternion = Quaternion()

        # Reset corrective pose shapes
        bpy.ops.object.zero_out_pose_correctives('EXEC_DEFAULT')

        return {'FINISHED'}


# TODO once we have AFV, we need to replace this with load animation, so you can load any animation onto any body and treat them separately
class OP_LoadPose(bpy.types.Operator, ImportHelper):
    bl_idname = "object.load_pose"
    bl_label = "Load Pose"
    bl_description = ("Load relaxed-hand model pose from file")
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.npz;*.npy;*.json", # this originally worked for .pkl files only, but they have been since removed.  Let us know if that's a problem, we just need a good .pkl file to test against.
        options={'HIDDEN'}
    )

    anim_format: EnumProperty(
        name="Format",
        items=(
            ("AMASS", "AMASS (Y-up)", ""),
            ("blender", "Blender (Z-up)", ""),
        ),
    )

    hand_pose: EnumProperty(
        name="Hand Pose Override",
        items=[
            ("disabled", "Disabled", ""),
            ("relaxed", "Relaxed", ""),
            ("flat", "Flat", ""),
        ]
    )

    # taking this out for now
    '''
    update_shape: BoolProperty(
        name="Update shape parameters",
        description="Update shape parameters using the beta shape information in the loaded file.  This is hard coded to false for SMPLH.",
        default=False
    )
    '''

    frame_number: IntProperty(
        name="Frame Number",
        description="Select the frame of the animation you'd like to load.  Only for .npz files.",
        default = 0,
        min = 0
    )


    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        SMPL_version = bpy.context.object['SMPL_version']
        gender = bpy.context.object['gender']
        joint_names = MODEL_JOINT_NAMES[SMPL_version].value
        num_joints = len(joint_names)
        num_body_joints = MODEL_BODY_JOINTS[SMPL_version].value
        num_hand_joints = MODEL_HAND_JOINTS[SMPL_version].value

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj
            obj = armature.children[0]
            context.view_layer.objects.active = obj # mesh needs to be active object for recalculating joint locations

        print("Loading: " + self.filepath)

        translation = None
        global_orient = None
        body_pose = None
        jaw_pose = None
        #leye_pose = None
        #reye_pose = None
        left_hand_pose = None
        right_hand_pose = None
        betas = None
        expression = None
        with open(self.filepath, "rb") as f:
            extension = os.path.splitext(self.filepath)[1]
            if extension == ".pkl": 
                data = pickle.load(f, encoding="latin1")
            elif extension == ".npz":
                data = np.load(f, allow_pickle=True)
            elif extension == ".npy":
                data = np.load(f, allow_pickle=True)
            elif extension == ".json":
                data = json.load(f)

            if "global_orient" in data:
                global_orient = np.array(data["global_orient"]).reshape(3)

            # it's not working anymore for some reason, but loading the betas onto a body isn't that useful because you could just load the body instead.  
            '''
            if extension in ['.npz', 'pkl']:
                betas = np.array(data["betas"]).reshape(-1).tolist()
    
            # Update shape if selected
            # TODO once we get the SMPLH regressor, we can take the SMPLH part out of this
            if self.update_shape and SMPL_version != 'SMPLH':
                bpy.ops.object.mode_set(mode='OBJECT')

                if (extension in ['.npz', 'pkl']):
                    for index, beta in enumerate(betas):
                        key_block_name = f"Shape{index:03}"

                        if key_block_name in obj.data.shape_keys.key_blocks:
                            obj.data.shape_keys.key_blocks[key_block_name].value = beta
                        else:
                            print(f"ERROR: No key block for: {key_block_name}")

                bpy.ops.object.update_joint_locations('EXEC_DEFAULT')
            '''

            if extension == '.pkl':
                body_pose = np.array(data['body_pose'])

                if body_pose.shape != (1, num_body_joints * 3):
                    print(f"Invalid body pose dimensions: {body_pose.shape}")
                    return {'CANCELLED'}

                body_pose = np.array(data['body_pose']).reshape(num_body_joints, 3)

                jaw_pose = np.array(data["jaw_pose"]).reshape(3)
                # leye_pose = np.array(data["leye_pose"]).reshape(3)
                # reye_pose = np.array(data["reye_pose"]).reshape(3)
                left_hand_pose = np.array(data["left_hand_pose"]).reshape(-1, 3)
                right_hand_pose = np.array(data["right_hand_pose"]).reshape(-1, 3)
                expression = np.array(data["expression"]).reshape(-1).tolist()

                # pose just the body
                for index in range(num_body_joints): 
                    pose_rodrigues = body_pose[index]
                    bone_name = joint_names[index + 1] 
                    set_pose_from_rodrigues(armature, bone_name, pose_rodrigues, frame=bpy.data.scenes[0].frame_current)

            elif extension == '.npz':
                correct_pose_key = 'pose'

                try: 
                    np.array(data['pose'])

                except KeyError:
                    correct_pose_key = "poses"

                print (f"using '{correct_pose_key}'")

                pose_index = max(0, min(self.frame_number, (len(np.array(data[correct_pose_key]))))) # clamp the frame they give you from 0 and the max number of frames in this poses array 
                body_pose = np.array(data[correct_pose_key][pose_index]).reshape(len(joint_names), 3)

                # pose the entire body
                for index in range(len(joint_names)):
                    pose_rodrigues = body_pose[index]
                    bone_name = joint_names[index]
                    set_pose_from_rodrigues(armature, bone_name, pose_rodrigues, frame=bpy.data.scenes[0].frame_current)

            elif extension == '.npy':
                # assuming a .npy containing a single pose
                body_pose = np.array(data).reshape(len(joint_names), 3)
                
                # pose the entire body
                for index in range(len(joint_names)):
                    pose_rodrigues = body_pose[index]
                    bone_name = joint_names[index]
                    set_pose_from_rodrigues(armature, bone_name, pose_rodrigues, frame=bpy.data.scenes[0].frame_current)

            elif extension == '.json':
                with open(self.filepath, "rb") as f:
                    pose_data = json.load(f)
                    
                pose = np.array(pose_data["pose"]).reshape(num_joints, 3)

                for index in range(num_joints):
                    pose_rodrigues = pose[index]
                    bone_name = joint_names[index]
                    set_pose_from_rodrigues(armature, bone_name, pose_rodrigues, frame=bpy.data.scenes[0].frame_current)
                       

        if global_orient is not None:
            set_pose_from_rodrigues(armature, "pelvis", global_orient, frame=bpy.data.scenes[0].frame_current)

        '''
        if translation is not None:
            # Set translation
            armature.location = (translation[0], -translation[2], translation[1])
        '''

        if self.hand_pose != 'disabled':
            context.window_manager.smpl_tool.hand_pose = self.hand_pose
            bpy.ops.object.set_hand_pose('EXEC_DEFAULT')

        # Activate corrective poseshapes
        bpy.ops.object.set_pose_correctives('EXEC_DEFAULT')

        # Set face expression
        if extension == '.pkl':
            set_pose_from_rodrigues(armature, "jaw", jaw_pose, frame=bpy.data.scenes[0].frame_current)

            for index, exp in enumerate(expression):
                key_block_name = f"Exp{index:03}"

                if key_block_name in obj.data.shape_keys.key_blocks:
                    obj.data.shape_keys.key_blocks[key_block_name].value = exp
                else:
                    print(f"ERROR: No key block for: {key_block_name}")

        bpy.ops.object.set_pose_correctives('EXEC_DEFAULT')
        key_all_pose_correctives(obj=obj, index=bpy.data.scenes[0].frame_current)

        correct_for_anim_format(self.anim_format, armature)
        bpy.ops.object.snap_to_ground_plane('EXEC_DEFAULT')
        armature.keyframe_insert(data_path="location", frame=bpy.data.scenes[0].frame_current)

        return {'FINISHED'}


class OP_SetExpressionPreset(bpy.types.Operator):
    bl_idname = "object.set_expression_preset"
    bl_label = "Set Expression Preset"
    bl_description = ("Sets the facial expression to artist created presets")
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ((context.object.type == 'MESH') and (bpy.context.object['SMPL_version'] != "SMPLH"))
        except: return False

    def execute(self, context):
        SMPL_version = bpy.context.object['SMPL_version']


        obj = context.object
        if not obj or not obj.data.shape_keys:
            self.report(
                {"WARNING"}, "Object has no shape keys. Please select a SMPL family mesh."
            )
            return {"CANCELLED"}

        if SMPL_version == 'SMPLX':
            bpy.ops.object.reset_expression_shape('EXEC_DEFAULT')
            presets = {
                "pleasant": [0, .3, 0, -.892, 0, 0, 0, 0, -1.188, 0, .741, -2.83, 0, -1.48, 0, 0, 0, 0, 0, -.89, 0,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, .89, 0, 0, 2.67],
                "happy": [0.9, 0, .741, -2, .27, -.593, -.29, 0, .333, 0, 1.037, -1, 0, .7, .296, 0, 0, -1.037, 0, 0, 0, 1.037, 0, 3],
                "excited": [-.593, .593, .7, -1.55, -.32, -1.186, -.43, -.14, -.26, -.88, 1, -.74, 1, -.593, 0, 0, 0, 0, 0, 0, -.593],
                "sad": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7.8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, -2, 0, 0, 0, 0, 0, 2,2,-2, 1, 1.6, 2, 1.6],
                "frustrated": [0, 0, -1.33, 1.63, 0, -1.185, 2.519, 0, 0, -.593, -.444],
                "angry": [0, 0, -2.074, 1.185, 1.63, -1.78, 1.63, .444, .89, .74, -4, 1.63, -1.93, -2.37, -4],
            }
        
        elif SMPL_version == 'SUPR':
            bpy.ops.object.reset_expression_shape('EXEC_DEFAULT')
            presets = {
                "pleasant": [0.3, 0, -0.2, 0, 0, 0, 0, 0, 0.3, 0.4],
                "happy":  [1.3, 0, 0, 0, -0.3, 0, 0.7, 0, -1, 0],
                "excited": [0.7, 0, -1.1, 0.9, -0.5, 0, 0, 0, 0, 0],
                "sad": [-0.35, 0, 0, -0.25, 1.75, 0, 0, 0, 0, 1.15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8.5],
                "frustrated": [0, 0, 0.7, -0.25, -1.5, -1, 0, 1.8, 0, 1.3],
                "angry": [0, 0, 1.2, 0, -1, -1, -1.5, 2.3, 0, -3],
            }
            
        preset_values = presets.get(self.preset)

        if not preset_values:
            self.report({"WARNING"}, f"Unknown preset: {self.preset}")
            return {"CANCELLED"}

        for i, value in enumerate(preset_values):
            key_name = f"Exp{i:03}"
            key_block = obj.data.shape_keys.key_blocks.get(key_name)
            if key_block:
                key_block.value = value

        return {"FINISHED"}


class OP_ModifyMetadata(bpy.types.Operator):
    bl_idname = "object.modify_avatar"
    bl_label = "Modify Metadata"
    bl_description = ("Click this button to save the meta data (SMPL_version and gender) on the selected avatar.  The SMPL_version and gender that are selected in the `Create Avatar` section will be assigned to the selected mesh.  This allows the plugin to know what kind of skeleton it's dealing with.  To view the meta data, click `Read Metadata` and check the console, or click `Object Properties` (orange box underneath the scene collection) > `Custom Properties`")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in Object Mode
            return (context.active_object is None) or (context.active_object.mode == 'OBJECT')
        except: return False

    def execute(self, context):
        gender = context.window_manager.smpl_tool.gender
        SMPL_version = context.window_manager.smpl_tool.SMPL_version

        #define custom properties on the avatar itself to store this kind of data so we can use it whenever we need to
        bpy.context.object['gender'] = gender
        bpy.context.object['SMPL_version'] = SMPL_version

        bpy.ops.object.read_avatar('EXEC_DEFAULT')

        return {'FINISHED'}


class OP_ReadMetadata(bpy.types.Operator):
    bl_idname = "object.read_avatar"
    bl_label = "Read Metadata"
    bl_description = ("Prints the selected Avatar's meta data to the console")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in Object Mode
            return (context.active_object is None) or (context.active_object.mode == 'OBJECT')
        except: return False

    def execute(self, context):
        print(bpy.context.object['gender'])
        print(bpy.context.object['SMPL_version'])

        return {'FINISHED'}

# this is a work around for a problem with the blender worker's fbx output.  Currently those .fbx's shape keys ranges are limited to 0 and 1.  
# this is a known problem, but I don't know why it's doing that.  For now, we can fix it using this button
class OP_FixBlendShapeRanges(bpy.types.Operator):
    bl_idname = "object.fix_blend_shape_ranges"
    bl_label = "Fix Blendshape Ranges"
    bl_description = ("Click this for any imported .fbx to set the min and max values for all blendshapes to -10 to 10.  At the time of writing this, Blender hardcodes imported .fbx file's blendshape ranges to 0 and 1.  This means that all meshcapade.me and digidoppel .fbx files will have their blendshapes clamped.  Until Blender fixes this issue (they're working on it), this button functions as a workaround.")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in Object Mode
            return (context.active_object is None) or (context.active_object.mode == 'OBJECT')
        except: return False

    def execute(self, context):
        
        for sk in context.active_object.data.shape_keys.key_blocks:
            sk.slider_min = -10
            sk.slider_max = 10

        return {'FINISHED'}


OPERATORS = [
    OP_LoadAvatar,
    OP_CreateAvatar,
    OP_SetTexture,
    OP_MeasurementsToShape,
    OP_RandomBodyShape,
    OP_RandomFaceShape,
    OP_ResetBodyShape,
    OP_ResetFaceShape,
    OP_RandomExpressionShape,
    OP_ResetExpressionShape,
    OP_SetExpressionPreset,
    OP_SnapToGroundPlane,
    OP_UpdateJointLocations,
    OP_CalculatePoseCorrectives,
    OP_CalculatePoseCorrectivesForSequence,
    OP_SetHandpose,
    OP_WritePoseToJSON,
    OP_WritePoseToConsole,
    OP_ResetPose,
    OP_ZeroOutPoseCorrectives,
    OP_LoadPose,
    OP_ModifyMetadata,
    OP_ReadMetadata,
    OP_FixBlendShapeRanges,
]
