#!/usr/bin/env python3
"""
BT396 批量策略回测脚本
自动运行所有策略并生成汇总报告
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime

# Python解释器路径 - 使用当前运行的Python解释器
PYTHON_PATH = sys.executable

# 策略配置列表
STRATEGIES = [
    {
        "name": "s1_dual_ma_crossover",
        "display_name": "策略1: 双均线策略 (Series 04)",
        "output_dir": "output/individual_strategies/s1_dual_ma"
    },
    {
        "name": "s2_buy_and_hold",
        "display_name": "策略2: 买入持有策略 (Series 05)",
        "output_dir": "output/individual_strategies/s2_buy_hold"
    },
    {
        "name": "s3_mean_reversion",
        "display_name": "策略3: 均值回归策略 (Series 09)",
        "output_dir": "output/individual_strategies/s3_mean_reversion"
    },
    {
        "name": "combined_cvar_strategy",
        "display_name": "组合策略: CVaR组合",
        "output_dir": "output/combined_strategy"
    }
]

def print_header(text, char='='):
    """打印格式化的标题"""
    print(f"\n{char * 60}")
    print(f"  {text}")
    print(f"{char * 60}\n")

def run_strategy(strategy_config, test_period=False):
    """运行单个策略

    Args:
        strategy_config: 策略配置字典
        test_period: 是否使用测试期数据（out-of-sample）
    """
    name = strategy_config["name"]
    display_name = strategy_config["display_name"]
    output_dir = strategy_config["output_dir"]

    print_header(f"正在运行: {display_name}", '-')
    print(f"策略名称: {name}")
    print(f"输出目录: {output_dir}")
    print(f"数据模式: {'测试期 (Out-of-Sample)' if test_period else '完整期'}\n")

    # 构建命令
    cmd = [
        PYTHON_PATH,
        "main.py",
        "--strategy", name,
        "--output-dir", output_dir
    ]

    # 添加测试期标志
    if test_period:
        cmd.append("--test-period")

    # 运行策略
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # 直接显示输出
            text=True
        )
        print(f"\n✓ {display_name} 运行成功！\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {display_name} 运行失败！")
        print(f"错误信息: {e}\n")
        return False

def load_strategy_results():
    """加载所有策略的结果"""
    results = []

    for strategy in STRATEGIES:
        summary_path = Path(strategy["output_dir"]) / "run_summary.json"

        if summary_path.exists():
            with open(summary_path, 'r') as f:
                data = json.load(f)
                results.append({
                    "name": strategy["display_name"],
                    "data": data
                })
        else:
            results.append({
                "name": strategy["display_name"],
                "data": None
            })

    return results

def print_summary_table(results):
    """打印性能汇总表格"""
    print_header("策略性能汇总表", '=')

    # 表头
    print(f"{'策略名称':<30} {'最终价值':>15} {'总收益率':>10} {'年化收益率':>12} {'年化夏普比率':>14} {'最大回撤':>10}")
    print("-" * 104)

    # 表格内容
    for result in results:
        name = result["name"]
        data = result["data"]

        if data:
            final_value = data.get("final_value", 0)
            total_return = data.get("total_return", 0) * 100
            ann_return = data.get("annualized_return", 0) * 100
            sharpe = data.get("annualized_sharpe", 0)
            max_dd = data.get("max_drawdown_pct", 0) * 100

            print(f"{name:<30} £{final_value:>13,.2f} {total_return:>9.2f}% {ann_return:>11.2f}% {sharpe:>14.3f} {max_dd:>9.2f}%")
        else:
            print(f"{name:<30} {'数据未找到':>15}")

    print("-" * 104)

def generate_markdown_report(results):
    """生成Markdown格式的汇总报告"""
    report_path = Path("output/all_strategies_summary.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# BT396 策略回测汇总报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"---\n\n")

        f.write("## 策略性能对比表\n\n")
        f.write("| 策略名称 | 最终价值 | 总收益率 | 年化收益率 | 年化夏普比率 | 最大回撤 |\n")
        f.write("|---------|---------|---------|-----------|-------------|----------|\n")

        for result in results:
            name = result["name"]
            data = result["data"]

            if data:
                final_value = f"£{data.get('final_value', 0):,.2f}"
                total_return = f"{data.get('total_return', 0) * 100:.2f}%"
                ann_return = f"{data.get('annualized_return', 0) * 100:.2f}%"
                sharpe = f"{data.get('annualized_sharpe', 0):.3f}"
                max_dd = f"{data.get('max_drawdown_pct', 0) * 100:.2f}%"

                f.write(f"| {name} | {final_value} | {total_return} | {ann_return} | {sharpe} | {max_dd} |\n")
            else:
                f.write(f"| {name} | N/A | N/A | N/A | N/A | N/A |\n")

        f.write("\n---\n\n")

        f.write("## 详细结果路径\n\n")
        for strategy in STRATEGIES:
            f.write(f"- **{strategy['display_name']}**: `{strategy['output_dir']}/`\n")

        f.write("\n---\n\n")
        f.write("## 输出文件说明\n\n")
        f.write("每个策略目录包含以下文件：\n\n")
        f.write("- `run_summary.json` - 性能指标汇总\n")
        f.write("- `equity_curve.png` - 权益曲线图\n")
        f.write("- `per_series_pd.json` - 各资产PD比率\n")
        f.write("- `equity_dashboard.png` - 综合仪表板\n")
        f.write("- `series_*_cumPnL.png` - 各资产累计盈亏图\n")

    print(f"✓ Markdown汇总报告已生成: {report_path}\n")

def main():
    """主函数"""
    import argparse

    # 添加命令行参数
    parser = argparse.ArgumentParser(description="BT396 批量策略回测系统")
    parser.add_argument("--test-period", action="store_true",
                        help="使用测试期数据（Days 701-1000）进行out-of-sample验证")
    args = parser.parse_args()

    print_header("BT396 策略批量回测系统", '=')

    # 显示数据模式
    data_mode = "测试期 (Out-of-Sample, Days 701-1000)" if args.test_period else "完整期 (Days 1-1000)"
    print(f"数据模式: {data_mode}\n")

    # 记录开始时间
    start_time = datetime.now()
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 运行所有策略
    success_count = 0
    for strategy in STRATEGIES:
        if run_strategy(strategy, test_period=args.test_period):
            success_count += 1

    # 记录结束时间
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print_header("运行结果总结", '=')
    print(f"成功运行: {success_count}/{len(STRATEGIES)} 个策略")
    print(f"总耗时: {duration:.2f} 秒\n")

    # 加载并显示结果
    if success_count > 0:
        results = load_strategy_results()
        print_summary_table(results)
        generate_markdown_report(results)

    print_header("所有任务完成！", '=')
    print("您可以在以下位置查看结果：")
    print("  - 汇总报告: output/all_strategies_summary.md")
    for strategy in STRATEGIES:
        print(f"  - {strategy['display_name']}: {strategy['output_dir']}/")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断运行。")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
