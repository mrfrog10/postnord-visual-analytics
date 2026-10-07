"""python render_all.py <workbook.twbx> <out_dir> [window names...]: one screenshot per dashboard or sheet."""
import re, subprocess, sys, tempfile, zipfile
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
z = zipfile.ZipFile(src)
twb_name = next(n for n in z.namelist() if n.endswith(".twb"))
xml = z.read(twb_name).decode("utf-8")
names = sys.argv[3:] or re.findall(r'<dashboard name=["\x27]([^"\x27]+)["\x27]', xml)
tmp = Path(tempfile.mkdtemp())
for n in names:
    m = re.search(r'<window class=["\x27](dashboard|worksheet)["\x27] name=["\x27]%s["\x27]>' % re.escape(n), xml)
    x = xml.replace(m.group(0), m.group(0).replace("<window ", '<window maximized="true" ', 1), 1)
    t = tmp / (re.sub(r"[^A-Za-z0-9]+", "_", n) + ".twbx")
    with zipfile.ZipFile(t, "w", zipfile.ZIP_DEFLATED) as o:
        for i in z.infolist():
            o.writestr(i.filename, x if i.filename == twb_name else z.read(i.filename))
    png = out / (re.sub(r"[^A-Za-z0-9]+", "_", n) + ".png")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(Path(__file__).with_name("render.ps1")),
                        "-Twbx", str(t), "-Png", str(png)], capture_output=True, text=True)
    print(n, "->", r.stdout.strip() or r.stderr.strip()[:300])
