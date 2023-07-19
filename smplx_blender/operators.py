import bpy
import os
import numpy as np
import json
import copy
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
    SMPLX_MODELFILE_300,
    SMPLH_MODELFILE,
    SUPR_MODELFILE,
    PATH,
)
from .blender import (
    set_pose_from_rodrigues,
    rodrigues_from_pose,
    get_joint_names,
    get_num_body_joints,
    get_num_hand_joints,
    setup_bone,
    correct_for_anim_format,
)

from mathutils import Vector, Quaternion
from math import radians



class OP_LoadAvatar(bpy.types.Operator, ImportHelper):
    bl_idname = "object.load_avatar"
    bl_label = "Load Avatar"
    bl_description = ("Load .npz file that contains a SMPL family avatar")
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
            #("guess", "Guess", ""),  #TODO
            ("SMPLH", "SMPL-H", ""),
            ("SMPLX", "SMPL-X", ""),
            ("SUPR", "SUPR", ""),
        ),
    )

    rest_position: EnumProperty(
        name="Body rest position",
        items=(
            ("SMPL-X", "SMPL-X", "Use default SMPL-X rest position (feet below the floor)"),
            ("GROUNDED", "Grounded", "Use feet-on-floor rest position"),
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

    hand_reference: EnumProperty(
        name="Hand pose reference",
        items=(
            ("FLAT", "Flat", "Use flat hand as hand pose reference"),
            ("RELAXED", "Relaxed", "Use relaxed hand as hand pose reference"),
        ),
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

    hand_pose_relaxed = None

    @classmethod
    def poll(cls, context):
        try:
            # Always enable button
            return True
        except: return False

    def execute(self, context):
        target_framerate = self.target_framerate

        if self.hand_reference == "RELAXED":
            if self.hand_pose_relaxed is None:
                data_path = os.path.join(PATH, "data", "smplx_handposes.npz")
                with np.load(data_path, allow_pickle=True) as data:
                    hand_poses = data["hand_poses"].item()
                    (left_hand_pose, right_hand_pose) = hand_poses["relaxed"]
                    self.hand_pose_relaxed = np.concatenate( (left_hand_pose, right_hand_pose) ).reshape(-1, 3)

        # Load .npz file
        print("Loading: " + self.filepath)
        with np.load(self.filepath) as data:
            # Check for valid AMASS file
            if ("trans" not in data) or ("gender" not in data) or (("mocap_frame_rate" not in data) and ("mocap_framerate" not in data) and ("fps" not in data)) or ("betas" not in data) or ("poses" not in data):
                self.report({"ERROR"}, "Invalid AMASS animation data file")
                return {"CANCELLED"}

            trans = data["trans"]

            if (self.gender_override != "disabled"):
                gender = self.gender_override
            else:
                gender = str(data["gender"])

            if "mocap_frame_rate" in data:
                fps_key = "mocap_frame_rate"
            elif "mocap_framerate" in data:
                fps_key = "mocap_framerate"
            else:
                fps_key = "fps"

            fps = int(data[fps_key])

            betas = data["betas"]
            poses = data["poses"]

            if fps < target_framerate:
                self.report({"ERROR"}, f"Mocap framerate ({fps}) below target framerate ({target_framerate})")
                return {"CANCELLED"}

        if (context.active_object is not None):
            bpy.ops.object.mode_set(mode='OBJECT')

        print ("gender: " + gender)
        print ("fps: " + str(fps))

        # Add gender specific model
        context.window_manager.smplx_tool.gender = gender
        context.window_manager.smplx_tool.smplx_handpose = "flat"
        bpy.ops.scene.create_avatar()

        obj = context.view_layer.objects.active
        armature = obj.parent

        # Append animation name to armature name
        armature.name = armature.name + "_" + os.path.basename(self.filepath).replace(".npz", "")

        context.scene.render.fps = target_framerate
        context.scene.frame_start = 1

        # Set shape and update joint locations
        bpy.ops.object.mode_set(mode='OBJECT')
        for index, beta in enumerate(betas):
            key_block_name = f"Shape{index:03}"

            if key_block_name in obj.data.shape_keys.key_blocks:
                obj.data.shape_keys.key_blocks[key_block_name].value = beta
            else:
                print(f"ERROR: No key block for: {key_block_name}")

        bpy.ops.object.update_joint_locations('EXEC_DEFAULT')

        height_offset = 0
        if self.rest_position == "GROUNDED":
            bpy.ops.object.snap_to_ground_plane('EXEC_DEFAULT')
            height_offset = armature.location[2]

            # Apply location offsets to armature and skinned mesh
            bpy.context.view_layer.objects.active = armature
            armature.select_set(True)
            obj.select_set(True)
            bpy.ops.object.transform_apply(location = True, rotation=False, scale=False) # apply to selected objects
            armature.select_set(False)

            # Fix root bone location
            bpy.ops.object.mode_set(mode='EDIT')
            bone = armature.data.edit_bones["root"]
            setup_bone(bone, SMPL_version)            
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.view_layer.objects.active = obj

        # Keyframe poses
        step_size = int(fps / target_framerate)

        num_frames = trans.shape[0]
        num_keyframes = int(num_frames / step_size)

        if self.keyframe_corrective_pose_weights:
            print(f"Adding pose keyframes with keyframed corrective pose weights: {num_keyframes}")
        else:
            print(f"Adding pose keyframes: {num_keyframes}")

        if len(bpy.data.actions) == 0:
            # Set end frame if we don't have any previous animations in the scene
            context.scene.frame_end = num_keyframes
        elif num_keyframes > context.scene.frame_end:
            context.scene.frame_end = num_keyframes

        SMPL_version = bpy.context.object['SMPL version']
        joint_names = get_joint_names(SMPL_version)
        num_joints = len(joint_names)
        num_body_joints = get_num_body_joints(SMPL_version)

        for index, frame in enumerate(range(0, num_frames, step_size)):
            if (index % 100) == 0:
                print(f"  {index}/{num_keyframes}")
            current_frame = index + 1
            current_pose = poses[frame].reshape(-1, 3)
            current_trans = trans[frame]
            for bone_index, bone_name in enumerate(joint_names):
                if bone_name == "pelvis":
                    # Keyframe pelvis location
                    if self.rest_position == "GROUNDED":
                        current_trans[1] = current_trans[1] - height_offset # SMPL-X local joint coordinates are Y-Up

                    armature.pose.bones[bone_name].location = Vector((current_trans[0], current_trans[1], current_trans[2]))
                    armature.pose.bones[bone_name].keyframe_insert('location', frame=current_frame)

                # Keyframe bone rotation
                pose_rodrigues = current_pose[bone_index]

                if self.hand_reference == "FLAT":
                    set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)
                else:
                    # Relaxed hand pose uses different coordinate system for fingers
                    finger_names = ["index", "middle", "pinky", "ring", "thumb"]
                    if not any([x in bone_name for x in finger_names]):
                        set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)
                    else:
                        # Finger rotations are relative to relaxed hand pose
                        hand_start_index = 1 + num_body_joints + 3
                        relaxed_hand_joint_index = bone_index - hand_start_index
                        pose_relaxed_rodrigues = self.hand_pose_relaxed[relaxed_hand_joint_index]
                        set_pose_from_rodrigues(armature, bone_name, pose_rodrigues, pose_relaxed_rodrigues)

                armature.pose.bones[bone_name].keyframe_insert('rotation_quaternion', frame=current_frame)

            if self.keyframe_corrective_pose_weights:
                # Calculate corrective poseshape weights for current pose and keyframe them.
                # Note: This significantly increases animation load time and also reduces real-time playback speed in Blender viewport.
                bpy.ops.object.update_pose_correctives('EXEC_DEFAULT')
                for key_block in obj.data.shape_keys.key_blocks:
                    if key_block.name.startswith("Pose"):
                        key_block.keyframe_insert("value", frame=current_frame)

        if (SMPL_version != 'SUPR'):
            correct_for_anim_format(self.anim_format, armature)

        print(f"  {num_keyframes}/{num_keyframes}")
        context.scene.frame_set(1)

        return {'FINISHED'}


class OP_CreateAvatar(bpy.types.Operator):
    bl_idname = "scene.create_avatar"
    bl_label = "Create"
    bl_description = ("Create a SMPL family avatar at the scene origin")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in Object Mode
            SMPL_version = context.window_manager.smpl_tool.SMPL_version

            if (context.active_object is None) or (context.active_object.mode == 'OBJECT'):
                return True
            else: 
                return False
        except: return False

    def execute(self, context):
        gender = context.window_manager.smpl_tool.gender
        SMPL_version = context.window_manager.smpl_tool.SMPL_version

        if (SMPL_version == 'SMPLX'):
            # Use 300 shape model by default if available
            model_path = os.path.join(PATH, "data", SMPLX_MODELFILE_300)
            if os.path.exists(model_path):
                model_file = SMPLX_MODELFILE_300
            else:
                model_file = SMPLX_MODELFILE

        elif (SMPL_version == 'SUPR'):
            model_path = os.path.join(PATH, "data", SUPR_MODELFILE)
            model_file = SUPR_MODELFILE

        # for now, the SMPLH option has been removed from the properties because we don't have regressors for it, 
        # so afm and a bunch of other stuff doesn't work
        elif (SMPL_version == "SMPLH"):
            model_path = os.path.join(PATH, "data", SMPLH_MODELFILE)
            model_file = SMPLH_MODELFILE

        else:
            model_path = "error bad SMPL version"
            model_file = "error bad SMPL version"

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
        bpy.context.object['SMPL version'] = SMPL_version

        # add a texture and change the texture option based on the gender
        if (gender == 'male'):
            context.window_manager.smpl_tool.texture = "m"
        else:
            context.window_manager.smpl_tool.texture = "f"

        # Set currently selected hand pose
        bpy.ops.object.set_handpose('EXEC_DEFAULT')
        bpy.ops.object.reset_body_shape('EXEC_DEFAULT')

        bpy.ops.object.set_texture()

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
            if (context.object.type == 'MESH'):
                return True
            else:
                return False
        except: return False

    def execute(self, context):
        selection = context.window_manager.smpl_tool.texture
        obj = bpy.context.object

        # if there's no material, add one
        if (len(obj.data.materials) == 0):
            # the incoming name of the selected object is in the format of "SUPR-mesh-male"
            # this line goes from "SUPR-mesh-male" to "SUPR-male", which is the naming format of the materials
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
        if (selection == 'm' or selection == 'f'):
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

        for i in range(0, 10):
            key_name = f"Shape{'%0.3d' % i}"
            key_block = obj.data.shape_keys.key_blocks.get(key_name)
            beta = np.random.normal(0.0, 1.0) * .5 * context.window_manager.smpl_tool.random_body_mult
            key_block.value = beta

        bpy.ops.object.update_joint_locations('EXEC_DEFAULT')

        context.window_manager.smpl_tool.alert = True

        return {'FINISHED'}
    
    def draw(self, context):
        context.window_manager.smpl_tool.alert = True
    

class OP_RandomFaceShape(bpy.types.Operator):
    bl_idname = "object.random_face_shape"
    bl_label = "Random Face Shape"
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

        for i in range(10,299):
            i_as_a_string = '%0.3d' % i
            key_name = f"Shape{i_as_a_string}"
            key_block = obj.data.shape_keys.key_blocks.get(key_name)
            beta = np.random.normal(0.0, 1.0) * .5 * context.window_manager.smpl_tool.random_face_mult
            #beta = np.clip(beta, -1.0, 1.0)
            key_block.value = beta

        bpy.ops.object.update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}


