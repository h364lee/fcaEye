import os
from PIL import Image, ImageDraw

output_dir = "stimObj"
os.makedirs(output_dir, exist_ok=True)

sizes = ["big", "small"]
colours = ["black", "white"]
shapes = ["tri", "square"]

for size in sizes:
    for colour in colours:
        for shape in shapes:
            img = Image.new("RGB", (400, 400), (200, 200, 200))
            draw = ImageDraw.Draw(img)

            fill = (0, 0, 0) if colour == "black" else (255, 255, 255)
            outline = (0, 0, 0) 

            if size == "big":
                left, top, right, bottom = 50, 50, 350, 350
            else:
                left, top, right, bottom = 150, 150, 250, 250

            if shape == "tri":
                top_vertex = ((left + right) // 2, top)
                bottom_left = (left, bottom)
                bottom_right = (right, bottom)
                draw.polygon([top_vertex, bottom_left, bottom_right], fill=fill, outline=outline, width=1)
            elif shape == "square":
                draw.rectangle([left, top, right, bottom], fill=fill, outline=outline, width=1)

            filename = f"{output_dir}/{size}_{colour}_{shape}.png"
            img.save(filename)

            print('I have completed my job as an image generating machine, Caleb!')
