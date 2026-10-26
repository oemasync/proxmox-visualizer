"""Proxmox Visualizer backend — live view of host + LXCs + resource flow."""
import json, subprocess, time, os, asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Proxmox Visualizer")

HOST_NODE = "pve"

def run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return out.stdout, out.returncode
    except Exception as e:
        return str(e), 1

def pvesh_json(path):
    out, rc = run(["pvesh", "get", path, "--output-format", "json"])
    if rc != 0:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None

def host_status():
    d = pvesh_json(f"/nodes/{HOST_NODE}/status") or {}
    mem = d.get("memory", {})
    cpuinfo = d.get("cpuinfo", {})
    return {
        "node": HOST_NODE,
        "status": "online",
        "uptime": d.get("uptime", 0),
        "cpu_pct": round((d.get("cpu", 0) or 0) * 100, 2),
        "cpu_cores": cpuinfo.get("cores", 0),
        "cpu_threads": cpuinfo.get("cpus", 0),
        "cpu_model": cpuinfo.get("model", ""),
        "mem_total": mem.get("total", 0),
        "mem_used": mem.get("used", 0),
        "mem_free": mem.get("free", 0),
        "mem_avail": mem.get("available", 0),
        "loadavg": d.get("loadavg", []),
        "kernel": (d.get("current-kernel") or {}).get("release", ""),
        "pveversion": d.get("pveversion", ""),
    }

def lxc_list():
    raw = pvesh_json(f"/nodes/{HOST_NODE}/lxc") or []
    out = []
    for c in raw:
        out.append({
            "vmid": c.get("vmid"),
            "name": c.get("name"),
            "status": c.get("status"),
            "cpu_pct": round((c.get("cpu", 0) or 0) * 100, 2),
            "cpus": c.get("cpus", 0),
            "mem": c.get("mem", 0),
            "maxmem": c.get("maxmem", 0),
            "disk": c.get("disk", 0),
            "maxdisk": c.get("maxdisk", 0),
            "diskread": c.get("diskread", 0),
            "diskwrite": c.get("diskwrite", 0),
            "netin": c.get("netin", 0),
            "netout": c.get("netout", 0),
            "uptime": c.get("uptime", 0),
            "tags": c.get("tags", ""),
            "template": bool(c.get("template", 0)),
        })
    return out

def qemu_list():
    raw = pvesh_json(f"/nodes/{HOST_NODE}/qemu") or []
    out = []
    for q in raw:
        out.append({
            "vmid": q.get("vmid"),
            "name": q.get("name"),
            "status": q.get("status"),
            "cpu_pct": round((q.get("cpu", 0) or 0) * 100, 2),
            "cpus": q.get("cpus", 0),
            "mem": q.get("mem", 0),
            "maxmem": q.get("maxmem", 0),
            "diskread": q.get("diskread", 0),
            "diskwrite": q.get("diskwrite", 0),
            "netin": q.get("netin", 0),
            "netout": q.get("netout", 0),
            "uptime": q.get("uptime", 0),
            "tags": q.get("tags", ""),
            "template": bool(q.get("template", 0)),
            "type": "qemu",
        })
    return out

def gpu_status():
    out, rc = run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw", "--format=csv,noheader,nounits"])
    gpus = []
    if rc == 0:
        for line in out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                gpus.append({
                    "name": parts[0],
                    "mem_total_mb": float(parts[1]),
                    "mem_used_mb": float(parts[2]),
                    "util_pct": float(parts[3]),
                    "temp_c": float(parts[4]),
                    "power_w": float(parts[5]),
                })
    # compute apps
    out2, rc2 = run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits"])
    apps = []
    if rc2 == 0:
        for line in out2.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3 and parts[0]:
                apps.append({"pid": parts[0], "name": parts[1], "mem_mb": float(parts[2])})
    return {"gpus": gpus, "compute_apps": apps}

def storage_status():
    out, rc = run(["pvesm", "status"])
    stores = []
    if rc == 0:
        lines = out.strip().splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 6:
                stores.append({
                    "name": parts[0],
                    "type": parts[1],
                    "status": parts[2],
                    "total": int(parts[3]) if parts[3].isdigit() else 0,
                    "used": int(parts[4]) if parts[4].isdigit() else 0,
                    "avail": int(parts[5]) if parts[5].isdigit() else 0,
                })
    return stores

@app.get("/api/topology")
def topology():
    return {
        "ts": time.time(),
        "host": host_status(),
        "lxcs": lxc_list(),
        "qemu": qemu_list(),
        "gpu": gpu_status(),
        "storage": storage_status(),
    }

@app.get("/", response_class=HTMLResponse)
def index():
    with open("/reiki/projects/proxmox-visualizer/frontend/index.html") as f:
        return f.read()

app.mount("/static", StaticFiles(directory="/reiki/projects/proxmox-visualizer/static"), name="static")