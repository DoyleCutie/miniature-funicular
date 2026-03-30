import requests
import re
import os
from collections import OrderedDict

# === 配置区 ===
SOURCE_URL = "https://t.freetv.fun/m3u/playlist_original.txt"
MY_M3U_URL = "https://raw.githubusercontent.com/DoyleCutie/miniature-funicular/main/2b.m3u"
OUTPUT_FILE = "2b.m3u"

# 关键词列表（确保包含你给的例子里的频道）
WHITE_LIST = ['CCTV', '卫视', '金鹰', '卡通', '动画', '体育', '电影']

def get_remote_bd_sources():
    """强力抓取逻辑"""
    bd_map = {}
    try:
        print(f">> 正在请求源地址: {SOURCE_URL}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(SOURCE_URL, timeout=15, headers=headers)
        resp.encoding = 'utf-8'
        lines = resp.text.splitlines()

        for line in lines:
            line = line.strip()
            # 只找带 [BD] 且带 http 的行
            if "[BD]" in line and "http" in line:
                if "," in line:
                    parts = line.split(",", 1)
                    raw_name = parts[0].strip()
                    url = parts[1].strip()
                    clean_name = raw_name.replace("[BD]", "").strip()
                    
                    # 匹配关键词
                    if any(kw.upper() in clean_name.upper() for kw in WHITE_LIST):
                        # --- 核心修改：不再调用 check_link，直接记录 ---
                        bd_map[clean_name] = url
                        print(f"   找到源: {clean_name}")
        return bd_map
    except Exception as e:
        print(f"爬取出错: {e}")
        return {}

def update_m3u():
    new_bd = get_remote_bd_sources()
    if not new_bd:
        print("❌ 远程未抓取到任何源，脚本退出。")
        return

    # 尝试读取旧文件进行合并
    channels_data = OrderedDict()
    try:
        resp = requests.get(MY_M3U_URL, timeout=10)
        if resp.status_code == 200:
            lines = resp.text.splitlines()
            i = 0
            while i < len(lines):
                if lines[i].startswith("#EXTINF") and i + 1 < len(lines):
                    name_match = re.search(r'tvg-id="(.*?)"', lines[i]) or re.search(r',(.*)$', lines[i])
                    if name_match:
                        name = name_match.group(1).strip()
                        url = lines[i+1].strip()
                        if name not in channels_data:
                            channels_data[name] = {"info": lines[i], "urls": []}
                        if url not in channels_data[name]["urls"]:
                            channels_data[name]["urls"].append(url)
                    i += 2
                else: i += 1
    except: pass

    # 合并新源
    for name, bd_url in new_bd.items():
        if name in channels_data:
            if bd_url not in channels_data[name]["urls"]:
                channels_data[name]["urls"].insert(0, bd_url)
        else:
            group = "地方卫视" if "卫视" in name else "央视频道" if "CCTV" in name.upper() else "高清频道"
            channels_data[name] = {
                "info": f'#EXTINF:-1 group-title="{group}" tvg-id="{name}",{name}',
                "urls": [bd_url]
            }

    # 写入文件
    final_output = ["#EXTM3U"]
    for name, data in channels_data.items():
        for url in data["urls"]:
            final_output.append(data["info"])
            final_output.append(url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_output))
    print(f"✅ 更新成功！准备提交到仓库。")

if __name__ == "__main__":
    update_m3u()
