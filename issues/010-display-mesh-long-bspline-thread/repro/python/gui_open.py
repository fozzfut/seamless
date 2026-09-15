"""GUI open benchmark. Run as: QT_QPA_PLATFORM=offscreen FreeCAD.exe -u <copy> -s <copy> gui_open.py
Env: PERF_FILE, PERF_OUT, PERF_PROFILE=1 (cProfile around open + idle wait), PERF_IDLE_MS (default 600),
PERF_GUILOG=1 (FreeCAD log level Log for Gui/App tags).
Timeline: process creation -> this script -> FreeCADGui.open() returns -> event loop idle."""
import os, sys, time, json, ctypes, collections

T_SCRIPT = time.perf_counter()


def process_age_s():
    k = ctypes.windll.kernel32
    k.GetCurrentProcess.restype = ctypes.c_void_p
    k.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.c_void_p] * 4
    ct, et, kt, ut, now = (ctypes.c_ulonglong() for _ in range(5))
    k.GetProcessTimes(k.GetCurrentProcess(), ctypes.byref(ct), ctypes.byref(et), ctypes.byref(kt), ctypes.byref(ut))
    k.GetSystemTimeAsFileTime(ctypes.byref(now))
    return (now.value - ct.value) / 1e7, (kt.value + ut.value) / 1e7


import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

path = os.environ["PERF_FILE"]
out = os.environ["PERF_OUT"]
res = {"file": path, "tag": os.environ.get("PERF_TAG", "")}
age, cpu = process_age_s()
res["startup_wall_s"] = age
res["startup_cpu_s"] = cpu
res["active_workbench"] = Gui.activeWorkbench().name() if Gui.activeWorkbench() else None
res["workbenches"] = sorted(Gui.listWorkbenches().keys())
res["mod_dirs"] = [d for d in getattr(App, "__ModDirs__", [])]
res["user_app_data"] = App.getUserAppDataDir()
res["hd_loaded"] = "HybridDesignWorkbench" in Gui.listWorkbenches()
res["hd_modules_at_start"] = sorted(m for m in sys.modules if m.startswith("hybriddesign"))
if os.environ.get("PERF_GUILOG"):
    for t in ("App", "Gui", "Part", "PartGui", "Document", "Assembly", "AssemblyGui"):
        try:
            App.setLogLevel(t, "Log")
        except Exception:
            pass

prof = None
if os.environ.get("PERF_PROFILE"):
    import cProfile
    prof = cProfile.Profile()

vp_orig = {}
IDLE_MS = int(os.environ.get("PERF_IDLE_MS", "600"))
TICK = 20
LATE = 40
state = {"t_open0": None, "t_open1": None, "last_busy": None, "quiet": 0.0, "prev": None, "max_gap": 0.0, "gaps": []}


