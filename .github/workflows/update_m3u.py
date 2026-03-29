import requests
import re
import sys
from collections import OrderedDict

# === 配置区 ===
SOURCE_URL = "https://t.freetv.fun/m3u/playlist_original.txt"
MY_M3U_URL = "https://raw.githubusercontent.com/DoyleCutie/miniature-funicular/main/2b.m3u"
OUTPUT_FILE = "2b.m3u"

# 白名单：只爬取包含这些关键词的 [BD] 源
WHITE_LIST_PATTERN = r'CCTV|卫视|金鹰|卡通|动画|体育|电影'

# 自动分类映射（仅针对新发现的频道）
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
        with requests.get(url, timeout=3, stream=True, verify=False) as r:
            return r.status_code == 200
    except:
        return False

def get_remote_bd_sources():
    """抓取远程源"""
    bd_map = {}
    try:
        print(">> 正在爬取远程 [BD] 源...")
        resp = requests.get(SOURCE_URL, timeout=10)
        resp.encoding = 'utf-8'
        pattern = r'#EXTINF:.*?,\[BD\](.*?)\n(http.*?\.m3u8)'
        matches = re.findall(pattern, resp.text)
        for name, url in matches:
            name = name.strip()
            if re.search(WHITE_LIST_PATTERN, name, re.IGNORECASE):
                if check_link(url):
                    bd_map[name] = url.strip()
        return bd_map
    except Exception as e:
        print(f"爬取失败: {e}")
        return {}

def update_m3u():
    """核心：同名多线路更新"""
    new_bd = get_remote_bd_sources()
    
    try:
        print(f">> 正在读取你的库并合并分类...")
        resp = requests.get(MY_M3U_URL, timeout=10)
        resp.encoding = 'utf-8'
        lines = resp.text.splitlines()
        
        # 结构：{ "频道名": { "info": "#EXTINF行", "urls": [线路1, 线路2...] } }
        channels_data = OrderedDict()
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("#EXTINF"):
                # 提取频道名（优先匹配 tvg-id，其次是逗号后的名字）
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

        # 逻辑：如果爬到了 [BD] 源，将其插入到对应频道的第一个位置（线路 1）
        for name, bd_url in new_bd.items():
            if name in channels_data:
                if bd_url not in channels_data[name]["urls"]:
                    channels_data[name]["urls"].insert(0, bd_url)
                    print(f"   [线路升级] {name} 插入高清源作为首选")
            else:
                # 库里没有的新频道，根据关键词自动分类
                group = "其他频道"
                for kw, g in AUTO_GROUPS.items():
                    if kw in name: group = g; break
                channels_data[name] = {
                    "info": f'#EXTINF:-1 group-title="{group}" tvg-id="{name}",{name}',
                    "urls": [bd_url]
                }
                print(f"   [新增频道] {name} 已归类至 {group}")

        # 生成最终文件内容
        final_output = ["#EXTM3U"]
        for name, data in channels_data.items():
            for url in data["urls"]:
                final_output.append(data["info"])
                final_output.append(url)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(final_output))
        print(f"\n✅ 成功更新！同名频道已合并，高清源已排在第一位。")

    except Exception as e:
        print(f"合并出错: {e}")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    update_m3u()