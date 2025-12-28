/**
 * 通用JavaScript工具函数
 */

// API基础URL（使用相对路径，自动指向当前Web服务）
// Web服务已集成API路由，直接使用/api路径
const API_BASE_URL = '/api';

// 认证相关常量
const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

// 全局加载模态框
let loadingModal = null;

// 全局确认对话框
let confirmModal = null;
let confirmCallback = null;
let cancelCallback = null;

// 页面加载完成后初始化
$(document).ready(function() {
    // 初始化加载模态框
    loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    
    // 初始化确认对话框
    confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    
    // 绑定确认按钮事件
    $('#confirm-ok-btn').on('click', function() {
        confirmModal.hide();
        if (confirmCallback) {
            confirmCallback();
            confirmCallback = null;
        }
    });
    
    // 绑定取消/关闭事件
    $('#confirmModal').on('hidden.bs.modal', function() {
        if (cancelCallback) {
            cancelCallback();
            cancelCallback = null;
        }
    });
    
    // 更新当前时间
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // 初始化工具提示
    initTooltips();
    
    // 检查认证状态
    checkAuth();
});

/**
 * 获取Token
 */
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

/**
 * 设置Token
 */
function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
    // 同时写入Cookie，有效期30天
    const d = new Date();
    d.setTime(d.getTime() + (30 * 24 * 60 * 60 * 1000));
    const expires = "expires=" + d.toUTCString();
    document.cookie = TOKEN_KEY + "=" + token + ";" + expires + ";path=/";
}

/**
 * 获取用户信息
 */
function getUser() {
    const userStr = localStorage.getItem(USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
}

/**
 * 设置用户信息
 */
function setUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * 清除认证信息
 */
function clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    // 清除Cookie
    document.cookie = TOKEN_KEY + "=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
}

/**
 * 检查认证状态
 */
function checkAuth() {
    const path = window.location.pathname;
    const publicPaths = ['/login', '/register'];
    
    // 如果是静态资源，跳过检查
    if (path.startsWith('/static/')) return;
    
    const token = getToken();
    
    if (!token && !publicPaths.includes(path)) {
        // 未登录且不在公开页面，跳转到登录页
        window.location.href = '/login';
    } else if (token && publicPaths.includes(path)) {
        // 已登录但在登录/注册页，跳转到首页
        window.location.href = '/';
    }
    
    // 更新UI上的用户信息
    updateUserUI();
}

/**
 * 更新UI上的用户信息
 */
function updateUserUI() {
    const user = getUser();
    if (user) {
        $('#user-name-display').text(user.username);
        $('#user-role-display').text(user.role === 'admin' ? '管理员' : '普通用户');
        
        // 控制管理员菜单显示
        if (user.role !== 'admin') {
            $('.admin-only').hide();
        } else {
            $('.admin-only').show();
        }
    }
}

/**
 * 注销
 */
function logout() {
    clearAuth();
    window.location.href = '/login';
}

/**
 * 更新当前时间显示
 */
function updateCurrentTime() {
    const now = new Date();
    const timeStr = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    $('#current-time').text(timeStr);
}

/**
 * 初始化Bootstrap工具提示
 */
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * 显示消息提示
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型 (success, danger, warning, info)
 * @param {number} duration - 显示时长（毫秒），0表示不自动关闭
 */
function showMessage(message, type = 'info', duration = 5000) {
    const alertId = 'alert-' + Date.now();
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${getIconForType(type)}"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    $('#message-container').append(alertHtml);
    
    // 自动关闭
    if (duration > 0) {
        setTimeout(function() {
            $(`#${alertId}`).alert('close');
        }, duration);
    }
}

/**
 * 根据消息类型获取图标
 */
function getIconForType(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

/**
 * 显示加载动画
 * @param {string} message - 加载提示消息
 * @param {boolean} showProgress - 是否显示进度条
 */
function showLoading(message = '正在处理，请稍候...', showProgress = false) {
    $('#loading-message').text(message);
    
    if (showProgress) {
        $('#loading-progress').show();
        updateProgress(0);
    } else {
        $('#loading-progress').hide();
    }
    
    loadingModal.show();
}

/**
 * 隐藏加载动画
 */
function hideLoading() {
    loadingModal.hide();
}

/**
 * 更新进度条
 * @param {number} percent - 进度百分比 (0-100)
 */
function updateProgress(percent) {
    const progressBar = $('#loading-progress .progress-bar');
    progressBar.css('width', percent + '%');
    progressBar.attr('aria-valuenow', percent);
    progressBar.text(percent + '%');
}

/**
 * 显示确认对话框
 * @param {string} message - 确认消息
 * @param {function} onConfirm - 确认回调函数
 * @param {function} onCancel - 取消回调函数
 */
function showConfirm(message, onConfirm, onCancel = null) {
    // 设置消息内容
    $('#confirm-message').text(message);
    
    // 保存回调函数
    confirmCallback = onConfirm;
    cancelCallback = onCancel;
    
    // 显示模态框
    confirmModal.show();
}

/**
 * API请求封装
 * @param {string} url - 请求URL
 * @param {string} method - 请求方法 (GET, POST, PUT, DELETE)
 * @param {object} data - 请求数据
 * @param {function} onSuccess - 成功回调
 * @param {function} onError - 失败回调
 */
function apiRequest(url, method = 'GET', data = null, onSuccess = null, onError = null) {
    const options = {
        url: API_BASE_URL + url,
        method: method,
        contentType: 'application/json',
        dataType: 'json',
        headers: {}
    };
    
    // 添加Token
    const token = getToken();
    if (token) {
        options.headers['Authorization'] = 'Bearer ' + token;
    }
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.data = JSON.stringify(data);
    }
    
    $.ajax(options)
        .done(function(response) {
            if (response.success || response.token) { // 兼容登录接口返回 token 而不是 success
                if (onSuccess) onSuccess(response);
            } else {
                const errorMsg = response.error || '操作失败';
                showMessage(errorMsg, 'danger');
                if (onError) onError(response);
            }
        })
        .fail(function(xhr, status, error) {
            // 处理 401 未授权
            if (xhr.status === 401) {
                clearAuth();
                window.location.href = '/login';
                return;
            }
            
            const errorMsg = xhr.responseJSON?.error || error || '网络请求失败';
            showMessage(errorMsg, 'danger');
            if (onError) onError(xhr);
        });
}

