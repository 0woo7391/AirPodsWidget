from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "preview.png"

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
BOLD = "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf"

def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

def rr(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def text(draw, xy, value, size, fill, bold=False, anchor=None):
    draw.text(xy, value, font=font(size, bold), fill=fill, anchor=anchor)

def bar(draw, x, y, w, percent, accent=(245,245,247,255)):
    rr(draw, (x,y,x+w,y+8), 4, (255,255,255,28))
    rr(draw, (x,y,x+w*percent/100,y+8), 4, accent)


def media_icon(draw, cx, cy, kind, fill, size=18):
    half = size / 2
    if kind == "play":
        draw.polygon([(cx-half*0.45, cy-half*0.72), (cx+half*0.68, cy), (cx-half*0.45, cy+half*0.72)], fill=fill)
    elif kind == "pause":
        w=size*0.18; h=size*0.62
        draw.rounded_rectangle((cx-size*0.28, cy-h/2, cx-size*0.28+w, cy+h/2), radius=1.5, fill=fill)
        draw.rounded_rectangle((cx+size*0.10, cy-h/2, cx+size*0.10+w, cy+h/2), radius=1.5, fill=fill)
    elif kind == "previous":
        draw.rounded_rectangle((cx-half*0.62, cy-half*0.58, cx-half*0.48, cy+half*0.58), radius=1, fill=fill)
        draw.polygon([(cx+half*0.54, cy-half*0.68), (cx-half*0.38, cy), (cx+half*0.54, cy+half*0.68)], fill=fill)
    elif kind == "next":
        draw.rounded_rectangle((cx+half*0.48, cy-half*0.58, cx+half*0.62, cy+half*0.58), radius=1, fill=fill)
        draw.polygon([(cx-half*0.54, cy-half*0.68), (cx+half*0.38, cy), (cx-half*0.54, cy+half*0.68)], fill=fill)

canvas = Image.new("RGBA", (1600, 900), (20, 22, 28, 255))
# quiet wallpaper gradient
bg = Image.new("RGBA", canvas.size)
p = bg.load()
for y in range(bg.height):
    for x in range(bg.width):
        dx=(x-1180)/900; dy=(y-180)/650
        glow=max(0,1-(dx*dx+dy*dy))
        p[x,y]=(int(21+22*glow), int(23+18*glow), int(31+35*glow),255)
canvas.alpha_composite(bg)

# desktop widget shadow and card
shadow=Image.new("RGBA",canvas.size,(0,0,0,0)); sd=ImageDraw.Draw(shadow)
rr(sd,(135,105,615,570),34,(0,0,0,135)); shadow=shadow.filter(ImageFilter.GaussianBlur(24)); canvas.alpha_composite(shadow)
d=ImageDraw.Draw(canvas)
rr(d,(150,90,600,555),30,(24,24,27,240),(255,255,255,36),1)
text(d,(181,126),"AirPods Pro 3",25,(245,245,247,255),True)
d.ellipse((552,132,560,140),fill=(48,209,88,255))
text(d,(181,158),"연결됨",14,(161,161,166,255))

rows=[("L",87,True),("R",82,True),("CASE",64,False)]
for i,(label,val,worn) in enumerate(rows):
    y=212+i*52
    text(d,(182,y),label,16,(161,161,166,255),True)
    if worn: d.ellipse((227,y+8,233,y+14),fill=(48,209,88,255))
    text(d,(293,y),f"{val}%",17,(245,245,247,255),True,anchor="ra")
    bar(d,320,y+9,235,val)

d.line((181,371,569,371),fill=(255,255,255,32),width=1)
text(d,(181,394),"오늘",12,(161,161,166,255),True)
text(d,(181,417),"2h 14m",21,(245,245,247,255),True)
text(d,(569,394),"현재 세션",12,(161,161,166,255),True,anchor="ra")
text(d,(569,417),"47 min",21,(245,245,247,255),True,anchor="ra")
text(d,(181,466),"The Adults Are Talking — A Very Long…",17,(245,245,247,255),True)
text(d,(181,492),"The Strokes · Spotify",13,(161,161,166,255))
# controls
for cx,kind,primary in [(330,"previous",False),(375,"pause",True),(420,"next",False)]:
    if primary: rr(d,(cx-21,510,cx+21,552),21,(245,245,247,255))
    media_icon(d,cx,531,kind,(24,24,27,255) if primary else (245,245,247,255),18 if primary else 16)

# tray popup
shadow=Image.new("RGBA",canvas.size,(0,0,0,0)); sd=ImageDraw.Draw(shadow)
rr(sd,(1035,348,1425,780),30,(0,0,0,140)); shadow=shadow.filter(ImageFilter.GaussianBlur(22)); canvas.alpha_composite(shadow)
d=ImageDraw.Draw(canvas)
rr(d,(1050,332,1410,764),28,(30,30,33,248),(255,255,255,36),1)
text(d,(1076,366),"AirPods Pro 3",21,(245,245,247,255),True)
text(d,(1076,395),"연결됨",13,(161,161,166,255))
d.ellipse((1371,373,1379,381),fill=(48,209,88,255))
for i,(label,val,worn) in enumerate(rows):
    y=448+i*44
    text(d,(1076,y),label,14,(161,161,166,255),True)
    text(d,(1165,y),f"{val}%",15,(245,245,247,255),True,anchor="ra")
    bar(d,1182,y+8,190,val)
text(d,(1076,592),"오늘",11,(161,161,166,255)); text(d,(1076,613),"2h 14m",17,(245,245,247,255),True)
text(d,(1374,592),"세션",11,(161,161,166,255),anchor="ra"); text(d,(1374,613),"47 min",17,(245,245,247,255),True,anchor="ra")
text(d,(1076,653),"Ditto",16,(245,245,247,255),True)
text(d,(1076,678),"NewJeans · Spotify",12,(161,161,166,255))
for cx,kind,primary in [(1170,"previous",False),(1230,"play",True),(1290,"next",False)]:
    if primary: rr(d,(cx-20,695,cx+20,735),20,(245,245,247,255))
    media_icon(d,cx,715,kind,(24,24,27,255) if primary else (245,245,247,255),17 if primary else 15)

# notification popup
shadow=Image.new("RGBA",canvas.size,(0,0,0,0)); sd=ImageDraw.Draw(shadow)
rr(sd,(1055,78,1450,202),26,(0,0,0,130)); shadow=shadow.filter(ImageFilter.GaussianBlur(20)); canvas.alpha_composite(shadow)
d=ImageDraw.Draw(canvas)
rr(d,(1070,64,1435,188),25,(30,30,33,248),(255,255,255,34),1)
rr(d,(1092,91,1138,137),15,(255,255,255,18))
for i,w in enumerate([23,17,11]): rr(d,(1104,102+i*8,1104+w,105+i*8),2,(245,245,247,255))
text(d,(1157,88),"AirPods 배터리 부족",16,(245,245,247,255),True)
text(d,(1157,118),"오른쪽 10%",14,(245,245,247,255),True)
text(d,(1157,145),"충전이 필요합니다",12,(161,161,166,255))

# labels
text(d,(150,650),"Desktop widget",18,(161,161,166,255),True)
text(d,(1050,806),"Tray popup",18,(161,161,166,255),True)

canvas.convert("RGB").save(OUT,quality=95)

# icon
icon=Image.new("RGBA",(256,256),(0,0,0,0)); idr=ImageDraw.Draw(icon)
rr(idr,(18,18,238,238),62,(23,23,26,255),(255,255,255,35),3)
for i,w in enumerate([118,90,62]): rr(idr,(70,82+i*43,70+w,96+i*43),7,(245,245,247,255))
icon.save(ROOT/"assets/app.ico",sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
