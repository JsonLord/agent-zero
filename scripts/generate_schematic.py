import argparse
from PIL import Image, ImageDraw

def generate_schematic(description, output_path):
    """
    Generates a dummy schematic image.
    """
    try:
        img = Image.new('RGB', (600, 400), color = (255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10,10), f"Schematic for: {description}", fill=(0,0,0))
        img.save(output_path)
        print(f"Schematic saved to {output_path}")
    except Exception as e:
        print(f"Error generating schematic: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate a schematic.')
    parser.add_argument('description', type=str, help='A description of the schematic.')
    parser.add_argument('-o', '--output', type=str, default='schematic.png', help='The output path for the schematic.')
    args = parser.parse_args()
    generate_schematic(args.description, args.output)