/**
 * 格式化日期时间为 YYYY-MM-DD HH:MM:SS 格式（北京时间）
 * @param {string} dateStr - 日期字符串（北京时间）
 * @param {boolean} includeTime - 是否包含时间
 */
function formatDateTime(dateStr, includeTime = true) {
    if (!dateStr) return '-';
    
    // 解析日期字符串
    const date = new Date(dateStr);
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
        return dateStr; // 如果解析失败，返回原字符串
    }
    
    // 使用本地时间格式化（北京时间）
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    if (includeTime) {
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    } else {
        return `${year}-${month}-${day}`;
    }
}

/**
 * 格式化数字
 * @param {number} num - 数字
 * @param {number} decimals - 小数位数
 */
function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined) return '-';
    return Number(num).toFixed(decimals);
}

/**
 * 格式化百分比
 * @param {number} num - 数字
 * @param {number} decimals - 小数位数
 */
function formatPercent(num, decimals = 2) {
    if (num === null || num === undefined) return '-';
    return formatNumber(num, decimals) + '%';
}

/**
 * 格式化涨跌幅（带颜色）
 * @param {number} pct - 涨跌幅
 */
function formatPctChange(pct) {
    if (pct === null || pct === undefined) return '-';
    
    const formatted = formatPercent(pct);
    const className = pct > 0 ? 'text-rise' : (pct < 0 ? 'text-fall' : '');
    const prefix = pct > 0 ? '+' : '';
    
    return `<span class="${className}">${prefix}${formatted}</span>`;
}

/**
 * 格式化大数字（万、亿）
 * @param {number} num - 数字
 */
function formatLargeNumber(num) {
    if (num === null || num === undefined) return '-';
    
    if (num >= 100000000) {
        return (num / 100000000).toFixed(2) + '亿';
    } else if (num >= 10000) {
        return (num / 10000).toFixed(2) + '万';
    } else {
        return num.toString();
    }
}

/**
 * 获取状态徽章HTML
 * @param {boolean} enabled - 是否启用
 */
function getStatusBadge(enabled) {
    if (enabled) {
        return '<span class="badge bg-success">启用</span>';
    } else {
        return '<span class="badge bg-secondary">禁用</span>';
    }
}

/**
 * 获取状态指示器HTML
 * @param {string} status - 状态 (success, warning, danger, info)
 */
function getStatusIndicator(status) {
    return `<span class="status-indicator status-${status}"></span>`;
}

/**
 * 防抖函数
 * @param {function} func - 要执行的函数
 * @param {number} wait - 等待时间（毫秒）
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 * @param {function} func - 要执行的函数
 * @param {number} limit - 时间限制（毫秒）
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * 复制文本到剪贴板
 * @param {string} text - 要复制的文本
 */
function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    
    try {
        document.execCommand('copy');
        showMessage('已复制到剪贴板', 'success', 2000);
    } catch (err) {
        showMessage('复制失败', 'danger');
    }
    
    document.body.removeChild(textarea);
}

/**
 * 下载文件
 * @param {string} url - 文件URL
 * @param {string} filename - 文件名
 */
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * 导出表格为CSV
 * @param {string} tableId - 表格ID
 * @param {string} filename - 文件名
 */
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    for (let row of rows) {
        const cols = row.querySelectorAll('td, th');
        const csvRow = [];
        
        for (let col of cols) {
            csvRow.push('"' + col.innerText.replace(/"/g, '""') + '"');
        }
        
        csv.push(csvRow.join(','));
    }
    
    const csvContent = csv.join('\n');
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    downloadFile(url, filename);
    URL.revokeObjectURL(url);
}

/**
 * 刷新页面数据
 */
function refreshPage() {
    location.reload();
}

/**
 * 返回上一页
 */
function goBack() {
    window.history.back();
}
