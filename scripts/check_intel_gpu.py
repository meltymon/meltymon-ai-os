import asyncio

from meltymon_ai_os.monitoring.gpu_intel import IntelGPUBackend


async def main():
    backend = IntelGPUBackend()
    gpus = await backend.detect()

    print("=== Erkannte Intel-GPUs ===")

    if not gpus:
        print("Keine Intel-GPU erkannt.")
        return

    for gpu in gpus:
        print(f"Name:       {gpu.name}")
        print(f"Hersteller: {gpu.vendor}")
        print(f"Treiber:    {gpu.driver}")
        print(f"Device-ID:  {gpu.device_id}")
        print(f"Backend:    {gpu.backend}")

        snapshot = await backend.collect(gpu)

        print("\n=== Live-Telemetrie ===")
        print(f"Temperatur:       {snapshot.temperature_celsius} °C")
        print(f"Auslastung:       {snapshot.utilization_percent} %")
        print(f"Leistung:         {snapshot.power_watts} W")
        print(f"Leistungsgrenze:  {snapshot.power_limit_watts} W")
        print(f"Energie:          {snapshot.energy_joules} J")
        print(f"Aktuelle Frequenz:{snapshot.current_frequency_mhz} MHz")
        print(f"Max. Frequenz:    {snapshot.max_frequency_mhz} MHz")
        print(f"Boost-Frequenz:   {snapshot.boost_frequency_mhz} MHz")
        print(f"VRAM verwendet:   {snapshot.memory_used_bytes}")
        print(f"VRAM gesamt:      {snapshot.memory_total_bytes}")


if __name__ == "__main__":
    asyncio.run(main())
