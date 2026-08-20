# -*- coding: utf-8 -*-
"""تحويل شعار (ن + س) من صورة إلى مسارات ناعمة: بلا درجات بكسل، مع الحفاظ على أطراف القلم."""
import numpy as np, math, sys
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure

SRC = 'invitation/assets/monogram-source.jpeg'
U        = 4        # معامل التكبير قبل استخراج الحدود
PRE_SIG  = 0.55     # تنعيم خفيف على الدقة الأصلية (ضد ضجيج JPEG)
POST_SIG = 0.85     # تنعيم بعد التكبير
CORNER   = 44.0     # زاوية الانعطاف التي تُعدّ ركناً حاداً (درجات)
WIN_PTS  = 17       # نافذة قياس الانعطاف بعدد النقاط (مطلقة، لا نسبية)
STEP_PX  = 11.0      # مسافة إعادة التوزيع بالبكسل المكبَّر
SM_SIG   = 3.7      # تنعيم الكنتور بعدد النقاط
DP_TOL   = 1.4      # سماحية التبسيط (بكسل مكبَّر) قبل رسم المنحنيات
MIN_AREA = 400      # أصغر مساحة (بالبكسل المكبَّر) تُعدّ عنصراً حقيقياً
FADE_FROM= 1186.0    # الصف الذي يبدأ عنده خفوت الحبر (بإحداثيات الصورة)
FADE_TO  = 1232.0    # الصف الذي يكتمل عنده الانتقال إلى قياس الخفوت
TAIL_END = 1252.0    # آخر صف فيه حبر حقيقي
FAINT_LO = 9.0      # أدنى فارق عن الخلفية يُعدّ حبراً
FAINT_SPAN = 24.0   # مدى التدرّج فوقه
TIP_FADE = 0.040    # نسبة الطرف الذي يتلاشى شفافيةً
CUT_Y    = 0     # قصّ ذيل الشعار عند أضيق نقطة في الساق
CUT_FADE = 170      # طول التلاشي فوق نقطة القصّ، ليختم الحرف بطرفٍ رفيع

def alpha_field():
    a = np.asarray(Image.open(SRC).convert('RGB')).astype(np.float32)
    mn = a.min(axis=2)
    # الحبر يخفت في نهاية السين حتى يكاد يذوب في الوردي، فتُخفَّض العتبة
    # تدريجياً في تلك المنطقة وحدها كي يُلتقط الطرف الباهت دون التقاط الخلفية.
    # جسم الشعار: عتبة حادّة تحفظ وزن الحرف كما هو
    al = np.clip((mn - 180.0) / 68.0, 0, 1)
    # ذيل السين: الحبر هناك أخفت من الخلفية بفارق ضئيل، فيُطرح ضوء الخلفية
    # نفسه (فتح مورفولوجي) ويُقاس ما تبقّى — هكذا يظهر الطرف الباهت كاملاً.
    bg = ndi.grey_opening(mn, size=(51, 51))
    faint = np.clip((mn - bg - FAINT_LO) / FAINT_SPAN, 0, 1)
    y = np.arange(mn.shape[0]).astype(np.float32)
    w = np.clip((y - FADE_FROM) / (FADE_TO - FADE_FROM), 0, 1)
    w = (w * w * (3 - 2 * w))[:, None]
    w = w * (y[:, None] <= TAIL_END)
    al = np.maximum(al, w * faint)
    al = ndi.gaussian_filter(al, PRE_SIG)
    al = ndi.zoom(al, U, order=3, mode='nearest')
    al = ndi.gaussian_filter(al, POST_SIG)
    if CUT_Y:
        y = np.arange(al.shape[0])[:, None].astype(np.float32)
        al = al * np.clip((CUT_Y - y) / float(CUT_FADE) + 1.0, 0, 1)
    return np.clip(al, 0, 1)

def resample(pts, step):
    """إعادة توزيع نقاط منحنى مفتوح على مسافات متساوية بطول القوس."""
    d = np.sqrt(((pts[1:] - pts[:-1]) ** 2).sum(1))
    s = np.concatenate([[0.0], np.cumsum(d)])
    L = s[-1]
    if L <= 1e-9:
        return pts[:1]
    n = max(2, int(round(L / step)) + 1)
    t = np.linspace(0, L, n)
    return np.column_stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])])

