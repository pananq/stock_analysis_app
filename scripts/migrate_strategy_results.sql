#!/bin/bash
# MySQL数据库迁移脚本 - 添加strategy_results表缺少的字段

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 读取配置
DB_HOST=$(python3 -c "import yaml; print(yaml.safe_load(open('$PROJECT_DIR/config.yaml'))['database']['mysql'].get('host', 'localhost'))" 2>/dev/null || echo "localhost")
DB_PORT=$(python3 -c "import yaml; print(yaml.safe_load(open('$PROJECT_DIR/config.yaml'))['database']['mysql'].get('port', 3306))" 2>/dev/null || echo "3306")
DB_USER=$(python3 -c "import yaml; print(yaml.safe_load(open('$PROJECT_DIR/config.yaml'))['database']['mysql']['user'])" 2>/dev/null)
DB_PASSWORD=$(python3 -c "import yaml; print(yaml.safe_load(open('$PROJECT_DIR/config.yaml'))['database']['mysql']['password'])" 2>/dev/null)
DB_NAME=$(python3 -c "import yaml; print(yaml.safe_load(open('$PROJECT_DIR/config.yaml'))['database']['mysql']['database'])" 2>/dev/null)

echo "正在连接MySQL数据库..."
echo "主机: $DB_HOST:$DB_PORT"
echo "数据库: $DB_NAME"

# 添加缺少的字段到strategy_results表
echo ""
echo "添加缺少的字段到strategy_results表..."

mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" << 'EOF' 2>/dev/null || mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" << 'EOF'

-- 添加stock_name字段（如果不存在）
ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS stock_name VARCHAR(100) AFTER stock_code;

-- 添加trigger_pct_change字段（如果不存在）
ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS trigger_pct_change DECIMAL(10,2) AFTER trigger_price;

-- 添加observation_days字段（如果不存在）
ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS observation_days INT AFTER trigger_pct_change;

-- 添加ma_period字段（如果不存在）
ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS ma_period INT AFTER observation_days;

-- 添加observation_result字段（如果不存在）
ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS observation_result TEXT AFTER ma_period;

-- 添加created_at字段（如果不存在）
ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP AFTER executed_at;

EOF

if [ $? -eq 0 ]; then
    echo "✓ 数据库迁移成功完成"
else
    echo "✗ 数据库迁移失败"
    exit 1
fi

echo ""
echo "验证表结构..."
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "DESCRIBE strategy_results;" 2>/dev/null || echo "无法验证表结构"

echo ""
echo "迁移完成！"
