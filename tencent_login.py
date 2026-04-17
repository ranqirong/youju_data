#!/usr/bin/env python3
"""腾讯云控制台自动登录并配置安全组"""
import asyncio
from playwright.async_api import async_playwright

# 登录信息
EMAIL = "tengxunyun@youjugroup.cn"
PASSWORD = "Yjjt123456@"
TOTP_SECRET = "ApplePasswords-fb0"  # 通行密钥

async def login_tencent():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-gpu']
        )
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})
        
        print("打开腾讯云登录页...")
        await page.goto("https://cloud.tencent.com/login")
        await asyncio.sleep(3)
        
        # 截图看当前状态
        await page.screenshot(path='/root/.openclaw/tencent_login_1.png')
        print("已截图: /root/.openclaw/tencent_login_1.png")
        
        # 找密码登录入口
        try:
            # 点击子用户/协作者登录
            subuser_tab = await page.query_selector('text=子用户/协作者')
            if subuser_tab:
                await subuser_tab.click()
                await asyncio.sleep(1)
            
            # 输入邮箱
            email_input = await page.query_selector('input[placeholder*="邮箱"], input[type="email"], input[name="email"]')
            if not email_input:
                # 尝试其他选择器
                email_input = await page.query_selector('input[placeholder*="账号"], input[placeholder*="用户名"]')
            
            if email_input:
                await email_input.fill(EMAIL)
                print(f"输入邮箱: {EMAIL}")
            
            # 输入密码
            pwd_input = await page.query_selector('input[type="password"]')
            if pwd_input:
                await pwd_input.fill(PASSWORD)
                print("输入密码")
            
            await asyncio.sleep(2)
            await page.screenshot(path='/root/.openclaw/tencent_login_2.png')
            
            # 点击登录
            login_btn = await page.query_selector('button:has-text("登 录"), button:has-text("登录"), .login-btn')
            if login_btn:
                await login_btn.click()
                print("点击登录")
            
            await asyncio.sleep(5)
            await page.screenshot(path='/root/.openclaw/tencent_login_3.png')
            print("登录后截图完成")
            
            # 可能需要二次验证
            # TODO: 生成 TOTP 码并输入
            
        except Exception as e:
            print(f"错误: {e}")
            await page.screenshot(path='/root/.openclaw/tencent_error.png')
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(login_tencent())
