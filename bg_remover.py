from rembg import remove
from PIL import Image

input_path='ele2.jpg'
image=Image.open(input_path)

output_image=remove(image)
output_path='ele_no_bg.png'
output_image.save(output_path)

print("Background removed and saved to", output_path)