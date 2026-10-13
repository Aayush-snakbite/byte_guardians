"""Safe, read-only collection of local system metrics via psutil."""
import platform
import socket
import time
import psutil

_BOOT_TIME = None

def _safe(call, fallback=None, *args, **kwargs):
    try: return call(*args, **kwargs)
    except (OSError, PermissionError, psutil.Error, AttributeError): return fallback

def collect_metrics():
    global _BOOT_TIME
    cpu = _safe(lambda: psutil.cpu_percent(interval=0.15))
    vm = _safe(psutil.virtual_memory)
    du = _safe(lambda: psutil.disk_usage("/" if platform.system() != "Windows" else "C:\\"))
    net = _safe(psutil.net_io_counters)
    if _BOOT_TIME is None: _BOOT_TIME = _safe(psutil.boot_time)
    uptime = max(0, int(time.time() - _BOOT_TIME)) if _BOOT_TIME else None
    return {
        "cpu_percent": cpu,
        "ram_percent": getattr(vm, "percent", None), "ram_total": getattr(vm, "total", None),
        "ram_available": getattr(vm, "available", None),
        "disk_percent": getattr(du, "percent", None), "disk_total": getattr(du, "total", None),
        "disk_free": getattr(du, "free", None),
        "bytes_recv": getattr(net, "bytes_recv", None), "bytes_sent": getattr(net, "bytes_sent", None),
        "hostname": _safe(socket.gethostname), "os": f"{platform.system()} {platform.release()}",
        "uptime_seconds": uptime, "collected_at": time.time(),
    }

def get_processes(limit=30):
    rows=[]
    try:
        for p in psutil.process_iter(["pid","name","memory_info"]):
            try:
                info=p.info; mem=info.get("memory_info")
                rows.append({"PID":info.get("pid"),"Process":info.get("name") or "Unavailable",
                             "Memory (MB)":round(mem.rss/1024**2,1) if mem else None})
            except (psutil.Error, OSError, PermissionError): continue
    except (psutil.Error, OSError): pass
    return sorted(rows,key=lambda r:r["Memory (MB)"] or 0,reverse=True)[:limit]

def get_interfaces():
    stats=_safe(psutil.net_if_stats,{}) or {}; addrs=_safe(psutil.net_if_addrs,{}) or {}
    counters=_safe(psutil.net_io_counters,pernic=True) or {}
    result=[]
    for name in sorted(set(stats)|set(addrs)):
        ips=[]
        for addr in addrs.get(name,[]):
            if addr.family in (socket.AF_INET, socket.AF_INET6): ips.append(addr.address.split("%",1)[0])
        s=stats.get(name); c=counters.get(name)
        result.append({"Interface":name,"Status":"Up" if getattr(s,"isup",False) else "Down",
                       "Speed (Mbps)":getattr(s,"speed",None),"IP addresses":", ".join(ips) or "Unavailable",
                       "Bytes received":getattr(c,"bytes_recv",None),"Bytes sent":getattr(c,"bytes_sent",None)})
    return result

def get_connections(limit=100):
    rows=[]
    try:
        for c in psutil.net_connections(kind="inet")[:limit]:
            rows.append({"PID":c.pid,"Local":f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "—",
                         "Remote":f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "—","Status":c.status})
    except (psutil.Error, OSError, PermissionError): return None
    return rows