class OP_ResetBodyShape(bpy.types.Operator):
    bl_idname = "object.reset_body_shape"
    bl_label = "Reset Body Shape"
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

        gender = bpy.context.object['gender']

        # These are the default height and weight values for the three different templates.
        # There is some rounding error that makes applying these numbers not give you exactly 0.0 on the shape keys,
        # but they're so close that you can't tell unless if you look at the numbers. 
        # There are cases where you really want all the shape keys to be 0.0, 
        # so my workaround here is to first apply these height and weight values, then afterwards, manually 0 out the shape keys.
        # This results in a mismatch between the shape keys and the height and weight sliders, 
        # but the shape keys at 0.0 is what's actually being represented in the model, and when you slide the sliders, you can't tell.
        # I think this is the right way to do it.  
        if (gender == "male"):
            context.window_manager.smpl_tool.height = 178.40813305675982
            context.window_manager.smpl_tool.weight = 84.48267403991704
        elif (gender == "female"):
            context.window_manager.smpl_tool.height = 165.58187348544598
            context.window_manager.smpl_tool.weight = 69.80320278887571
        elif (gender == "neutral"):
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

        for i in range(10,299):
            key_name = f"Shape{'%0.3d' % i}"
            key_block = obj.data.shape_keys.key_blocks.get(key_name)
            key_block.value = 0

        bpy.ops.object.update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}


