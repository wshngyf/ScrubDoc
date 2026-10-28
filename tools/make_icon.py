"""Build a code-drawn document/shield icon with no external assets."""
from pathlib import Path
from PIL import Image, ImageDraw

folder = Path(__file__).resolve().parents[1] / 'assets'
folder.mkdir(exist_ok=True)
im = Image.new('RGBA', (1024, 1024))
d = ImageDraw.Draw(im)
d.rounded_rectangle((32, 32, 992, 992), radius=220, fill='#2563eb')
d.rounded_rectangle((270, 180, 735, 815), radius=48, fill='white')
d.polygon([(590, 180), (735, 325), (590, 325)], fill='#bfdbfe')
for y, x in [(385, 610), (460, 540), (535, 505)]:
    d.rounded_rectangle((340, y, x, y+25), radius=12, fill='#94a3b8')
d.polygon([(695, 470), (870, 535), (850, 700), (790, 790), (695, 850), (600, 790), (540, 700), (520, 535)], fill='#0f766e')
d.line([(605, 655), (670, 720), (790, 585)], fill='white', width=35, joint='curve')
im.resize((256, 256), Image.Resampling.LANCZOS).save(folder / 'app.png')
im.save(folder / 'app.ico', sizes=[(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)])
