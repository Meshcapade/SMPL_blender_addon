import os
import platform
import numpy as np

VERSION = (2023, 7, 20)

SMPLX_MODELFILE = "smplx_model_20210421.blend"
SMPLX_MODELFILE_300 = "smplx_model_300_20220615.blend"
SUPR_MODELFILE = "supr.blend"
SMPLH_MODELFILE = "smplh.blend"

SMPLX_JOINT_NAMES = [
    'pelvis',
    'left_hip',
    'right_hip',
    'spine1',
    'left_knee',
    'right_knee',
    'spine2',
    'left_ankle',
    'right_ankle',
    'spine3',
    'left_foot',
    'right_foot',
    'neck',
    'left_collar',
    'right_collar',
    'head',
    'left_shoulder',
    'right_shoulder',
    'left_elbow',
    'right_elbow',
    'left_wrist',
    'right_wrist',
    'jaw',
    'left_eye_smplhf',
    'right_eye_smplhf',
    'left_index1',
    'left_index2',
    'left_index3',
    'left_middle1',
    'left_middle2',
    'left_middle3',
    'left_pinky1',
    'left_pinky2',
    'left_pinky3',
    'left_ring1',
    'left_ring2',
    'left_ring3',
    'left_thumb1',
    'left_thumb2',
    'left_thumb3',
    'right_index1',
    'right_index2',
    'right_index3',
    'right_middle1',
    'right_middle2',
    'right_middle3',
    'right_pinky1',
    'right_pinky2',
    'right_pinky3',
    'right_ring1',
    'right_ring2',
    'right_ring3',
    'right_thumb1',
    'right_thumb2',
    'right_thumb3'
    ]

SMPLH_JOINT_NAMES = [
    'pelvis',
    'left_hip',
    'right_hip',
    'spine1',
    'left_knee',
    'right_knee',
    'spine2',
    'left_ankle',
    'right_ankle',
    'spine3',
    'left_foot',
    'right_foot',
    'neck',
    'left_collar',
    'right_collar',
    'head',
    'left_shoulder',
    'right_shoulder',
    'left_elbow',
    'right_elbow',
    'left_wrist',
    'right_wrist',
    'left_index1',
    'left_index2',
    'left_index3',
    'left_middle1',
    'left_middle2',
    'left_middle3',
    'left_pinky1',
    'left_pinky2',
    'left_pinky3',
    'left_ring1',
    'left_ring2',
    'left_ring3',
    'left_thumb1',
    'left_thumb2',
    'left_thumb3',
    'right_index1',
    'right_index2',
    'right_index3',
    'right_middle1',
    'right_middle2',
    'right_middle3',
    'right_pinky1',
    'right_pinky2',
    'right_pinky3',
    'right_ring1',
    'right_ring2',
    'right_ring3',
    'right_thumb1',
    'right_thumb2',
    'right_thumb3'
    ]

SUPR_JOINT_NAMES = [
    "pelvis",
    "left_hip",
    "right_hip",
    "spine1",
    "left_knee",
    "right_knee",
    "spine2",
    "left_ankle",
    "right_ankle",
    "spine3",
    "left_foot",
    "right_foot",
    "neck",
    "left_collar",
    "right_collar",
    "head",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "jaw",
    "left_eye",
    "right_eye",
    "left_index1",
    "left_index2",
    "left_index3",
    "left_middle1",
    "left_middle2",
    "left_middle3",
    "left_pinky1",
    "left_pinky2",
    "left_pinky3",
    "left_ring1",
    "left_ring2",
    "left_ring3",
    "left_thumb1",
    "left_thumb2",
    "left_thumb3",
    "right_index1",
    "right_index2",
    "right_index3",
    "right_middle1",
    "right_middle2",
    "right_middle3",
    "right_pinky1",
    "right_pinky2",
    "right_pinky3",
    "right_ring1",
    "right_ring2",
    "right_ring3",
    "right_thumb1",
    "right_thumb2",
    "right_thumb3",
    "left_bigtoe1",
    "left_bigtoe2",
    "left_indextoe1",
    "left_indextoe2",
    "left_middletoe1",
    "left_middletoe2",
    "left_ringtoe1",
    "left_ringtoe2",
    "left_pinkytoe1",
    "left_pinkytoe2",
    "right_bigtoe1",
    "right_bigtoe2",
    "right_indextoe1",
    "right_indextoe2",
    "right_middletoe1",
    "right_middletoe2",
    "right_ringtoe1",
    "right_ringtoe2",
    "right_pinkytoe1",
    "right_pinkytoe2"
    ]

NUM_SMPLX_JOINTS = len(SMPLX_JOINT_NAMES)
NUM_SMPLX_BODYJOINTS = 21
NUM_SMPLX_HANDJOINTS = 15

NUM_SUPR_JOINTS = len(SUPR_JOINT_NAMES)
NUM_SUPR_BODY_JOINTS = 21    # leaving as is for now.  Not sure what to do about the toes
NUM_SUPR_HAND_JOINTS = 15 

NUM_SMPLH_JOINTS = len(SMPLX_JOINT_NAMES)
NUM_SMPLH_BODY_JOINTS = 21   
NUM_SMPLH_HAND_JOINTS = 15   # must be per hand

FBX_TYPE = "fbx"
OBJ_TYPE = "obj"

HIGH = "high"
MEDIUM = "medium"
LOW = "low"

OS = platform.system()
PATH = os.path.dirname(os.path.realpath(__file__))

LEFT_HAND_RELAXED = np.load(os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "handpose_relaxed_left.npy"))
RIGHT_HAND_RELAXED = np.load(os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "handpose_relaxed_right.npy"))

RESOLUTIONS = [
    HIGH,
    MEDIUM,
    LOW,
]

RESOLUTION_MAPPING = {
    6890: LOW,
    27578: MEDIUM,
    110306: HIGH,
}

SMPL_V1 = "smpl_v1"
SMPL_V0 = "smpl_v0"

UV_TYPES = [
    SMPL_V1,
    SMPL_V0,
]
