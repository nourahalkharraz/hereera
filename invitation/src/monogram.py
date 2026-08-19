import math

def bez(P, t):
    (x0,y0),(x1,y1),(x2,y2),(x3,y3) = P
    u = 1-t
    x = u**3*x0 + 3*u*u*t*x1 + 3*u*t*t*x2 + t**3*x3
    y = u**3*y0 + 3*u*u*t*y1 + 3*u*t*t*y2 + t**3*y3
    dx = 3*u*u*(x1-x0) + 6*u*t*(x2-x1) + 3*t*t*(x3-x2)
    dy = 3*u*u*(y1-y0) + 6*u*t*(y2-y1) + 3*t*t*(y3-y2)
    return x, y, math.atan2(dy, dx)

def sample(segs, per=90):
    out = []
    for k, P in enumerate(segs):
        m = per if k == len(segs)-1 else per-1
        for i in range(m):
            out.append(bez(P, i/(per-1)))
    return out

def nib(pts, nib_deg=-30, w=64, floor=.19, taper=(.10,.12), wscale=None):
    """Broad-nib stroke: thickness is the nib projected on the direction of
       travel — the thick-and-thin that makes a line read as Arabic script."""
    a = math.radians(nib_deg); L=[]; R=[]; N=len(pts)
    for i,(x,y,th) in enumerate(pts):
        u = i/(N-1)
        hw = w/2 * max(floor, abs(math.sin(th-a)))
        if wscale: hw *= wscale(u)
        for end, amt in ((u, taper[0]), (1-u, taper[1])):
            if amt > 0 and end < amt: hw *= (0.04 + 0.96*(end/amt)**.85)
        nx, ny = -math.sin(th), math.cos(th)
        L.append((x+nx*hw, y+ny*hw)); R.append((x-nx*hw, y-ny*hw))
    return ("M" + " L".join("%.2f,%.2f"%p for p in L)
            + " L" + " L".join("%.2f,%.2f"%p for p in reversed(R)) + " Z")

def diamond(cx, cy, w, h, rot):
    r = math.radians(rot)
    q = [(0,-h/2),(w/2,0),(0,h/2),(-w/2,0)]
    o = [(cx+px*math.cos(r)-py*math.sin(r), cy+px*math.sin(r)+py*math.cos(r)) for px,py in q]
    return "M" + " L".join("%.2f,%.2f"%p for p in o) + " Z"

# ═══ الحرفان مندمجان في مِحبرةٍ واحدة:
#     خطّ السين الأفقي هو نفسه مبتدأ كأس النون، والأسنان تنهض منه.
#     نرسم الكأس مساراً واحداً متّصلاً، والأسنان أشكالاً تعلوه وتلتحم به —
#     لأن الإزاحة المتوازية تنهار عند انعكاس القلم على نفسه. ═══
bowl = sample([
    ((356,166), (324,176), (290,174), (258,168)),   # سطر السين
    ((258,168), (252,244), (246,326), (218,382)),   # ينحدر يميناً
    ((218,382), (186,444), (104,458), ( 54,402)),   # بطن الكأس العميق
    (( 54,402), (  8,348), ( 16,208), ( 88,116)),   # ويصعد إلى طرفٍ رفيع
], per=120)

paths = [nib(bowl, nib_deg=-30, w=86, floor=.18, taper=(.05,.24),
             wscale=lambda u: .58 + .42*min(1.0, u/.24))]

# أسنان السين الثلاث، كلٌّ نهضةٌ واحدة تنتهي بسنٍّ مدبّب
for (bx,by),(tx,ty) in [((344,172),(338, 84)), ((304,178),(299, 90)), ((266,183),(261, 98))]:
    seg = sample([((bx,by), (bx+3, by-34), (tx+5, ty+26), (tx,ty))], 70)
    paths.append(nib(seg, nib_deg=-30, w=40, floor=.40, taper=(0,.62)))

paths.append(diamond(140, 268, 58, 36, -30))   # نقطة النون في حِضن الكأس

svg = ('<svg viewBox="0 0 400 470" fill="currentColor" aria-hidden="true">'
       + "".join('<path d="%s"/>'%p for p in paths) + '</svg>')
open('monogram.svg','w').write(svg)
open('mono-prev.html','w').write(
 '<body style="margin:0;background:#FAF8F4;display:flex;align-items:center;'
 'justify-content:center;height:100vh;color:#26333A">'
 '<div style="width:320px">%s</div></body>' % svg)
print('bytes', len(svg))
