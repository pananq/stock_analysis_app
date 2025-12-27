#!/bin/bash

################################################################################
# SQLite 到 MySQL 8.0 数据库迁移自动化脚本
# 
# 功能说明:
# - 自动检查前置条件
# - 备份SQLite数据库和配置文件
# - 安装Python依赖
# - 配置MySQL连接参数
# - 执行数据迁移
# - 验证迁移结果
# - 切换到MySQL数据库
#
# 使用方法:
#   ./migrate_to_mysql.sh [选项]
#
# 选项:
#   --help                显示帮助信息
#   --skip-backup         跳过备份步骤
#   --overwrite           覆盖MySQL中已有数据
#   --auto-confirm        自动确认所有提示
#
# 示例:
#   # 标准迁移
#   ./migrate_to_mysql.sh
#
#   # 覆盖已有数据
#   ./migrate_to_mysql.sh --overwrite
#
#   # 跳过备份（谨慎使用）
#   ./migrate_to_mysql.sh --skip-backup
#
# 作者: 股票分析系统
# 日期: 2025-12-27
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 脚本位于项目根目录，所以SCRIPT_DIR就是PROJECT_ROOT
PROJECT_ROOT="$SCRIPT_DIR"
BACKUP_DIR="${PROJECT_ROOT}/data/backups"
LOG_DIR="${PROJECT_ROOT}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 配置变量
SKIP_BACKUP=false
OVERWRITE=false
AUTO_CONFIRM=false
MYSQL_HOST="localhost"
MYSQL_PORT="3306"
MYSQL_DATABASE="stock_analysis"
MYSQL_USER="stock_user"
MYSQL_PASSWORD="your_password"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# 执行命令并记录错误详情
exec_command() {
    local cmd="$1"
    local error_message="$2"
    local show_cmd="${3:-true}"
    local temp_file
    
    if [ "$show_cmd" = true ]; then
        log_info "执行命令: $cmd"
    fi
    
    temp_file=$(mktemp)
    
    if eval "$cmd" > "$temp_file" 2>&1; then
        rm -f "$temp_file"
        return 0
    else
        local exit_code=$?
        rm -f "$temp_file"
        log_error "命令执行失败！"
        log_error "错误代码: $exit_code"
        log_error "执行的命令: $cmd"
        log_error "错误原因: $error_message"
        return 1
    fi
}

# 静默执行命令（不显示执行的命令，但在失败时显示）
exec_command_silent() {
    local cmd="$1"
    local error_message="$2"
    
    exec_command "$cmd" "$error_message" false
}

# 显示帮助信息
show_help() {
    cat << EOF
SQLite 到 MySQL 8.0 数据库迁移自动化脚本

使用方法:
    $0 [选项]

选项:
    --help                显示帮助信息
    --skip-backup         跳过备份步骤（谨慎使用）
    --overwrite           覆盖MySQL中已有数据
    --auto-confirm        自动确认所有提示（非交互模式）

环境变量（可选）:
    MYSQL_HOST           MySQL主机地址（默认: localhost）
    MYSQL_PORT           MySQL端口（默认: 3306）
    MYSQL_DATABASE       数据库名称（默认: stock_analysis）
    MYSQL_USER           MySQL用户名
    MYSQL_PASSWORD       MySQL密码

示例:
    # 标准迁移（交互式）
    $0

    # 使用环境变量配置
    export MYSQL_HOST=localhost
    export MYSQL_USER=root
    export MYSQL_PASSWORD=your_password
    $0

    # 覆盖已有数据
    $0 --overwrite

    # 完全自动迁移（跳过备份和确认）
    $0 --skip-backup --auto-confirm

EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_help
                exit 0
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --overwrite)
                OVERWRITE=true
                shift
                ;;
            --auto-confirm)
                AUTO_CONFIRM=true
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 确认提示
confirm() {
    local message="$1"
    if [ "$AUTO_CONFIRM" = true ]; then
        log_info "$message [自动确认: 是]"
        return 0
    fi
    
    read -p "$message [是/否]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return 1
    fi
    return 0
}

# 检查Python环境
check_python() {
    log_step "检查Python环境"
    
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请先安装Python3"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    log_info "Python版本: $PYTHON_VERSION"
}