class OP_RandomExpressionShape(bpy.types.Operator):
    bl_idname = "object.random_expression_shape"
    bl_label = "Random Facial Expression"
    bl_description = ("Sets all face expression blend shape keys to a random value")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ((context.object.type == 'MESH') and (bpy.context.object['SMPL version'] != "SMPLH"))
        except: return False

    def execute(self, context):
        SMPL_version = bpy.context.object['SMPL version']
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        
        if (SMPL_version == 'SMPLX'):
            starting_string = 'Exp'
            distribution_range = 2
        elif (SMPL_version == 'SUPR'):
            starting_string = 'Shape3'  # the last 100 shape keys, 300 - 399, are expression keys
            distribution_range = 1.5    # putting 2 here for SUPR like SMPLX gets kind of crazy sometimes so I scaled it back

        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith(starting_string):
                key_block.value = np.random.uniform(-distribution_range, distribution_range)

        return {'FINISHED'}


class OP_ResetExpressionShape(bpy.types.Operator):
    bl_idname = "object.reset_expression_shape"
    bl_label = "Reset"
    bl_description = ("Resets all blend shape keys for face expression")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ((context.object.type == 'MESH') and (bpy.context.object['SMPL version'] != "SMPLH"))
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')

        SMPL_version = bpy.context.object['SMPL version']

        if (SMPL_version == 'SMPLX'):
            starting_string = 'Exp'
        elif (SMPL_version == 'SUPR'):
            starting_string = 'Shape3'  # the last 100 shape keys, 300 - 399, are expression keys
    
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith(starting_string):
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

        SMPL_version = bpy.context.object['SMPL version']
        gender = bpy.context.object['gender']
        joint_names = get_joint_names(SMPL_version)
        num_joints = len(joint_names)

        # Get beta shapes
        betas = []
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Shape"):
                betas.append(key_block.value)
        num_betas = len(betas)
        betas = np.array(betas)

        # this seems like it's loading up every possibilty every time you click this button
        # TODO: determine what you need and then only load what you need?
        # Cache regressor files on first call
        if (SMPL_version == 'SMPLX'):
            self.j_regressor_female = { 10: None, 300: None }
            self.j_regressor_male = { 10: None, 300: None }
            self.j_regressor_neutral = { 10: None, 300: None }

            for target_betas in [10, 300]:
                if self.j_regressor_female[target_betas] is None:
                    self.j_regressor_female[target_betas] = self.load_regressor("female", target_betas, SMPL_version.lower())

                if self.j_regressor_male[target_betas] is None:
                    self.j_regressor_male[target_betas] = self.load_regressor("male", target_betas, SMPL_version.lower())

                if self.j_regressor_neutral[target_betas] is None:
                    self.j_regressor_neutral[target_betas] = self.load_regressor("neutral", target_betas, SMPL_version.lower())

        elif (SMPL_version == 'SUPR'):
                self.j_regressor_female = { 400: None }
                self.j_regressor_male = { 400: None }
                self.j_regressor_neutral = { 300: None }
                
                self.j_regressor_female[400] = self.load_regressor("female", 400, SMPL_version.lower())
                self.j_regressor_male[400] = self.load_regressor("male", 400, SMPL_version.lower())
                self.j_regressor_neutral[300] = self.load_regressor("neutral", 300, SMPL_version.lower())               


        if "female" in obj.name:
            (betas_to_joints, template_j) = self.j_regressor_female[num_betas]
        elif "male" in obj.name:
            (betas_to_joints, template_j) = self.j_regressor_male[num_betas]
        else:
            (betas_to_joints, template_j) = self.j_regressor_neutral[num_betas]
        

        joint_locations = betas_to_joints @ betas + template_j

        # Set new bone joint locations
        armature = obj.parent
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')

        for index in range(num_joints):
            bone = armature.data.edit_bones[joint_names[index]]
            setup_bone(bone, SMPL_version)

            # Convert SMPL-X joint locations to Blender joint locations
            joint_location = joint_locations[index]

            if (SMPL_version == 'SMPLX'):
                bone_start = Vector((joint_location[0], -joint_location[2], joint_location[1]))

            elif (SMPL_version == 'SUPR'):
                bone_start = Vector((joint_location[0] * 100, joint_location[1] * 100, joint_location[2] * 100))

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
    # Calculate weights of pose corrective blend shapes
    # Input is pose of all 55 joints, output is weights for all joints except pelvis
    def rodrigues_to_posecorrective_weight(self, context, pose):
        SMPL_version = bpy.context.object['SMPL version']
        joint_names = get_joint_names(SMPL_version)
        num_joints = len(joint_names)
        
        if (SMPL_version == 'SMPLX' or SMPL_version == 'SMPLH'):
            rod_rots = np.asarray(pose).reshape(num_joints, 3)
            mat_rots = [self.rodrigues_to_mat(rod_rot) for rod_rot in rod_rots]
            bshapes = np.concatenate([(mat_rot - np.eye(3)).ravel() for mat_rot in mat_rots[1:]])
            return(bshapes)

        elif (SMPL_version == 'SUPR'):
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
        SMPL_version = bpy.context.object['SMPL version']
        joint_names = get_joint_names(SMPL_version)
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

        if (SMPL_version == 'SMPLH'):
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
            bpy.ops.object.update_pose_correctives()
            
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
    bl_idname = "object.set_handpose"
    bl_label = "Set"
    bl_description = ("Set selected hand pose")
    bl_options = {'REGISTER', 'UNDO'}

    hand_poses = None

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

        if self.hand_poses is None:
            path = os.path.dirname(os.path.realpath(__file__))
            data_path = os.path.join(path, "data", "handposes.npz")
            with np.load(data_path, allow_pickle=True) as data:
                self.hand_poses = data["hand_poses"].item()

        hand_pose_name = context.window_manager.smpl_tool.handpose
        print("Setting hand pose: " + hand_pose_name)

        if hand_pose_name not in self.hand_poses:
            self.report({"ERROR"}, f"Desired hand pose not existing: {hand_pose_name}")
            return {"CANCELLED"}

        (left_hand_pose, right_hand_pose) = self.hand_poses[hand_pose_name]

        hand_pose = np.concatenate((left_hand_pose, right_hand_pose)).reshape(-1, 3)

        SMPL_version = bpy.context.object['SMPL version']
        joint_names = get_joint_names(SMPL_version)
        num_body_joints = get_num_body_joints(SMPL_version)
        num_hand_joints = get_num_hand_joints(SMPL_version)

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
            return (context.object.type == 'MESH') or (context.object.type == 'ARMATURE')
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        joint_names = get_joint_names(bpy.context.object['SMPL version'])
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
            return (context.object.type == 'MESH') or (context.object.type == 'ARMATURE')
        except Exception:
            return False

    def execute(self, context):
        obj = bpy.context.object
        SMPL_version = bpy.context.object['SMPL version']
        joint_names = get_joint_names(SMPL_version)
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


