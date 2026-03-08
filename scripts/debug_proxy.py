import os
import subprocess
import time
import sqlite3
import sys

def run():
    print(">>> 正在清理旧代理进程...")
    subprocess.run("pkill -9 -f mitmdump", shell=True)
    
    print(">>> 正在建立 ADB 端口反向代理 (8080)...")
    subprocess.run("adb reverse tcp:8080 tcp:8080", shell=True)
    
    print(">>> 正在启动 mitmproxy (带详细输出)...")
    # 增加 PYTHONPATH 并启动 mitmdump
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + ":."
    
    with open("data/logs/mitm_debug.log", "w") as f:
        p = subprocess.Popen(
            ["mitmdump", "-p", "8080", "-s", "src/proxy/addon.py"],
            env=env,
            stdout=f,
            stderr=f
        )
    
    print(">>> 代理已在后台运行。日志: data/logs/mitm_debug.log")
    print(">>> 请在手机上手动刷新小红书首页，或进行搜索操作...")
    
    db_path = "data/xiaohongshu.db"
    last_count = 0
    
    try:
        while True:
            time.sleep(2)
            if not os.path.exists(db_path):
                continue
            
            conn = sqlite3.connect(db_path)
            count = conn.execute("SELECT count(*) FROM notes").fetchone()[0]
            conn.close()
            
            if count > last_count:
                print(f"[{time.strftime('%H:%M:%S')}] 🎉 抓取到新数据！当前数据库总笔记数: {count}")
                # 显示最新一条
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT author_name, title, source FROM notes ORDER BY updated_at DESC LIMIT 1").fetchone()
                if row:
                    print(f"  - [{row['source']}] {row['author_name']}: {row['title'][:30]}...")
                conn.close()
                last_count = count
            
            # 检查后台进程
            if p.poll() is not None:
                print("❌ mitmdump 进程已退出，请检查日志！")
                break
                
    except KeyboardInterrupt:
        print("
>>> 停止监控。")
        p.terminate()

if __name__ == "__main__":
    run()
