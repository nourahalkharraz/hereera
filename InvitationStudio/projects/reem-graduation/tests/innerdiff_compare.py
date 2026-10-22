"""يقارن لقطات innerdiff.js: لكل شاشة عدد البكسلات المختلفة وأقصى فرق وحدود المنطقة المختلفة."""
import sys, glob, os
import numpy as np
from PIL import Image
out = sys.argv[1] if len(sys.argv) > 1 else 'diff-out'
total = 0
for old in sorted(glob.glob(os.path.join(out, 'old_*.png'))):
    new = old.replace(os.sep + 'old_', os.sep + 'new_')
    if not os.path.exists(new):
        print('missing', new); continue
    a = np.asarray(Image.open(old).convert('RGB')).astype(int)
    b = np.asarray(Image.open(new).convert('RGB')).astype(int)
    if a.shape != b.shape:
        print(os.path.basename(old), 'size differs', a.shape, b.shape); continue
    d = np.abs(a - b).max(2); ys, xs = np.where(d > 2); total += len(xs)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None
    print(f"{os.path.basename(old)[4:-4]:8} diff px {len(xs):7d}  max {int(d.max()):3d}  bbox {bbox}")
print('TOTAL differing px', total)