# 检查MySQL服务
check_mysql() {
    log_step "检查MySQL服务"
    
    if ! command -v mysql &> /dev/null; then
        log_error "未找到MySQL客户端，请先安装MySQL"
        log_info "Ubuntu/Debian: sudo apt install mysql-client"
        log_info "CentOS/RHEL: sudo yum install mysql"
        log_info "macOS: brew install mysql-client"
        exit 1
    fi
    
    # 检查MySQL服务是否运行
    local mysql_cmd="mysql -h\"$MYSQL_HOST\" -P\"$MYSQL_PORT\" -u\"$MYSQL_USER\" -p\"$MYSQL_PASSWORD\" -e \"SELECT 1\""
    if ! exec_command_silent "$mysql_cmd" "无法连接到MySQL服务器，请检查服务状态、连接参数和权限"; then
        log_info "请检查:"
        log_info "  1. MySQL服务是否运行"
        log_info "  2. 主机地址和端口是否正确"
        log_info "  3. 用户名和密码是否正确"
        log_info "  4. 防火墙设置"
        exit 1
    fi
    
    log_info "MySQL服务运行正常"
}

# 检查SQLite数据库
check_sqlite() {
    log_step "检查SQLite数据库"
    
    SQLITE_DB="${PROJECT_ROOT}/data/stock_analysis.db"
    
    if [ ! -f "$SQLITE_DB" ]; then
        log_error "SQLite数据库文件不存在: $SQLITE_DB"
        exit 1
    fi
    
    log_info "SQLite数据库文件存在: $SQLITE_DB"
    
    # 检查数据库是否可读
    local sqlite_cmd="sqlite3 \"$SQLITE_DB\" \"SELECT COUNT(*) FROM sqlite_master;\""
    if ! exec_command_silent "$sqlite_cmd" "SQLite数据库文件损坏或无法读取，可能权限不足或文件已损坏"; then
        exit 1
    fi
    
    log_info "SQLite数据库可正常访问"
}

# 创建备份目录
create_backup_dir() {
    log_step "创建备份目录"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "备份目录已创建: $BACKUP_DIR"
    else
        log_info "备份目录已存在: $BACKUP_DIR"
    fi
}

# 备份SQLite数据库
backup_sqlite() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_warn "跳过SQLite数据库备份"
        return 0
    fi
    
    log_step "备份SQLite数据库"
    
    SQLITE_DB="${PROJECT_ROOT}/data/stock_analysis.db"
    BACKUP_FILE="${BACKUP_DIR}/stock_analysis_backup_${TIMESTAMP}.db"
    
    local backup_cmd="cp \"$SQLITE_DB\" \"$BACKUP_FILE\""
    if ! exec_command "$backup_cmd" "备份SQLite数据库失败，请检查磁盘空间或文件权限"; then
        exit 1
    fi
    
    log_info "SQLite数据库已备份: $BACKUP_FILE"
    log_info "备份文件大小: $(du -h "$BACKUP_FILE" | cut -f1)"
}

# 备份配置文件
backup_config() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_warn "跳过配置文件备份"
        return 0
    fi
    
    log_step "备份配置文件"
    
    CONFIG_FILE="${PROJECT_ROOT}/config.yaml"
    BACKUP_FILE="${BACKUP_DIR}/config_backup_${TIMESTAMP}.yaml"
    
    if [ -f "$CONFIG_FILE" ]; then
        local backup_cmd="cp \"$CONFIG_FILE\" \"$BACKUP_FILE\""
        if ! exec_command "$backup_cmd" "备份配置文件失败，请检查文件权限"; then
            exit 1
        fi
        
        log_info "配置文件已备份: $BACKUP_FILE"
    else
        log_warn "配置文件不存在，跳过备份"
    fi
}

# 安装Python依赖
install_dependencies() {
    log_step "检查并安装Python依赖"
    
    cd "$PROJECT_ROOT"
    
    # 检查依赖是否已安装
    log_info "检查PyMySQL..."
    if ! python3 -c "import pymysql" 2>/dev/null; then
        log_info "安装PyMySQL..."
        if ! exec_command "pip3 install pymysql" "安装PyMySQL失败，请检查pip是否可用或网络连接"; then
            exit 1
        fi
    else
        log_info "PyMySQL已安装"
    fi
    
    log_info "检查dbutils..."
    if ! python3 -c "import dbutils" 2>/dev/null; then
        log_info "安装dbutils..."
        if ! exec_command "pip3 install dbutils" "安装dbutils失败，请检查pip是否可用或网络连接"; then
            exit 1
        fi
    else
        log_info "dbutils已安装"
    fi
    
    log_info "检查tqdm..."
    if ! python3 -c "import tqdm" 2>/dev/null; then
        log_info "安装tqdm..."
        if ! exec_command "pip3 install tqdm" "安装tqdm失败，请检查pip是否可用或网络连接"; then
            exit 1
        fi
    else
        log_info "tqdm已安装"
    fi
    
    log_info "所有Python依赖已准备就绪"
}

