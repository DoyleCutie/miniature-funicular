import requests
import re
import sys
from collections import OrderedDict

# === 配置区 ===
SOURCE_URL = "https://t.freetv.fun/m3u/playlist_original.txt"
# 自动获取你的 GitHub Raw 链接，确保合并时能读到旧数据
MY_M3U_URL = "https://raw.githubusercontent.com/DoyleCutie/miniature-funicular/main/2b.m3u"
OUTPUT_FILE = "2b.m3u"

# 白名单：只爬取包含这些关键词的 [BD] 源
WHITE_LIST_PATTERN = r'CCTV|卫视|金鹰|卡通|动画|体育|电影'

# 自动分类映射
AUTO_GROUPS = {
    "CCTV": "央视频道",
    "卫视": "地方频道",
    "卡通": "少儿频道",
    "动画": "少儿频道",
    "体育": "体育竞技",
    "电影": "影院经典"
}

def check_link(url):
    """测试连接性"""
    try:
        # 兼容 .php 和 .m3u8 的请求测试
        with requests.get(url, timeout=3, stream=True, verify=False) as r:
            return r.status_code == 200
    except:
        return False

def get_remote_bd_sources():
    """抓取远程源 (支持 [BD]名字,链接 格式)"""
    bd_map = {}
    try:
        print(">> 正在爬取远程 [BD] 源...")
        resp = requests.get(SOURCE_URL, timeout=10)
        resp.encoding = 'utf-8'
        
        lines = resp.text.splitlines()
        for line in lines:
            line = line.strip()
            # 修正匹配逻辑：只要包含 [BD] 且有逗号，且后缀符合要求
            if "[BD]" in line and "," in line:
                if any(ext in line for ext in [".m3u8", ".php", ".m3u8?", ".php?"]):
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        name = parts[0].replace("[BD]", "").strip()
                        url = parts[1].strip()
                        
                        if re.search(WHITE_LIST_PATTERN, name, re.IGNORECASE):
                            if check_link(url):
                                bd_map[name] = url
        return bd_map
    except Exception as e:
        print(f"爬取失败: {e}")
        return {}

def update_m3u():
    """核心：同名多线路更新"""
    new_bd = get_remote_bd_sources()

    try:
        print(f">> 正在读取你的库并合并分类...")
        try:
            resp = requests.get(MY_M3U_URL, timeout=10)
            resp.encoding = 'utf-8'
            lines = resp.text.splitlines() if resp.status_code == 200 else []
        except:
            lines = []

        channels_data = OrderedDict()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("#EXTINF"):
                name_match = re.search(r'tvg-id="(.*?)"', line) or re.search(r',(.*)$', line)
                if name_match and i + 1 < len(lines):
                    name = name_match.group(1).strip()
                    url = lines[i+1].strip()
                    if name not in channels_data:
                        channels_data[name] = {"info": line, "urls": []}
                    if url not in channels_data[name]["urls"]:
                        channels_data[name]["urls"].append(url)
                    i += 2
                    continue
            i += 1

        # 插入新爬到的高清线路
        for name, bd_url in new_bd.items():
            if name in channels_data:
                if bd_url not in channels_data[name]["urls"]:
                    channels_data[name]["urls"].insert(0, bd_url) # 插在第一位
                    print(f"   [线路升级] {name} 插入高清源")
            else:
                group = "其他频道"
                for kw, g in AUTO_GROUPS.items():
                    if kw in name: group = g; break
                channels_data[name] = {
                    "info": f'#EXTINF:-1 group-title="{group}" tvg-id="{name}",{name}',
                    "urls": [bd_url]
                }
                print(f"   [新增频道] {name} 归类至 {group}")

        # 生成文件
        final_output = ["#EXTM3U"]
        for name, data in channels_data.items():
            for url in data["urls"]:
                final_output.append(data["info"])
                final_output.append(url)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(final_output))
        print(f"\n✅ 成功更新！同名频道已合并。")

    except Exception as e:
        print(f"合并出错: {e}")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    update_m3u()
