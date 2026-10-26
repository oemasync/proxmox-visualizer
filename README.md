# Proxmox Visualizer

Live, browser-based view of a Proxmox VE host and its guests — inspired by
[paperdraw.dev](https://paperdraw.dev), but wired to the real machine.

Instead of drawing a system on a canvas, it reads the actual host: CPU, RAM, GPU VRAM,
storage pools, network, and every LXC/VM, and renders them as a topology map with
animated resource-flow edges. Click any node for details. Auto-refreshes every 5s.

## Run

```bash
cd /reiki/projects/proxmox-visualizer
uvicorn backend.main:app --host 0.0.0.0 --port 8801
# open http://<host>:8801
```

## Data sources

- Host / guest metrics: `pvesh get /nodes/pve/{status,lxc,qemu}` (read-only)
- GPU: `nvidia-smi`
- Storage: `pvesm status`

No credentials, no mutations. All playbooks are read-only queries of local state.

## Stack

- Backend: FastAPI + uvicorn (Python)
- Frontend: single-file HTML + SVG + vanilla JS (no build step)

## Endpoints

- `GET /` — the canvas UI
- `GET /api/topology` — full JSON snapshot (host, lxcs, qemu, gpu, storage)

## License

MIT