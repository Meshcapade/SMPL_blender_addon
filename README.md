# About
This addon is an extension of the [SMPL-X Blender addon](https://www.youtube.com/watch?v=DY2k29Jef94) created by Joachim Tesch and owned by the Max Planck Institute for Intelligent Systems. Meshcapade has licensed the SMPL model and its updates (including SMPL-H, SMPL-X, STAR and SUPR) from Max Planck Institute, and is making this extension of the blender add-on available for commercial users who have an active license for the SMPL Model. 

Academic use of this plugin is free - just contact us at support@meshcapade.com.

This add-on allows you to add [SMPL-H](https://mano.is.tue.mpg.de/), [SMPL-X](https://smpl-x.is.tue.mpg.de), and [SUPR](https://supr.is.tue.mpg.de) bodies to your current Blender scene. Each body consists of a mesh, a shape specific rig, and shape keys (blend shapes) for shape, expression and pose correctives. This addon was most recently developed in Blender 3.5.1.

# Features

## Overview
- Add female/male/neutral SMPLH/SMPLX/SUPR bodies to current scene<sup>2</sup> 
- Set sample materials
- Load avatar from .npz file<sup>2</sup> 
- Set body shape from height and weight measurements<sup>1, 2</sup> 
- Randomize/reset body shape<sup>1, 2</sup> 
- Randomize/reset face shape<sup>1, 2</sup> 
- Randomize/reset facial expression <sup>1, 2</sup> 
- Update joint locations<sup>1, 2</sup> 
- Position feet on ground plane
- Enable/disable corrective poseshapes for a single frame or for multiple frames
- Change hand pose (flat, relaxed)<sup>2</sup> 
- Write current pose in theta notation to console or to a .json file
- Modify and read a body's metadata
- Set the blend shape range of all shape keys to -10 and 10, to bypass a current bug in Blender when importing .fbx files with shape keys on them.
<br>
<font size=2>
  <sup>1</sup>not SMPLH
  <br>
  <sup>2</sup>commercial use only
</font>

## Installation
- Download the zipped data folder containing SMPL model files for which you have a SMPL-Commercial use license.  If you do not have this link, please contact support@meshcapade.com for help.
- Unzip the data folder and place it inside the 'meshcapade/meshcapade_addon' folder.
- Place that folder inside your Blender folder's addon folder here:
  - <b>Windows</b>: `[drive]:\Program Files\Blender Foundation\Blender [version]\[version]\scripts\addons\`
  - <b>Linux</b>: `/usr/share/blender/[version]/scripts/addons/`
  - <b>Mac</b>: 
    - Go to `Applications > Blender` then right click on blender and select `Show Package Contents`
![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/mac_install_00.png)

    - Then navigate to `contents > resources > [version] > scripts > addons` and place the meshcapade addon inside the `addons` folder

- Inside Blender, go to `Edit > Preferences`, and select `Add-ons` from the left bar
- Search for `Meshcapade` in the search bar on the top right
- If you don't see the plugin, hit refresh in the top right corner.  If you still don't see it, try restarting Blender.
- If the plugin is not enabled, check the box next to the plugin name to enable it
![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/blender_addon_00.png)

- To open the addon panel, click the tiny arrow on the top right of the viewport below the viewport shading options. 
![image](https://raw.githubusercontent.com/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/blender_addon_01.gif)

## Notes

- The add-on GUI (gender, texture, hand pose) does not reflect the state of the currently selected model if you work with multiple models in one scene.
- To maintain editor responsiveness the add-on does not automatically recalculate the corrective pose shape keys when edit the armature pose. Use the `Update Pose Shapes` button to update the joint locations after pose changes.

### Terminal
Opening the terminal window will allow you to see the output of any running script.  It's particularly helpful for displaying progress of lengthier operations, since the UI doesn't show any info.  To achieve this with Linux or Mac, you need to launch Blender from the terminal.  
#### <b>Windows</b>
Click `Window` > `Toggle System Console`
  
![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/windows_terminal_00.png)

#### <b>Mac</b>
- press command + space and type `terminal` and press enter
![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/mac_terminal_00.png)
  
- leave the terminal window open and open up the applications folder in another window
- find Blender, right click on it, and select `Show Package Contents`
- That will open a new folder.  Select `Contents` > `MacOS`
- Inside that folder will be a single file called `Blender`.  Click and drag `Blender` onto the terminal window you opened in the first step. 
![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/mac_terminal_01.png)

- Press enter and it will launch blender from the terminal.

#### <b>Linux</b>
This will be slightly different depending on your Linux distribution.
- Open the terminal and go to the location of your blender executable.  
- You can also navigate there in the folder view and then launch the terminal from that location.
![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/linux_terminal_00.png)
- In the terminal, type `blender` and press enter.  This will launch blender from the terminal.


## Getting avatars inside Blender

There are a few ways to get Meshcapade avatars into Blender.  One way is to create and download free avatars from our platform, meshcapade.me.  You can create up to 5 free avatars a day, or you can purchase credits to be able to do more than that.  

Academic or commercial license customers can get an additional component to the plugin that allows them to add an unlimited number of SMPL bodies directly to their scenes.  They can either create avatars from scratch, or they can load .npz files that contain not only body shape definitions but animations as well.  Both of these methods support SMPLH (to a limited extent), SMPLX and SUPR bodies and you can create an unlimited number of avatars using these two methods.

## Pose Correctives

Meshcapade avatars have a built in component that allows for statistically accurate pose based deformations.  Once a Meshcapade avatar is in your Blender scene, you can animate or pose it as you normally would.  Click the `Calculate Pose Correctives` button for a single frame or `Calculate Pose Correctives for Entire Sequence` for an animation sequence.  This feature is available for non licensed use of our Blender plugin.

Note: A bug exists in Blender up to and including LTS 6.1 in which imported .fbx files have their blend shapes clamped to 0 and 1.  The pose correctives can have values that are less than 0 and greater than 1, so this is a problem here.  After importing your .fbx, click the `Fix Blend Shape Ranges` button on the plugin and it will set all the blend shape ranges to the highest and lowest possible values blender allows: 10 and -10.  This is a known issue which Blender has already addressed, it just hasn’t been released as of my writing this.

More information about the commercial and R&D licenses can be found [on our website](https://meshcapade.com/assets/body-models) or by contacting sales@meshcapade.com.

## Facial Expressions

SMPLX and SUPR bodies have facial expression support.  The plugin comes with 6 pre-baked facial expressions (Pleasant, Happy, Excited, Sad, Frustrated, and Angry), a `Random Facial Expression` button, and a `Reset` button to set the facial expression back to normal.  For finer control of the facial expressions, select the mesh in Object Mode and open the Object Data Properties tab.  Under Shape Keys, you can edit th eshape keys that start with `Exp` to modify the facial expression.

## Modifying Shape and Loading Poses

If you have the additional data folder, you have access to a few more features of the plugin.  The first is modifying the body shape.  There are sliders to change the avatar’s height and weight, along with `Random Body Shape` and `Random Face Shape` buttons.  The joint locations are automatically updated if you use any of the body shape modification tools from the plugin.  You can also fine tune the shape of your avatar using the `Shape` blend shapes in the Object Data Properties panel.  If you do that, you need to manually click the `Update Joint Locations` button to calculate the new joint locations.

Along with this, you can also load in poses onto your avatars if you have .npz files that contain animation data (like [AMASS](https://amass.is.tue.mpg.de/), which is free for non-commercial scientific research).  If you are loading a pose, be sure to select the correct up-axis in the import options in the top right corner of the popup dialogue.

## Additional Tools

The `Fix Pose Correctives for Entire Sequence` button is explained in the Pose Correctives section.  

Meshcapade avatars have additional metadata on them that tell the plugin what gender and SMPL version the selected avatar is.  When you click the `Modify Metadata` button, the `SMPL version` and `gender` in the `Create` section will be written on the selected avatar.  You only need to use this if you are trying to use the plugin with older avatars that do not have this data encoded on them.  You can also use this to change metadata on an avatar that already has metadata on it, but this will likely cause problems.

`Read Metadata` writes the metadata to the console.

The two `Write Pose` buttons are so that you can see the poses in SMPL format.  This is something our internal machine learning scientists need.

## Licenses

- The blender code available in this repo is licensed under the GPL 3.0 license:
https://www.gnu.org/licenses/gpl-3.0.en.html

- The SMPL, SMPL-H, SMPL-X, or SUPR model files used in or by this repo are available only under the SMPL-Commercial use license. Before using this product, please make sure you have an active SMPL Model commercial-use license. See models_license.md for further license information about SMPL & SMPL-X.

- Body meshes generated using this add-on are covered under the SMPL-Body Creative-Commons-BY license: https://smpl.is.tue.mpg.de/bodylicense.html

- Attribution for publications:
  - You agree to cite the most recent paper describing the model as specified on the SMPL-X website: <https://smpl-x.is.tue.mpg.de>

## Acknowledgements

- [Joachim Tesch](https://gitlab.tuebingen.mpg.de/jtesch), creator of the original blender addon for SMPL-X. This repo is a commercial-use extension for his addon which is available for academic use here: https://gitlab.tuebingen.mpg.de/jtesch/smplx_blender_addon

- Sergey Prokudin (rainbow texture data)

- Vassilis Choutas (betas-to-joints regressor)

- Lea Müller and Vassilis Choutas (measurements-to-betas regressor)

## Changelog

- 20210505: Initial release
- 20210525: Replaced vertices-to-joints regressor with beta-to-joints regressor. Added rainbow texture (CC BY-NC 4.0).
- 20210611: Added option to set shape from height and weight values for female and male models
- 20210820: Created Meshcapade fork
- 20230720: Added SUPR and limited SMPLH support to the plugin 

## Contact

- support@meshcapade.com