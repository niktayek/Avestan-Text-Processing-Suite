import os
from PIL import Image

input_folder = '../../data/Test_40/'
output_folder = '../../data/Test_40/'


for filename in os.listdir(input_folder):
    if os.path.splitext(filename.lower())[-1] not in [".png", ".jpg", ".tiff"]:
        continue

    input_path = os.path.join(input_folder, filename)
    output_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_mirrored{os.path.splitext(filename)[1]}")

    img = Image.open(input_path)
    flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
    flipped.save(output_path)
    print(f"Mirrored: {filename} -> {output_path}")
