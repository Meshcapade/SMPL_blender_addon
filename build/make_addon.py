from zipfile import ZipFile, ZIP_DEFLATED
from os import path, walk, listdir
from datetime import date

build_script_dir = path.dirname(path.abspath(__file__))
today = date.today()
filedate = today.strftime("%Y%m%d")
filename = '{}_{}.zip'.format("smplx_blender", filedate)

root_folder = "{}/../".format(build_script_dir)
addon_folder = "{}/smplx_blender".format(root_folder)
data_folder = "{}/data".format(addon_folder)

with ZipFile(filename, 'w') as z:
    # Adding python and data files
    for root, _, files in walk(addon_folder):
        for file in files:
            if not (root.startswith(data_folder) or file.endswith('.py') or file.endswith('.pyd')):
                continue
            filepath = path.join(root, file)
            print("Adding '{}'".format(filepath.replace(root_folder, "")))
            z.write(filepath, compress_type=ZIP_DEFLATED)
    # Adding README, LICENSE, and other root .md files
    for file in listdir(root_folder):
        if file.endswith(".md"):
            filepath = path.join(root_folder, file)
            print("Adding '{}'".format(filepath.replace(root_folder, "")))
            z.write(filepath, compress_type=ZIP_DEFLATED)

print("Finished making release '{}', saved to current directory".format(filename))
