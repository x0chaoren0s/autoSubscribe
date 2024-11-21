#!/bin/bash

# 获取当前脚本所在目录绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# 设置必要的环境变量
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/dellu/bin
export HOME=/home/dellu
# 如果glider是通过conda安装的，需要初始化conda
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate autoSubscribe

# 进入项目根目录
cd $ROOT_DIR

# 添加日志输出，便于调试
exec 1>> $ROOT_DIR/results/output/cron.log 2>&1

echo "[$(date)] Starting script execution..."
echo "Current directory: $(pwd)"
echo "PATH: $PATH"
echo "Python path: $(which python)"

# 运行python脚本
python autoSubscribe.py --filter_subscriptions

echo "[$(date)] Script execution completed"