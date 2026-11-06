#!/usr/bin/env python3
"""Windows ISO -> USB flashka na macOS (UEFI/GPT, FAT32).
Ispolzovaniye: python3 mkwinusb.py Win.iso
"""
import os
import plistlib
import shutil
import subprocess
import sys
import time

LABEL = "WINUSB"
FAT32_MAX = 4 * 1024**3 - 1
CHUNK = 4 * 1024 * 1024


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def plist(cmd):
    out = subprocess.run(cmd, check=True, capture_output=True).stdout
    return plistlib.loads(out)


def fmt_size(n):
    return f"{n / 1024**3:.2f} GB" if n >= 1024**3 else f"{n / 1024**2:.0f} MB"


def fmt_time(s):
    s = int(s)
    return f"{s // 60:02d}:{s % 60:02d}"


class Progress:
    def __init__(self, total):
        self.total = max(total, 1)
        self.done = 0
        self.start = time.time()
        self.last = 0
        self.name = ""

    def add(self, n, name=None, force=False):
        self.done += n
        if name:
            self.name = name
        now = time.time()
        if not force and now - self.last < 0.1:
            return
        self.last = now
        self.draw(now)

    def draw(self, now):
        frac = min(self.done / self.total, 1)
        elapsed = now - self.start
        speed = self.done / elapsed if elapsed > 0 else 0
        eta = (self.total - self.done) / speed if speed > 0 else 0
        cols = shutil.get_terminal_size((80, 20)).columns
        width = max(10, min(30, cols - 62))
        filled = int(width * frac)
        bar = "█" * filled + "░" * (width - filled)
        line = (f"\r{bar} {frac * 100:5.1f}%  "
                f"{fmt_size(self.done)}/{fmt_size(self.total)}  "
                f"{speed / 1024**2:5.1f} MB/s  ostalos {fmt_time(eta)}")
        extra = cols - len(line) - 1
        if extra > 8 and self.name:
            n = self.name[-(extra - 3):]
            line += f"  {n}"
        sys.stdout.write(line.ljust(cols - 1)[:cols - 1])
        sys.stdout.flush()


def copy_tree(src, dest, skip_rel):
    files = []
    for root, _, names in os.walk(src):
        for n in names:
            p = os.path.join(root, n)
            rel = os.path.relpath(p, src)
            if rel == skip_rel:
                continue
            files.append((p, rel, os.path.getsize(p)))
    prog = Progress(sum(f[2] for f in files))
    for p, rel, size in files:
        out = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(p, "rb") as fi, open(out, "wb") as fo:
            while True:
                buf = fi.read(CHUNK)
                if not buf:
                    break
                fo.write(buf)
                prog.add(len(buf), rel)
            fo.flush()
            os.fsync(fo.fileno())
        if size == 0:
            prog.add(0, rel)
    prog.add(0, "", force=True)
    print()


def erase(disk):
    dev = f"/dev/{disk}"
    for _ in range(3):
        subprocess.run(["diskutil", "unmountDisk", "force", dev], capture_output=True)
        r = subprocess.run(["diskutil", "eraseDisk", "MS-DOS", LABEL, "GPT", dev],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return
        print((r.stdout + r.stderr).strip())
        time.sleep(2)
    sys.exit("Ne udalos otformatirovat. Vyyni i vstav flashku zanovo i zapusti opyat.")


def safe_eject(disk):
    dev = f"/dev/{disk}"
    for _ in range(5):
        if subprocess.run(["diskutil", "eject", dev], capture_output=True).returncode == 0:
            return True
        time.sleep(2)
    subprocess.run(["diskutil", "unmountDisk", "force", dev], capture_output=True)
    return subprocess.run(["diskutil", "eject", dev], capture_output=True).returncode == 0


def list_usb_disks():
    ids = plist(["diskutil", "list", "-plist", "external", "physical"]).get("WholeDisks", [])
    disks = []
    for d in ids:
        info = plist(["diskutil", "info", "-plist", d])
        disks.append((d, info.get("TotalSize", 0), info.get("MediaName", "?")))
    return disks


def ensure_wimlib():
    if shutil.which("wimlib-imagex"):
        return
    if not shutil.which("brew"):
        sys.exit("Nuzhen wimlib (install.wim > 4GB), a brew ne naydyen. Ustanovi Homebrew.")
    print("Stavlyu wimlib cherez brew...")
    run(["brew", "install", "wimlib"])


def main():
    if len(sys.argv) != 2 or not os.path.isfile(sys.argv[1]):
        sys.exit("Ispolzovaniye: python3 mkwinusb.py Win.iso")
    iso = os.path.abspath(sys.argv[1])

    disks = list_usb_disks()
    if not disks:
        sys.exit("Vneshniye diski ne naydeny. Vstav flashku.")

    print("Vneshniye diski:")
    for i, (d, size, name) in enumerate(disks, 1):
        print(f"  {i}) {d}  {size / 1e9:.1f} GB  {name}")
    try:
        choice = int(input("Nomer diska: ")) - 1
        if choice < 0:
            raise IndexError
        disk, size, name = disks[choice]
    except (ValueError, IndexError):
        sys.exit("Nepravilniy nomer.")

    print(f"\nVSE DANNYYE na {disk} ({name}, {size / 1e9:.1f} GB) budut udaleny!")
    if input(f"Vvedi '{disk}' dlya podtverzhdeniya: ").strip() != disk:
        sys.exit("Otmena.")

    t0 = time.time()
    print("\n[1/4] Formatirovaniye...")
    erase(disk)
    dest = f"/Volumes/{LABEL}"
    if not os.path.isdir(dest):
        sys.exit(f"{dest} ne smontirovan.")
    open(os.path.join(dest, ".metadata_never_index"), "w").close()

    print("[2/4] Montiruyu ISO...")
    res = plist(["hdiutil", "attach", "-plist", "-readonly", "-nobrowse", iso])
    src = next(e["mount-point"] for e in res["system-entities"] if "mount-point" in e)

    try:
        wim = os.path.join(src, "sources", "install.wim")
        big = os.path.isfile(wim) and os.path.getsize(wim) > FAT32_MAX

        print("[3/4] Kopiruyu fayly...")
        copy_tree(src, dest, os.path.join("sources", "install.wim") if big else None)

        print("[4/4] install.wim...")
        if big:
            ensure_wimlib()
            print(f"Razmer {fmt_size(os.path.getsize(wim))} > 4GB, razbivayu na chasti...")
            run(["wimlib-imagex", "split", wim,
                 os.path.join(dest, "sources", "install.swm"), "3800"])
        else:
            print("Razmer < 4GB, uzhe skopirovano.")
    except KeyboardInterrupt:
        print("\nPrervano. Flashka ne gotova.")
        sys.exit(1)
    finally:
        subprocess.run(["hdiutil", "detach", src], capture_output=True)

    print("Zapis na disk (sync)...")
    run(["sync"])
    if safe_eject(disk):
        print(f"\n✅ Gotovo za {fmt_time(time.time() - t0)}. Flashka izvlechena (UEFI).")
    else:
        print(f"\n✅ Gotovo za {fmt_time(time.time() - t0)}, no avtoizvlecheniye ne srabotalo.\n"
              "Fayly zapisany. Izvlechi flashku vruchnuyu cherez Finder.")


if __name__ == "__main__":
    main()
