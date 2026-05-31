print("="*50)
print("  DRIVE SAFE AI - MONITORAMENTO BÁSICO DE SONOLÊNCIA")
print("="*50)
print()

from vision.driver_monitor import SimpleDriverMonitor

if __name__ == "__main__":
    monitor = SimpleDriverMonitor()
    monitor.start(camera_id=0)