def smooth_closed(pts, sig):
    """تنعيم دوري يحافظ على إغلاق الكنتور."""
    x = ndi.gaussian_filter1d(pts[:, 0], sig, mode='wrap')
    y = ndi.gaussian_filter1d(pts[:, 1], sig, mode='wrap')
    return np.column_stack([x, y])

def corners(pts, win, thr):
    """أركان حادة: زاوية بين الوترين الممتدين نافذةً أمام النقطة وخلفها."""
    n = len(pts)
    k = max(3, int(win))
    idx = []
    for i in range(n):
        a = pts[(i - k) % n] - pts[i]
        b = pts[(i + k) % n] - pts[i]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-9 or nb < 1e-9:
            continue
        c = float(np.clip(np.dot(a, b) / (na * nb), -1, 1))
        turn = 180.0 - math.degrees(math.acos(c))
        if turn > thr:
            idx.append((i, turn))
    # ضمّ الأركان المتجاورة إلى ركن واحد (الأحدّ)
    out, group = [], []
    taken = set(i for i, _ in idx)
    for i, t in idx:
        if group and (i - group[-1][0]) > k:
            out.append(max(group, key=lambda g: g[1])[0]); group = []
        group.append((i, t))
    if group:
        out.append(max(group, key=lambda g: g[1])[0])
    return sorted(set(out))

def simplify(pts, tol):
    """دوغلاس-بوكر: يُسقط النقاط التي لا تغيّر الشكل، فيقلّ عدد المنحنيات دون خسارة."""
    if len(pts) < 3:
        return pts
    keep = np.zeros(len(pts), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        a, b = pts[i], pts[j]
        ab = b - a
        L = np.linalg.norm(ab)
        seg = pts[i + 1:j]
        if L < 1e-9:
            d = np.linalg.norm(seg - a, axis=1)
        else:
            d = np.abs(np.cross(np.broadcast_to(ab, seg.shape), seg - a)) / L
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m)); stack.append((m, j))
    return pts[keep]

def catmull(seg, closed):
    """كاتمُل-روم مركزية (alpha=.5): منحنيات C1 لا تتجاوز نقاطها حتى مع تباعد غير منتظم."""
    p = seg
    n = len(p)
    if n < 2:
        return []
    def P(i):
        if closed:
            return p[i % n]
        return p[min(max(i, 0), n - 1)]
    def dt(a, b):
        return max(1e-6, float(np.linalg.norm(b - a)) ** 0.5)
    segs = []
    last = n if closed else n - 1
    for i in range(last):
        p0, p1, p2, p3 = P(i - 1), P(i), P(i + 1), P(i + 2)
        t1, t2, t3 = dt(p0, p1), dt(p1, p2), dt(p2, p3)
        m1 = (p2 - p1) / t2 - (p2 - p0) / (t1 + t2) + (p1 - p0) / t1
        m2 = (p2 - p1) / t2 - (p3 - p1) / (t2 + t3) + (p3 - p2) / t3
        c1 = p1 + m1 * t2 / 3.0
        c2 = p2 - m2 * t2 / 3.0
        segs.append((c1, c2, p2))
    return segs

def fmt(v):
    return ('%.2f' % v).rstrip('0').rstrip('.')

def path_of(contour):
    sm = smooth_closed(contour, SM_SIG)
    cs = corners(sm, WIN_PTS, CORNER)
    step = STEP_PX
    d = []
    if not cs:
        pts = simplify(resample(np.vstack([sm, sm[:1]]), step), DP_TOL)[:-1]
        segs = catmull(pts, True)
        d.append('M%s %s' % (fmt(pts[0][0]), fmt(pts[0][1])))
        for c1, c2, p2 in segs:
            d.append('C%s %s %s %s %s %s' % (fmt(c1[0]), fmt(c1[1]), fmt(c2[0]), fmt(c2[1]), fmt(p2[0]), fmt(p2[1])))
        d.append('Z')
        return ' '.join(d)
    # مقاطع بين ركن وركن: كلٌّ ينعم داخلياً ويبقى الركن حاداً
    n = len(sm)
    first = None
    for j, ci in enumerate(cs):
        cj = cs[(j + 1) % len(cs)]
        if cj > ci:
            arc = sm[ci:cj + 1]
        else:
            arc = np.vstack([sm[ci:], sm[:cj + 1]])
        arc = simplify(resample(arc, step), DP_TOL)
        segs = catmull(arc, False)
        if first is None:
            first = arc[0]
            d.append('M%s %s' % (fmt(arc[0][0]), fmt(arc[0][1])))
        for c1, c2, p2 in segs:
            d.append('C%s %s %s %s %s %s' % (fmt(c1[0]), fmt(c1[1]), fmt(c2[0]), fmt(c2[1]), fmt(p2[0]), fmt(p2[1])))
    d.append('Z')
    return ' '.join(d)

