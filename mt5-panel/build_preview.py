"""Bundle the panel into one self-contained HTML file.

The result is the real interface — same markup, same stylesheet, same app.js —
with web/preview-mock.js standing in for the python server, so it can be opened
from anywhere with no PC and no MetaTrader running.

    python build_preview.py [output.html]
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")


def read(name):
    with open(os.path.join(WEB, name), "r", encoding="utf-8") as fh:
        return fh.read()


def build():
    html = read("index.html")

    # keep only what lives inside <body> — the artifact host supplies the shell
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.S).group(1)
    body = re.sub(r'<script src="[^"]*"></script>', "", body)
    body = body.replace('<script>window.PANEL_KEY = "__PANEL_KEY__";</script>', "")

    banner = """
<div id="preview-banner">
  <strong>معاينة</strong>
  <span>أسعار وهمية · غير متصلة بأي حساب · ما فيه أوامر حقيقية</span>
</div>
"""

    extra_css = """
/* preview-only chrome */
#preview-banner {
  position: fixed; inset-inline: 0; top: 0; z-index: 300;
  background: var(--surface-2); border-bottom: 1px solid var(--line);
  padding: 7px 14px; display: flex; gap: 8px; align-items: baseline;
  justify-content: center; flex-wrap: wrap;
  font-family: 'Tahoma', 'Segoe UI', system-ui, sans-serif;
  font-size: 11.5px; color: var(--ink-2);
}
#preview-banner strong {
  color: var(--buy); font-size: 11px; letter-spacing: .6px;
  text-transform: uppercase; font-weight: 800;
}
body { padding-top: 46px; }
@media (max-width: 560px) {
  body { padding-top: 34px; }
  #phone { height: calc(100vh - 34px); height: calc(100dvh - 34px); }
  #topbar { padding-top: 12px; }
}
"""

    parts = [
        "<title>MT5 Panel — معاينة</title>",
        "<style>\n" + read("app.css") + extra_css + "</style>",
        banner,
        body.strip(),
        "<script>\n" + read("i18n.js") + "\n</script>",
        "<script>\n" + read("preview-mock.js") + "\n</script>",
        "<script>\n" + read("app.js") + "\n</script>",
    ]
    return "\n".join(parts)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "preview.html")
    page = build()
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("wrote %s (%.0f KB)" % (out, len(page.encode("utf-8")) / 1024.0))
