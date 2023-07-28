# About
This addon is an extension of the [SMPL-X Blender addon](https://www.youtube.com/watch?v=DY2k29Jef94) created by Joachim Tesch and owned by the Max Planck Institute for Intelligent Systems. Meshcapade has licensed the SMPL model and its updates (including SMPL+H, SMPL-X, STAR and SUPR) from Max Planck Institute, and is making this extension of the blender add-on available for commercial users who have an active license for the SMPL Model. 

For academic uses, please visit: https://smpl-x.is.tue.mpg.de/. Or contact us at support@meshcapade.com

# Meshcape Utilities Blender Add-on

This add-on allows you to add [SMPL-H](https://mano.is.tue.mpg.de/), [SMPL-X](https://smpl-x.is.tue.mpg.de), and [SUPR](https://supr.is.tue.mpg.de) skinned meshes to your current Blender scene. Each imported mesh consists of a shape specific rig, as well as shape keys (blend shapes) for shape, expression and pose correctives. It was developed in Blender 3.5.1.

# Features

## SMPL versions
- Add female/male/neutral SMPLH/SMPLX/SUPR meshes to current scene
- Set sample albedo texture
- Set body shape from height and weight measurements* 
- Randomize/reset body shape*
- Randomize/reset face expression shape*
- Randomize/reset face shape*
- Update joint locations*
- Position feet on ground plane (z=0)
- Enable/disable corrective poseshapes 
- Change hand pose (flat, relaxed)
- Write current pose in theta notation to console and console
- Load avatar from .npz file
<br>
<font size=2>*not SMPLH</font>

## Installation
- Download the zipped data folder containing SMPL model files for which you have a SMPL-Commercial use license.  If you do not have this link, please contact support@meshcapade.com for help.
- Unzip the data folder and place it inside the 'meshcapade/meshcapade_addon' folder.
- Place that folder inside your Blender folder's addon folder here:
  - <b>Windows</b>: `C:\Program Files\Blender Foundation\Blender <blender version>\<blender version>\scripts\addons\`
  - <b>Linux</b>: `C:\Program Files\Blender Foundation\Blender <blender version>\<blender version>\scripts\addons\`
  - <b>Mac</b>: `C:\Program Files\Blender Foundation\Blender <blender version>\<blender version>\scripts\addons\`
- Go to Edit -> Preferences, select Add-ons from the left bar
- Search for `Meshcapade` in the search bar on the top right
- If the plugin is not already enabled, check the box to enable it

![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/blender_addon_00.png)

- To open the panel, click the tiny arrow below the viewport shading options on the top right of the viewport. 

![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/blender_addon_01.gif)

## Notes

### SMPL-X

- The add-on GUI (gender, texture, hand pose) does not reflect the state of the currently selected SMPL-X model if you work with multiple models in one scene.
- To maintain editor responsiveness the add-on does not automatically recalculate the corrective pose shape keys when edit the armature pose. Use the `Update Pose Shapes` button to update the joint locations after pose changes.

### Terminal
- Opening the terminal window will allow you to see the output of any running script.  To achieve this with Linux or Mac, you need to launch Blender from the terminal.  
  - Windows
    - Click `Windows` > `Toggle System Console`
  
  ![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/windows_terminal_00.png)

  - Mac
    - press command + space and type `terminal` and press enter

  ![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/mac_terminal_00.png)

    - leave the terminal window open and open up the applications folder in another window
    - find Blender, right click on it, and select `Show Package Contents`
    - That will open a new folder.  Select `Contents` > `MacOS`
    - Inside that folder will be a single file called `Blender`.  Click and drag `Blender` onto the terminal window you opened in the first step. 
  
  ![image](https://media.githubusercontent.com/media/Meshcapade/SMPL_blender_addon/nathan/supr-update-blender/images/mac_terminal_01.png)

    - Press enter and it will launch blender from the terminal.
  - Linux


 Particularly helpful for displaying progress of lengthier operations, as the UI does not show any info.

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