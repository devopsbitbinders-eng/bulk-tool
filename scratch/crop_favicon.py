from PIL import Image, ImageOps
import os

# Ensure we are in the right directory
os.chdir(r"c:\Users\kajal\Downloads\messanger")

# Load image
img = Image.open("static/logo.png")

# Convert to RGB if it's RGBA and has white background
if img.mode == 'RGBA':
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.paste(img, (0, 0), img)
    img = bg.convert('RGB')
else:
    img = img.convert('RGB')

# Invert image to find bounding box of non-white content
inverted = ImageOps.invert(img)
bbox = inverted.getbbox()

if bbox:
    print(f"Original content bbox: {bbox}")
    # Crop to the content (removes white borders)
    cropped = img.crop(bbox)
    
    w, h = cropped.size
    print(f"Cropped content size: {w}x{h}")
    
    # The icon is at the top. Let's crop a square from the top.
    # The icon usually has a bit of space below it before the text.
    # Let's assume the icon is a square of size `w` (width of content).
    # If h is larger than w, we take a square of size w from the top.
    # Let's add a safety check.
    crop_height = min(w, h)
    
    # Actually, looking at the image, the text "Bulk Pulse" is quite close.
    # Let's take the top 60% of the cropped content height if it's taller than wide.
    if h > w:
        crop_height = int(h * 0.55) # Take top 55%
    
    icon_box = (0, 0, w, crop_height)
    favicon = cropped.crop(icon_box)
    
    # Resize to favicon size
    favicon = favicon.resize((64, 64), Image.Resampling.LANCZOS)
    
    # Save as favicon.png
    favicon.save("static/favicon.png")
    print("Favicon saved successfully as 64x64 PNG!")
else:
    print("No content found in image!")