class OP_LoadPose(bpy.types.Operator, ImportHelper):
    bl_idname = "object.load_pose"
    bl_label = "Load Pose"
    bl_description = ("Load relaxed-hand model pose from file")
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.npz;*.npy;*.json", # this originally worked for .pkl files only, but they have been since removed.  Let us know if that's a problem, we just need a good .pkl file to test against.
        options={'HIDDEN'}
    )

    update_shape: BoolProperty(
        name="Update shape parameters",
        description="Update shape parameters using the beta shape information in the loaded file",
        default=True
    )

    anim_format: EnumProperty(
        name="Format",
        items=(
            ("AMASS", "AMASS (Y-up)", ""),
            ("blender", "Blender (Z-up)", ""),
        ),
    )

    frame_number: IntProperty(
        name="Frame Number",
        description="Select the frame of the animation you'd like to load.  Only for .npz files.",
        default = 0,
        min = 0
    )

    hand_pose_relaxed = None

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        SMPL_version = bpy.context.object['SMPL version']
        joint_names = get_joint_names(SMPL_version)
        num_joints = len(joint_names)
        num_body_joints = get_num_body_joints(SMPL_version)
        num_hand_joints = get_num_hand_joints(SMPL_version)

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj
            obj = armature.children[0]
            context.view_layer.objects.active = obj # mesh needs to be active object for recalculating joint locations

        if self.hand_pose_relaxed is None:
            data_path = os.path.join(PATH, "data", "smplx_handposes.npz")
            with np.load(data_path, allow_pickle=True) as data:
                hand_poses = data["hand_poses"].item()
                (left_hand_pose, right_hand_pose) = hand_poses["relaxed"]
                self.hand_pose_relaxed = np.concatenate( (left_hand_pose, right_hand_pose) ).reshape(-1, 3)

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
            if (extension == ".pkl"): 
                data = pickle.load(f, encoding="latin1")
            elif (extension == ".npz"):
                data = np.load(f, allow_pickle=True)
            elif (extension == ".npy"):
                data = np.load(f, allow_pickle=True)

            if "transl" in data:
                translation = np.array(data["transl"]).reshape(3)

            if "global_orient" in data:
                global_orient = np.array(data["global_orient"]).reshape(3)

            if (extension == '.pkl'):
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
                    set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)

            elif (extension == '.npz'):
                correct_key = 'pose'
                try: 
                    np.array(data['pose'])

                except KeyError:
                    correct_key = "poses"

                print (f"using '{correct_key}'")

                pose_index = max(0, min(self.frame_number, (len(np.array(data[correct_key]))))) # clamp the frame they give you from 0 and the max number of frames in this poses array 
                body_pose = np.array(data[correct_key][pose_index]).reshape(len(joint_names), 3)

                # pose the entire body
                for index in range(len(joint_names)):
                    pose_rodrigues = body_pose[index]
                    bone_name = joint_names[index]
                    set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)

            elif (extension == '.npy'):
                # assuming a .npy containing a single pose
                body_pose = np.array(data).reshape(len(joint_names), 3)
                
                # pose the entire body
                for index in range(len(joint_names)):
                    pose_rodrigues = body_pose[index]
                    bone_name = joint_names[index]
                    set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)

            elif (extension == '.json'):
                with open(self.filepath, "rb") as f:
                    pose_data = json.load(f)
                    
                pose = np.array(pose_data["pose"]).reshape(num_joints, 3)

                for index in range(num_joints):
                    pose_rodrigues = pose[index]
                    bone_name = joint_names[index]
                    set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)
               
            if (extension in ['.npz', 'pkl']):
                betas = np.array(data["betas"]).reshape(-1).tolist()


        # Update shape if selected
        if self.update_shape:
            bpy.ops.object.mode_set(mode='OBJECT')

            if (extension in ['.npz', 'pkl']):
                for index, beta in enumerate(betas):
                    key_block_name = f"Shape{index:03}"

                    if key_block_name in obj.data.shape_keys.key_blocks:
                        obj.data.shape_keys.key_blocks[key_block_name].value = beta
                    else:
                        print(f"ERROR: No key block for: {key_block_name}")

            bpy.ops.object.update_joint_locations('EXEC_DEFAULT')

        if global_orient is not None:
            set_pose_from_rodrigues(armature, "pelvis", global_orient)

        if (SMPL_version != 'SUPR'):
            correct_for_anim_format(self.anim_format, armature)

        if translation is not None:
            # Set translation
            armature.location = (translation[0], -translation[2], translation[1])

        # Activate corrective poseshapes
        bpy.ops.object.update_pose_correctives('EXEC_DEFAULT')

        # Set face expression
        if (extension == '.pkl'):
            set_pose_from_rodrigues(armature, "jaw", jaw_pose)  

            # Left hand
            start_name_index = 1 + num_body_joints + 3
            for i in range(0, num_hand_joints):
                pose_rodrigues = left_hand_pose[i]
                bone_name = joint_names[start_name_index + i]
                pose_relaxed_rodrigues = self.hand_pose_relaxed[i]
                set_pose_from_rodrigues(armature, bone_name, pose_rodrigues, pose_relaxed_rodrigues)

            # Right hand
            start_name_index = 1 + num_body_joints + 3 + num_hand_joints
            for i in range(0, num_hand_joints):
                pose_rodrigues = right_hand_pose[i]
                bone_name = joint_names[start_name_index + i]
                pose_relaxed_rodrigues = self.hand_pose_relaxed[num_hand_joints + i]
                set_pose_from_rodrigues(armature, bone_name, pose_rodrigues, pose_relaxed_rodrigues)

            for index, exp in enumerate(expression):
                key_block_name = f"Exp{index:03}"

                if key_block_name in obj.data.shape_keys.key_blocks:
                    obj.data.shape_keys.key_blocks[key_block_name].value = exp
                else:
                    print(f"ERROR: No key block for: {key_block_name}")

        return {'FINISHED'}