# 配置MySQL连接参数
configure_mysql() {
    log_step "配置MySQL连接参数"
    
    # 从环境变量读取配置
    MYSQL_HOST=${MYSQL_HOST:-localhost}
    MYSQL_PORT=${MYSQL_PORT:-3306}
    MYSQL_DATABASE=${MYSQL_DATABASE:-stock_analysis}
    
    # 如果没有提供用户名，提示输入
    if [ -z "$MYSQL_USER" ]; then
        if [ "$AUTO_CONFIRM" = true ]; then
            log_error "自动模式下必须通过环境变量提供MYSQL_USER和MYSQL_PASSWORD"
            exit 1
        fi
        read -p "MySQL用户名: " MYSQL_USER
    fi
    
    # 如果没有提供密码，提示输入
    if [ -z "$MYSQL_PASSWORD" ]; then
        if [ "$AUTO_CONFIRM" = true ]; then
            log_error "自动模式下必须通过环境变量提供MYSQL_USER和MYSQL_PASSWORD"
            exit 1
        fi
        read -s -p "MySQL密码: " MYSQL_PASSWORD
        echo
    fi
    
    log_info "MySQL配置:"
    log_info "  主机: $MYSQL_HOST"
    log_info "  端口: $MYSQL_PORT"
    log_info "  数据库: $MYSQL_DATABASE"
    log_info "  用户: $MYSQL_USER"
    
    # 测试连接
    local mysql_test_cmd="mysql -h\"$MYSQL_HOST\" -P\"$MYSQL_PORT\" -u\"$MYSQL_USER\" -p\"$MYSQL_PASSWORD\" \"$MYSQL_DATABASE\" -e \"SELECT 1\""
    if ! exec_command_silent "$mysql_test_cmd" "无法连接到MySQL数据库 $MYSQL_DATABASE，请检查数据库是否存在以及用户权限"; then
        log_info "请检查:"
        log_info "  1. 数据库是否存在"
        log_info "  2. 用户是否有权限"
        exit 1
    fi
    
    log_info "MySQL连接测试成功"
    
    # 设置环境变量供迁移工具使用
    export MYSQL_HOST
    export MYSQL_PORT
    export MYSQL_DATABASE
    export MYSQL_USER
    export MYSQL_PASSWORD
}

# 执行数据迁移
run_migration() {
    log_step "执行数据迁移"
    
    cd "$PROJECT_ROOT"
    
    # 构建迁移命令
    MIGRATE_CMD="python3 tools/migrate_sqlite_to_mysql.py"
    
    if [ "$OVERWRITE" = true ]; then
        MIGRATE_CMD="$MIGRATE_CMD --overwrite"
        log_warn "将覆盖MySQL中已有的数据"
    fi
    
    log_info "执行迁移命令: $MIGRATE_CMD"
    echo ""
    
    # 执行迁移
    if ! exec_command "$MIGRATE_CMD" "数据迁移执行失败，请检查迁移脚本输出或MySQL数据库连接"; then
        log_error "请检查错误信息，或使用回滚工具恢复"
        exit 1
    fi
    
    echo ""
    log_info "数据迁移成功完成"
}

# 验证迁移结果
validate_migration() {
    log_step "验证迁移结果"
    
    cd "$PROJECT_ROOT"
    
    log_info "执行数据验证..."
    echo ""
    
    # 执行验证
    local validate_cmd="python3 tools/validate_data.py"
    if ! exec_command "$validate_cmd" "数据验证失败，可能是数据不一致或验证脚本执行出错"; then
        log_warn "数据验证发现不一致，请查看验证报告"
        log_warn "这可能是正常的差异，也可能是迁移问题"
    else
        log_info "数据验证通过"
    fi
}

