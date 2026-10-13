"""Rule-based resource health checks. High usage is a resource warning, not attack evidence."""
from .storage import add_event

def run_health_check(metrics, settings):
    checks=[]
    for metric,label in (("cpu_percent","CPU usage"),("ram_percent","RAM usage"),("disk_percent","Disk usage")):
        value=metrics.get(metric); warning=settings[f"{metric.split('_')[0]}_warning"]; critical=settings[f"{metric.split('_')[0]}_critical"]
        if value is None:
            severity="Info"; result="Unavailable"; action="Check local permissions and supported system metrics."
        elif value >= critical:
            severity="Critical"; result="Critical resource usage"; action="Review active applications and available capacity; investigate expected workload."
        elif value >= warning:
            severity="Warning"; result="Resource warning"; action="Review resource use and close unneeded workloads if appropriate."
        else:
            severity="Healthy"; result="Within configured thresholds"; action="No action needed; continue monitoring."
        check={"metric":label,"value":value,"warning":warning,"critical":critical,"severity":severity,"result":result,"action":action}
        checks.append(check)
        add_event("Health check", severity, f"{label}: {result}.", {metric:value,"warning_threshold":warning,"critical_threshold":critical}, result=result)
    return checks
