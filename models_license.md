This Software is provided as part of the SMPL Model Commercial or Trial Sublicense Agreement (“Master Agreement”) made by and between [Meshcapade GmbH](www.meshcapade.com) (“MESHCAPADE”), and you (“SUBLICENSEE”), each of whom hereinafter individually also called a "Party", or collectively called the "Parties". 

For further details, please see the Master Agreement, or contact us for more information at: [support@meshcapade.com](support@meshcapade.com)

By downloading and/or using the Software, you acknowledge that you have read, understand, and agree to be bound by the terms and conditions laid out here. If any terms and conditions herein materially conflict with the terms and conditions agreed to in the Master Agreement concluded between the Parties, the terms of the Master Agreement shall apply.

### 1.  Definitions
**1.1 “Software”** shall mean (a) the trained SMPL-Model (including without limitation the updates to SMPL+H and SMPL-X) and associated software as of the Effective Date, (b) sample Python language programs that demonstrate the use of the Model Software (“Sample Code”), and (c) documentation supporting and enabling the matters described in (a) and (b) and maintenance releases and updates provided by Meshcapade under the Master Agreement.

The Software has been developed at the Max Planck Institute for Intelligent Systems (MPI) and is owned by and proprietary material of the Max-Planck-Gesellschaft zur Foerderung der Wissenschaften e.V. (MPG). The SMPL-Model specification is defined in the patent application WO2016207311A1 (2016-12-29), Skinned Multi-Person Linear Model listed in Exhibit A. MPG owns patent-pending technology disclosed in this patent application. MESHCAPADE has entered into a non-exclusive license agreement with Max-Planck-Innovation GmbH (MI), MPG’s technology transfer agency, for a non-exclusive license and the right to sublicense the use of the Software (the “MI/Meshcapade-License Agreement”).

**1.2 “SMPL-Model”** means SMPL: Skinned Multi-Person Linear Model (including without limitation the updates to SMPL+H and SMPL-X), a realistic representation of the human body that supports realistic changes in body shape and pose. SMPL-Model is learned from thousands of 3D body scans and is provided as male and female 3D models containing a 3D mesh, a joint skeleton based on linear blend skinning, and blend shapes for shape and pose deformations to represent realistic articulation for various body shapes. The SMPL-Model  includes the following software components:

**Template Mesh:** a 3D mesh that defines the 3D topology (e.g. number of vertices, polygons, skeleton joints) used by the SMPL-Model.

**Shape Components:** 10 Identity-dependent shape descriptors represented as vectors of concatenated vertex offsets from the Template Mesh.

**Pose Components:** 207 Pose-dependent shape descriptors represented as vectors of concatenated vertex offsets from the Template Mesh.

**Facial Expression Components:** 10 facial expression descriptors represented as vectors of concatenated vertex offsets from the Template Mesh.

**Face, Body and Hands' Pose parameters:** 30 body, 38 hands and 3 facial pose parameters represented as a vector of 3D skeleton joint positions.

**Model Software:** software to provide functionality to load the Shape and Pose Components, and a parametric function that uses the Components to generate 3D human meshes with varying identities in different poses.

Any individual subset of the SMPL-Model created under the Master Agreement, which excludes the shape blendshapes or the tools to create 3D bodies using the shape blendshapes of the SMPL-Model, is known as a **“SMPL-Body”** (collectively, “SMPL-Bodies”), and is licensed under the Creative Commons Attribution 4.0 International License, as defined here:
http://smpl.is.tue.mpg.de/license_body.

### Grant of Rights

**2.1 Sublicense Grant.** MESHCAPADE grants to SUBLICENSEE and its Affiliates during the term of the Master Agreement a non-exclusive, worldwide, non-sublicensable, non-transferable, royalty-free (but subject to payment under the Master Agreement) right and license under MESHCAPADE’s intellectual property rights to:

- make, use, lease, sell (directly or indirectly through multiple tiers of distributors and distribution channels), offer to sell, import, export, keep, supply, and otherwise dispose of and commercialize Integrated Products.
- use, reproduce, distribute, transmit, and otherwise exploit the Software solely as part of and to facilitate or enable the exploitation of Integrated Products.
- use, disclose, reproduce, distribute, transmit, make derivative works of and otherwise exploit the Sample Code to facilitate or enable the exploitation of Integrated Products.

For the sake of clarity, the license granted in this Section 2.1 does not permit any external use or disclosure of the Shape Components and Model Software; provided, however, that the Shape Components and Model Software may be integrated into SUBLICENSEE’S products and services that are provided externally so long as SUBLICENSEE takes reasonable steps in the design and making of its Integrated Products to prevent third parties from accessing or viewing the Shape Components and Model Software within the Integrated Products. For clarity, the rights granted above to SUBLICENSEE and its Affiliates include the right to:

- Download, copy, display, import, and use the Software and prepare derivative works of the Sample Code on computers owned, leased or otherwise controlled by SUBLICENSEE and/or its Affiliates;
- Distribute the Software among developers employed by SUBLICENSEE and/or its Affiliates, provided that all such developers shall be bound by terms as restrictive as the terms of the Master Agreement;
- Use the Software to train methods/algorithms/neural networks/etc. for commercial use of the trained system.
- Use the Software to generate training data for machine learning methods for commercial use of the method.
- Modify the Sample Code to create Derivative Works.
- Create and externally distribute SMPL-Bodies created using the Software.

Each of the foregoing being permitted uses by SUBLICENSEE and/or its Affiliates, and any product that results from the foregoing (subject to any restrictions set forth in the Master Agreement) being an Integrated Product.

**2.2 Sublicense Restrictions.** The Software must not be used by SUBLICENSEE and/or its Affiliates to generate defamatory, harassing, pornographic, obscene, or racist material whether commercial or not. With the exception of independent contractors of SUBLICENSEE that are acting on behalf of SUBLICENSEE and bound by terms as restrictive as the terms of the Master Agreement, the Software must not be reproduced, modified and/or made available in any form to any third party without MESHCAPADE’s prior written permission. SUBLICENSEE must not and must restrict its independent contractors from, directly or indirectly, reverse engineering the Software. SUBLICENSEE shall not, directly or indirectly, attempt to reverse engineer the Shape Components, Pose Components or Model Software.

**2.3 Software Updates.** MESHCAPADE, at its discretion, and MESHCAPADE’s sole expense, may make available updates, enhancements, extensions, modifications and other changes to the Software. These changes, if any, may not necessarily include all existing software or new features that MESHCAPADE releases for newer or other services of MESHCAPADE. The terms of the Master Agreement will govern any changes provided by MESHCAPADE that replace and/or supplement the original Software, unless such changes are accompanied by a separate license in which case the terms of that license will govern.

**2.4 Ownership.** SUBLICENSEE shall own and retain all rights, title and interest in and to any improvements, modifications or derivative works of the Sample Code created by or on behalf of SUBLICENSEE (“Derivative Works”), including but not limited to any annotations or labeling of the Sample Code. SUBLICENSEE shall also own and retain all rights, title and interest in and to any prototypes, algorithms, models, designs, ideas, drawings, notes, reports, documentation, specifications, hardware, software, products, services, data, materials or any other tangible or intangible items created by of for SUBLICENSEE in connection with or related to SUBLICENSEE’s use of the Software and related documentation.  For clarification, SUBLICENSEE is not obligated to disclose any Derivative Works to MESHCAPADE.

**2.5 Publication with SMPL.** Please cite the related research project - this website lists the most up to date bibliographic information for citing SMPL: http://smpl.is.tue.mpg.de

**2.6 Media projects with SMPL.** When using SMPL in a media project please give credit to Max Planck Institute for Intelligent Systems. For example: SMPL was used for character animation courtesy of the Meshcapade GmbH.