# 切换到MySQL数据库
switch_to_mysql() {
    log_step "切换到MySQL数据库"
    
    CONFIG_FILE="${PROJECT_ROOT}/config.yaml"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "配置文件不存在: $CONFIG_FILE"
        exit 1
    fi
    
    # 修改配置文件中的数据库类型
    if command -v yq &> /dev/null; then
        # 使用yq工具（如果可用）
        local yq_cmd="yq eval '.database.type = \"mysql\"' -i \"$CONFIG_FILE\""
        if ! exec_command "$yq_cmd" "使用yq修改配置文件失败"; then
            exit 1
        fi
        log_info "已使用yq工具修改配置文件"
    else
        # 使用sed修改
        if [ "$AUTO_CONFIRM" = true ]; then
            local sed_cmd1="sed -i 's/^  type: sqlite$/  type: mysql/' \"$CONFIG_FILE\""
            local sed_cmd2="sed -i 's/^database:$/database:\\n  type: mysql/' \"$CONFIG_FILE\""
            
            if ! exec_command "$sed_cmd1" "修改配置文件失败（sed命令1）" && 
               ! exec_command "$sed_cmd2" "修改配置文件失败（sed命令2）"; then
                exit 1
            fi
            log_info "已使用sed工具修改配置文件"
        else
            log_warn "未找到yq工具，请手动修改配置文件"
            log_info "编辑 $CONFIG_FILE，将 database.type 改为 mysql"
            
            if ! confirm "是否继续？"; then
                exit 0
            fi
        fi
    fi
    
    log_info "配置已更新，数据库类型: MySQL"
}

# 显示迁移后操作说明
show_post_migration() {
    log_step "迁移完成"
    
    cat << EOF

${GREEN}========================================${NC}
${GREEN}迁移成功完成！${NC}
${GREEN}========================================${NC}

${BLUE}后续操作步骤：${NC}

1. 检查配置文件
   ${YELLOW}cat config.yaml${NC}

2. 重启应用
   ${YELLOW}python main.py${NC}

3. 验证应用功能
   - 检查股票列表是否正常显示
   - 检查策略配置是否正常
   - 检查系统日志是否正常记录

4. 如果遇到问题，可以使用回滚工具
   ${YELLOW}python tools/rollback_migration.py${NC}

${BLUE}备份文件位置：${NC}
   ${YELLOW}$BACKUP_DIR${NC}

${BLUE}验证报告位置：${NC}
   ${YELLOW}$LOG_DIR/data_validation_report_*.json${NC}

${BLUE}相关文档：${NC}
   迁移指南: ${YELLOW}docs/mysql-migration-guide.md${NC}
   回滚指南: ${YELLOW}docs/mysql-rollback-guide.md${NC}

${GREEN}========================================${NC}

EOF
}

# 主函数
main() {
    echo -e "${GREEN}"
    cat << "EOF"
  ____  _             _            ____             _       
 |  _ \| | __ _ _   _(_)_ __      / ___| _ __  _ __(_)_ __  
 | |_) | |/ _` | | | | | '_ \_______\___ \| '_ \| '__| | '_ \ 
 |  __/| | (_| | |_| | | | | |_____|__) | |_) | |  | | | | |
 |_|   |_|\__,_|\__,_|_|_| |_|    |____/| .__/|_|  |_|_| |_|
                                        |_|                    
              SQLite 到 MySQL 8.0 迁移工具
EOF
    echo -e "${NC}"
    
    # 解析参数
    parse_args "$@"
    
    # 显示配置摘要
    if [ "$AUTO_CONFIRM" = true ]; then
        log_warn "运行模式: 自动确认（非交互）"
    else
        log_info "运行模式: 交互式"
    fi
    
    if [ "$OVERWRITE" = true ]; then
        log_warn "覆盖模式: 将覆盖MySQL中已有数据"
    fi
    
    if [ "$SKIP_BACKUP" = true ]; then
        log_warn "备份模式: 跳过备份（谨慎使用）"
    fi
    
    # 确认开始迁移
    if ! confirm "是否开始迁移？"; then
        log_info "迁移已取消"
        exit 0
    fi
    
    # 执行迁移流程
    check_python
    check_mysql
    check_sqlite
    create_backup_dir
    backup_sqlite
    backup_config
    install_dependencies
    configure_mysql
    run_migration
    validate_migration
    switch_to_mysql
    show_post_migration
    
    log_info "所有步骤已完成！"
}

# 捕获错误
error_handler() {
    local exit_code=$?
    local line_number=$1
    
    if [ $exit_code -ne 0 ]; then
        echo ""
        log_error "=========================================="
        log_error "脚本执行失败！"
        log_error "=========================================="
        log_error "退出代码: $exit_code"
        log_error "失败位置: 第 $line_number 行"
        log_error "=========================================="
        log_error "故障排查建议："
        log_error "  1. 查看上方的错误详情"
        log_error "  2. 检查MySQL服务状态: systemctl status mysql"
        log_error "  3. 检查MySQL连接参数"
        log_error "  4. 查看MySQL日志: tail -f /var/log/mysql/error.log"
        log_error "  5. 检查磁盘空间: df -h"
        log_error "=========================================="
    fi
}

trap 'error_handler $LINENO' ERR

# 运行主函数
main "$@"
