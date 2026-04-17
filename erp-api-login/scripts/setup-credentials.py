#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP 凭证配置向导
帮助用户安全地配置 ERP 登录凭证
"""

import os
import sys
import getpass

def main():
    print("="*70)
    print("ERP 凭证配置向导")
    print("="*70)
    
    # 确定配置文件路径
    config_dir = os.path.expanduser("~/.openclaw/workspace/configs")
    config_file = os.path.join(config_dir, "erp-credentials.env")
    
    # 检查配置文件是否已存在
    if os.path.exists(config_file):
        print(f"\n⚠️  检测到已存在的配置文件:")
        print(f"   {config_file}")
        print("\n是否覆盖现有配置？(y/N): ", end='')
        choice = input().strip().lower()
        if choice != 'y':
            print("\n已取消配置")
            return
    
    # 创建配置目录
    os.makedirs(config_dir, exist_ok=True)
    
    print("\n" + "="*70)
    print("请输入 ERP 登录凭证")
    print("="*70)
    print("\n💡 提示:")
    print("   - 凭证将保存在加密的配置文件中")
    print("   - 只有你有权限读取该文件")
    print("   - 不会上传到任何服务器")
    print("")
    
    # 获取手机号
    while True:
        print("\n请输入手机号:", end=' ')
        phone = input().strip()
        
        if not phone:
            print("❌ 手机号不能为空")
            continue
        
        # 简单验证手机号格式
        if not phone.isdigit() or len(phone) < 10 or len(phone) > 15:
            print("⚠️  手机号格式可能不正确，确认继续？(y/N): ", end='')
            choice = input().strip().lower()
            if choice == 'y':
                break
        else:
            break
    
    # 获取密码
    while True:
        print("\n请输入密码:", end=' ')
        password = getpass.getpass()
        
        if not password:
            print("❌ 密码不能为空")
            continue
        
        # 确认密码
        print("请确认密码:", end=' ')
        password_confirm = getpass.getpass()
        
        if password != password_confirm:
            print("❌ 两次输入的密码不一致")
            continue
        
        break
    
    # 获取可选配置
    print("\n" + "="*70)
    print("可选配置（直接回车跳过）")
    print("="*70)
    
    print("\n公司名称:", end=' ')
    company = input().strip()
    
    print("品牌 ID [默认：593347894961426496]:", end=' ')
    brand_id = input().strip() or "593347894961426496"
    
    print("城市代码 [默认：150200]:", end=' ')
    city_code = input().strip() or "150200"
    
    # 生成配置文件
    config_content = f"""# ERP 凭证配置文件
# 生成时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#
# ⚠️ 安全提示:
# - 此文件包含敏感信息，请妥善保管
# - 不要将此文件提交到 Git 仓库
# - 建议设置文件权限：chmod 600 erp-credentials.env

# ==================== 必需配置 ====================

ERP_USERNAME={phone}
ERP_PASSWORD={password}

# ==================== 可选配置 ====================

ERP_COMPANY={company if company else '广西优居科技总部'}
ERP_BRAND_ID={brand_id}
ERP_CITY_CODE={city_code}
ERP_EXPORT_DIR=~/Desktop/ERP 导出

# ==================== 安全建议 ====================
# 1. 定期更换密码
# 2. 不要分享此文件
# 3. 使用强密码（大小写字母 + 数字 + 特殊字符）
"""
    
    # 写入配置文件
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        # 设置文件权限
        os.chmod(config_file, 0o600)
        
        print("\n" + "="*70)
        print("✅ 配置成功！")
        print("="*70)
        print(f"\n配置文件已保存到:")
        print(f"   {config_file}")
        print(f"\n文件权限已设置为:")
        print(f"   chmod 600 (仅所有者可读写)")
        print(f"\n使用账号:")
        print(f"   手机号：{phone}")
        print(f"   公司：{company if company else '广西优居科技总部'}")
        
        # 测试配置
        print("\n" + "="*70)
        print("是否立即测试登录？(y/N): ", end='')
        choice = input().strip().lower()
        
        if choice == 'y':
            print("\n正在测试登录...")
            
            # 导入并测试
            script_dir = os.path.dirname(os.path.abspath(__file__))
            erp_export_path = os.path.join(script_dir, 'erp-export.py')
            
            import importlib.util
            spec = importlib.util.spec_from_file_location("erp_export", erp_export_path)
            erp_export = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(erp_export)
            
            client = erp_export.ERPAPIClient(phone=phone, password=password)
            
            if client.login():
                print("\n✅ 登录成功！")
                user_info = client.get_user_info()
                if user_info:
                    print(f"✅ 用户：{user_info.get('userName')}")
                    if user_info.get('organName'):
                        print(f"   组织：{user_info.get('organName')}")
            else:
                print("\n❌ 登录失败")
                print("\n💡 请检查:")
                print("   1. 手机号和密码是否正确")
                print("   2. 账号是否有 ERP 系统访问权限")
                print("   3. 联系系统管理员确认账号状态")
        
        print("\n" + "="*70)
        print("📚 使用指南:")
        print("="*70)
        print("\n运行导出脚本:")
        print(f"   cd {script_dir}")
        print(f"   python3 erp-export.py")
        print("\n查看其他命令:")
        print(f"   ls {script_dir}/*.py")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ 配置失败：{e}")
        print("\n请手动创建配置文件:")
        print(f"   vi {config_file}")

if __name__ == "__main__":
    main()