class OP_ExportUnityFBX(bpy.types.Operator, ExportHelper):
    bl_idname = "object.export_unity_fbx"
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
        except Exception:
            return False

    def execute(self, context):

        obj = bpy.context.object
        export_shape_keys = context.window_manager.smpl_tool.smplx_export_setting_shape_keys

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

        # Apply armature object location to armature root bone and skinned mesh so
        # that armature and skinned mesh are at origin before export
        context.view_layer.objects.active = armature
        context.view_layer.objects.active = armature
        armature_offset = Vector(armature.location)
        armature.location = (0, 0, 0)
        bpy.ops.object.mode_set(mode='EDIT')
        for edit_bone in armature.data.edit_bones:
            if edit_bone.name != "root":
                edit_bone.translate(armature_offset)

        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = skinned_mesh
        mesh_location = Vector(skinned_mesh.location)
        skinned_mesh.location = mesh_location + armature_offset
        bpy.ops.object.transform_apply(location=True)

        # Reset pose
        bpy.ops.object.reset_pose('EXEC_DEFAULT')

        if export_shape_keys != 'SHAPE_POSE':
            # Remove pose corrective shape keys
            print("Removing pose corrective shape keys")
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

        # Model (skeleton and skinned mesh) needs to have rotation of (90, 0, 0) when
        # exporting so that it will have rotation (0, 0, 0) when imported into Unity
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh.select_set(True)
        skinned_mesh.rotation_euler = (radians(-90), 0, 0)
        bpy.context.view_layer.objects.active = skinned_mesh
        bpy.ops.object.transform_apply(rotation=True)
        skinned_mesh.rotation_euler = (radians(90), 0, 0)
        skinned_mesh.select_set(False)

        armature.select_set(True)
        armature.rotation_euler = (radians(-90), 0, 0)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.transform_apply(rotation=True)
        armature.rotation_euler = (radians(90), 0, 0)

        # Select armature and skinned mesh for export
        skinned_mesh.select_set(True)

        gender = context.window_manager.smplx_tool.gender
        SMPL_version = context.window_manager.smplx_tool.SMPL_version

        target_mesh_name = f"{SMPL_version}-mesh-{gender}"
        target_armature_name = f"{SMPL_version}-{gender}"

        if target_mesh_name in bpy.data.objects:
            bpy.data.objects[target_mesh_name].name = f"{SMPL_version}-temp-mesh"
        skinned_mesh.name = target_mesh_name

        if target_armature_name in bpy.data.objects:
            bpy.data.objects[target_armature_name].name = f"{SMPL_version}-temp-armature"
        armature.name = target_armature_name

        bpy.ops.export_scene.fbx(
            filepath=self.filepath,
            use_selection=True,
            apply_scale_options="FBX_SCALE_ALL",
            add_leaf_bones=False,
        )

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
            return ((context.object.type == 'MESH') and (bpy.context.object['SMPL version'] != "SMPLH"))
        except: return False

    def execute(self, context):
        SMPL_version = bpy.context.object['SMPL version']

        obj = context.object
        if not obj or not obj.data.shape_keys:
            self.report(
                {"WARNING"}, "Object has no shape keys. Please select a SMPL-X mesh."
            )
            return {"CANCELLED"}

        if (SMPL_version == 'SMPLX'):
            presets = {
                "pleasant": [0, 0.30, 0, -0.30, -0.40, 0, -0.20, 0, 0.30, 0],
                "happy": [0.93, 0, 0, 0, 0.27, 0, 0.29, 0, -1.00, 0],
                "excited": [0, 0, 0, 0, 1.50, 0.90, 0, 0, -0.70, 0],
                "sad": [-0.20, 0, 0, 0, -1.60, 0, -1.30, 0, 0.60, 0],
                "frustrated": [0, 0.75, -1.20, 0.13, -0.60, 0.62, -0.90, -0.78, 0, -1.56],
                "angry": [1.11, 1.69, -0.27, 0, -0.78, 0, -1.24, 1.29, -0.22, -2.00],
            }
        
        elif (SMPL_version == 'SUPR'):
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
            if (SMPL_version == 'SMPLX'):
                key_name = f"Exp00{i}"
            elif (SMPL_version == 'SUPR'):
                key_name = f"Shape{i+300}"
            key_block = obj.data.shape_keys.key_blocks.get(key_name)
            if key_block:
                key_block.value = value

        return {"FINISHED"}