def main():
    al = alpha_field()
    lab, nlab = ndi.label(al > 0.5)
    keep = [i for i in range(1, nlab + 1) if (lab == i).sum() >= MIN_AREA]
    ys, xs = np.where(np.isin(lab, keep))
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    pad = int(6 * U)
    y0, x0 = max(0, y0 - pad), max(0, x0 - pad)
    y1, x1 = min(al.shape[0] - 1, y1 + pad), min(al.shape[1] - 1, x1 + pad)
    sub = al[y0:y1 + 1, x0:x1 + 1]
    lab2, n2 = ndi.label(sub > 0.5)
    paths, comps = [], []
    for i in range(1, n2 + 1):
        m = (lab2 == i)
        if m.sum() < MIN_AREA:
            continue
        field = np.where(m, sub, 0.0)
        cons = measure.find_contours(field, 0.5)
        if not cons:
            continue
        cons.sort(key=len, reverse=True)
        segs = []
        for c in cons:
            if len(c) < 24:
                continue
            segs.append(path_of(np.column_stack([c[:, 1], c[:, 0]])))  # (x, y)
        if segs:
            comps.append((float(np.where(m)[0].mean()), ' '.join(segs), int(m.sum())))
    comps.sort(key=lambda t: t[0])
    # الإطار يُقصّ عبر viewBox وحده — الإحداثيات تبقى كما هي
    import re as _re
    nums = [(float(a), float(b)) for c in comps
            for a, b in _re.findall(r'(-?[\d.]+) (-?[\d.]+)', c[1])]
    pad = 8.0 * U
    bx0 = min(n[0] for n in nums) - pad; bx1 = max(n[0] for n in nums) + pad
    by0 = min(n[1] for n in nums) - pad; by1 = max(n[1] for n in nums) + pad
    W, H = bx1 - bx0, by1 - by0
    body = ''.join('<path d="%s"/>' % p for _, p, _ in comps)
    # الطرف الأخير من السين يخفت في الأصل حتى يكاد يذوب، فيُعاد ذلك بقناع شفافية
    tip = by1 - H * TIP_FADE
    svg = ('<svg class="mono" viewBox="%.1f %.1f %.1f %.1f" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
           '<defs><linearGradient id="omb" gradientUnits="userSpaceOnUse" x1="0" y1="%.1f" x2="0" y2="%.1f">'
           '<stop offset="0%%" stop-color="#1B2933"/><stop offset="50%%" stop-color="#3B5A6B"/>'
           '<stop offset="100%%" stop-color="#7BA0B2"/></linearGradient>'
           '<linearGradient id="tip" gradientUnits="userSpaceOnUse" x1="0" y1="%.1f" x2="0" y2="%.1f">'
           '<stop offset="0%%" stop-color="#fff"/><stop offset="100%%" stop-color="#fff" stop-opacity="0"/>'
           '</linearGradient>'
           '<mask id="mfade" maskUnits="userSpaceOnUse" x="%.1f" y="%.1f" width="%.1f" height="%.1f">'
           '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#fff"/>'
           '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="url(#tip)"/></mask></defs>'
           '<g fill="url(#omb)" stroke="none" fill-rule="evenodd" mask="url(#mfade)">%s</g></svg>') % (
           bx0, by0, W, H, by0, by1, tip, by1,
           bx0, by0, W, H,
           bx0, by0, W, tip - by0,
           bx0, tip, W, by1 - tip, body)
    open('mono10.svg', 'w').write(svg)
    print('components', len(comps), 'size', W, H, 'bytes', len(svg))
    for cy, p, area in comps:
        print('  cy=%.0f area=%d curves=%d' % (cy, area, p.count('C')))

main()
