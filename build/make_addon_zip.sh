#!/bin/bash
pushd ../..

filedate=$(date '+%Y%m%d')
archivename=./smplx_blender_addon-$filedate.zip
if [ -f $archivename ]; then
  echo "Removing old add-on: $archivename"
  rm $archivename
fi

zip $archivename smplx_blender_addon/*.py smplx_blender_addon/*.md smplx_blender_addon/data/*.npz smplx_blender_addon/data/*.json smplx_blender_addon/data/*.png smplx_blender_addon/data/*.blend
popd