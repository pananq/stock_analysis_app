import sys
import os
import argparse
import getpass

# 添加项目根目录到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_service import AuthService
from app.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description='管理员账户管理工具')
    parser.add_argument('action', choices=['reset-password'], help='操作类型')
    parser.add_argument('--password', help='新密码（如果不提供则交互式输入）')
    
    args = parser.parse_args()
    
    if args.action == 'reset-password':
        password = args.password
        if not password:
            try:
                password = getpass.getpass("请输入新管理员密码: ")
                confirm = getpass.getpass("请再次输入密码: ")
                if password != confirm:
                    print("两次输入的密码不一致")
                    return
            except KeyboardInterrupt:
                print("\n操作已取消")
                return
        
        if len(password) < 6:
            print("密码长度至少需要6位")
            return
            
        auth_service = AuthService()
        if auth_service.reset_admin_password(password):
            print("管理员密码重置成功")
        else:
            print("管理员密码重置失败")

if __name__ == '__main__':
    main()