class OP_ModifyMetadata(bpy.types.Operator):
    bl_idname = "object.modify_avatar"
    bl_label = "Modify Metadata"
    bl_description = ("Click this button to save the meta data (SMPL version and gender) on the selected avatar.  The SMPL version and gender that are selected in the `Create Avatar` section will be assigned to the selected mesh.  This allows the plugin to know what kind of skeleton it's dealing with.  To view the meta data, click `Read Metadata` and check the console, or click `Object Properties` (orange box underneath the scene collection) > `Custom Properties`")
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
        gender = context.window_manager.smplx_tool.gender
        SMPL_version = context.window_manager.smplx_tool.SMPL_version

        #define custom properties on the avatar itself to store this kind of data so we can use it whenever we need to
        bpy.context.object['gender'] = gender
        bpy.context.object['SMPL version'] = SMPL_version

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
            if (context.active_object is None) or (context.active_object.mode == 'OBJECT'):
                return True
            else: 
                return False
        except: return False

    def execute(self, context):
        print(bpy.context.object['gender'])
        print(bpy.context.object['SMPL version'])

        return {'FINISHED'}

# this is a work around for a problem with the blender worker's fbx output.  Currently those .fbx's shape keys ranges are limited to 0 and 1.  
# this is a known problem, but I don't know why it's doing that.  For now, we can fix it using this button
class OP_FixBlendShapeRanges(bpy.types.Operator):
    bl_idname = "object.fix_blend_shape_ranges"
    bl_label = "Fix Blend Shape Ranges"
    bl_description = ("Click this for any imported .fbx to set the min and max values for all blendshapes to -10 to 10.  At the time of writing this, Blender hardcodes imported .fbx file's blend shape ranges to 0 and 1.  This means that all meshcapade.me and digidoppel .fbx files will have their blend shapes clamped.  Until Blender fixes this issue (they're working on it), this button functions as a workaround.")
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
    OP_ExportUnityFBX,
    OP_ModifyMetadata,
    OP_ReadMetadata,
    OP_FixBlendShapeRanges,
]
