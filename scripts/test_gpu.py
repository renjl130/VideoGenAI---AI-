"""
GPU检测测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_nvidia_smi():
    """直接测试nvidia-smi"""
    import subprocess

    print("=" * 50)
    print("测试 nvidia-smi 命令")
    print("=" * 50)

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            print("✓ nvidia-smi 可用")
            print(f"\n输出:\n{result.stdout}")

            lines = result.stdout.strip().split("\n")
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 8:
                    print(f"\nGPU {parts[0]}:")
                    print(f"  名称: {parts[1]}")
                    print(f"  总显存: {parts[2]} MB")
                    print(f"  已用显存: {parts[3]} MB")
                    print(f"  可用显存: {parts[4]} MB")
                    print(f"  温度: {parts[5]}°C")
                    print(f"  利用率: {parts[6]}%")
                    print(f"  功耗: {parts[7]} W")

            return True
        else:
            print("✗ nvidia-smi 失败")
            print(f"错误: {result.stderr}")
            return False

    except FileNotFoundError:
        print("✗ nvidia-smi 未找到")
        return False
    except Exception as e:
        print(f"✗ 异常: {e}")
        return False


def test_gpu_monitor():
    """测试GPU监控模块"""
    print("\n" + "=" * 50)
    print("测试 GPU 监控模块")
    print("=" * 50)

    try:
        from utils.gpu_monitor import format_memory, get_gpu_monitor

        monitor = get_gpu_monitor()

        print(f"\nGPU数量: {monitor.gpu_count}")
        print(f"GPU名称: {monitor.gpu_names}")

        # 获取所有GPU信息
        all_info = monitor.get_all_gpu_info()
        print(f"\n获取到 {len(all_info)} 个GPU的信息")

        for info in all_info:
            print(f"\n--- GPU {info.device_id} ---")
            print(f"  名称: {info.name}")
            memory_text = (
                f"{format_memory(info.used_memory)} / "
                f"{format_memory(info.total_memory)} "
                f"({info.memory_usage_percent:.1f}%)"
            )
            print(f"  显存: {memory_text}")
            print(f"  温度: {info.temperature}°C")
            print(f"  利用率: {info.utilization}%")
            print(f"  功耗: {info.power_usage:.1f}W")
            print(f"  驱动版本: {info.driver_version}")

        return True

    except Exception as e:
        print(f"✗ GPU监控模块失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_backend():
    """测试后端GPU获取"""
    print("\n" + "=" * 50)
    print("测试后端 GPU 获取")
    print("=" * 50)

    try:
        from backend.engine_manager import get_backend_manager

        backend = get_backend_manager()
        gpu_infos = backend.get_gpu_info()

        print(f"\n从后端获取到 {len(gpu_infos)} 个GPU的信息")

        for info in gpu_infos:
            print(f"\nGPU {info.device_id}: {info.name}")
            print(f"  显存: {info.used_memory}/{info.total_memory} MB")
            print(f"  温度: {info.temperature}°C")

        return True

    except Exception as e:
        print(f"✗ 后端测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("  VideoGenAI GPU 检测测试")
    print("=" * 60)

    results = []

    results.append(("nvidia-smi", test_nvidia_smi()))
    results.append(("GPU监控模块", test_gpu_monitor()))
    results.append(("后端GPU获取", test_backend()))

    print("\n" + "=" * 60)
    print("  测试结果")
    print("=" * 60)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")

    if all(r for _, r in results):
        print("\n✓ 所有测试通过！GPU检测正常工作。")
        return 0
    else:
        print("\n✗ 部分测试失败。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