def finish():
    t_idle = state["last_busy"]
    if prof is not None:
        prof.disable()
    res["gui_open_call_s"] = state["t_open1"] - state["t_open0"]
    res["open_to_idle_s"] = t_idle - state["t_open0"]
    res["after_open_busy_s"] = t_idle - state["t_open1"]
    res["event_gaps_over_100ms"] = [round(g, 3) for g in state["gaps"] if g > 0.1][:50]
    res["max_event_gap_s"] = state["max_gap"]
    doc = App.ActiveDocument
    if doc:
        res["n_objects"] = len(doc.Objects)
        res["touched_after_open"] = [o.Name for o in doc.Objects if "Touched" in o.State]
        gdoc = Gui.getDocument(doc.Name)
        vps = 0
        vis = 0
        for o in doc.Objects:
            vp = gdoc.getObject(o.Name)
            if vp:
                vps += 1
                try:
                    vis += 1 if vp.Visibility else 0
                except Exception:
                    pass
        res["view_providers"] = vps
        res["visible_vps"] = vis
    res["hd_modules_after"] = len([m for m in sys.modules if m.startswith("hybriddesign")])
    if os.environ.get("PERF_TESS") and doc:
        # Replays ViewProviderPartExt::updateVisual through its own trigger: a change of AngularDeflection
        # re-meshes a visible object synchronously (ViewProviderExt.cpp:951 at 1.1.1). A +1e-4 degree
        # change reproduces the stored parameters; 28.5 is FreeCAD's default.
        gdoc = Gui.getDocument(doc.Name)
        tess = {}
        for label, target in (("stored", None), ("ang28_5", 28.5), ("stored_again", None)):
            rows = []
            for o in doc.Objects:
                vp = gdoc.getObject(o.Name)
                if not vp or "AngularDeflection" not in vp.PropertiesList:
                    continue
                if not vp.Visibility:
                    continue
                cur = float(vp.AngularDeflection)
                orig = vp_orig.setdefault(o.Name, cur)
                new = (orig + 1e-4 if cur == orig else orig) if target is None else target
                ta = time.perf_counter()
                vp.AngularDeflection = new
                rows.append((time.perf_counter() - ta, o.Name, o.TypeId, cur, new, float(vp.Deviation)))
            rows.sort(reverse=True)
            tess[label] = {"total_s": sum(r[0] for r in rows), "n": len(rows),
                           "top": [[round(r[0], 4), r[1], r[2], r[4], r[5]] for r in rows[:10]]}
        res["tessellation_replay"] = tess
    res["process_wall_at_end_s"], res["process_cpu_at_end_s"] = process_age_s()
    if prof is not None:
        import pstats, io
        st = pstats.Stats(prof)
        s = io.StringIO()
        st.stream = s
        st.sort_stats("cumulative").print_stats(60)
        s.write("\n==== tottime ====\n")
        st.sort_stats("tottime").print_stats(40)
        with open(out.replace(".json", "_profile.txt"), "w", encoding="utf-8") as f:
            f.write(s.getvalue())
        # HybridDesign entry points: HD functions with no HD caller
        hd_entries = []
        hd_self = 0.0
        for func, (cc, nc, tt, ct, callers) in st.stats.items():
            fn = func[0].replace("\\", "/").lower()
            if "hybriddesign" not in fn:
                continue
            hd_self += tt
            if not any("hybriddesign" in c[0].replace("\\", "/").lower() for c in callers):
                hd_entries.append((ct, nc, "%s:%d(%s)" % (func[0].split("HybridDesign")[-1], func[1], func[2])))
        hd_entries.sort(reverse=True)
        res["hd_entry_cumtime_s"] = sum(e[0] for e in hd_entries)
        res["hd_python_selftime_s"] = hd_self
        res["hd_entries_top"] = [[round(e[0], 4), e[1], e[2]] for e in hd_entries[:25]]
        total = sum(v[2] for v in st.stats.values())
        res["profiled_python_total_tottime_s"] = total
    with open(out, "w") as f:
        json.dump(res, f, indent=1)
    print("PERF-DONE", json.dumps({k: res.get(k) for k in ("startup_wall_s", "gui_open_call_s", "after_open_busy_s", "open_to_idle_s", "hd_loaded", "hd_entry_cumtime_s")}))
    sys.stdout.flush()
    try:  # close so no recovery/transient directory is left behind, then leave without saving prefs
        for name in list(App.listDocuments().keys()):
            App.closeDocument(name)
    except Exception:
        pass
    os._exit(0)


def tick():
    now = time.perf_counter()
    gap = now - state["prev"]
    state["prev"] = now
    if gap > state["max_gap"]:
        state["max_gap"] = gap
    if gap * 1000 > TICK + LATE:
        state["gaps"].append(gap)
        state["last_busy"] = now
        state["quiet"] = 0.0
    else:
        state["quiet"] += gap
    if state["quiet"] * 1000 >= IDLE_MS or now - state["t_open0"] > 900:
        finish()
        return
    QtCore.QTimer.singleShot(TICK, tick)


def do_open():
    res["script_to_open_s"] = time.perf_counter() - T_SCRIPT
    if prof is not None:
        prof.enable()
    state["t_open0"] = time.perf_counter()
    # Gui::Application::open() for an .FCStd runs exactly this command (Gui/Application.cpp:766 at 1.1.1);
    # FreeCADGui.open() from Python answered "File type 'fcstd' not supported" in this mode.
    try:
        Gui.doCommand("FreeCAD.openDocument(%r)" % path) if hasattr(Gui, "doCommand") else App.openDocument(path)
    except Exception as e:
        res["open_error"] = str(e)
    if App.ActiveDocument is None:
        try:
            App.openDocument(path)
        except Exception as e:
            res["open_error2"] = str(e)
    state["t_open1"] = time.perf_counter()
    state["last_busy"] = state["t_open1"]
    state["prev"] = state["t_open1"]
    QtCore.QTimer.singleShot(TICK, tick)


# let delayed start-up (autoload workbench, theme timers) settle first, like a user who opens a file
# a few seconds after the window appeared
def wait_startup_idle():
    st = {"prev": time.perf_counter(), "quiet": 0.0, "t0": time.perf_counter()}

    def t():
        now = time.perf_counter()
        gap = now - st["prev"]
        st["prev"] = now
        st["quiet"] = 0.0 if gap * 1000 > TICK + LATE else st["quiet"] + gap
        if st["quiet"] * 1000 >= 1000 or now - st["t0"] > 120:
            res["startup_settle_s"] = now - st["t0"]
            res["startup_wall_before_open_s"] = process_age_s()[0]
            do_open()
            return
        QtCore.QTimer.singleShot(TICK, t)

    QtCore.QTimer.singleShot(TICK, t)


wait_startup_idle()
