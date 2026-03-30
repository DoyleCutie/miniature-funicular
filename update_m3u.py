import requests
import re
import os
from collections import OrderedDict

# === 配置区 ===
SOURCE_URL = "https://t.freetv.fun/m3u/playlist_original.txt"
# 确保这个链接能读到你仓库里已有的 2b.m3u，实现增量合并
MY_M3U_URL = "https://raw.githubusercontent.com/DoyleCutie/miniature-funicular/main/2b.m3u"
OUTPUT_FILE = "2b.m3u"

# 关键词过滤：只抓包含这些词的 [BD] 源
# 如果想全抓，可以把列表清空：WHITE_LIST = []
WHITE_LIST = ['CCTV', '卫视', '金鹰', '卡通', '动画', '体育', '电影']

def check_link(url):
    """测试连接性"""
    try:
        # 增加 headers 模拟浏览器，防止被屏蔽
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        with requests.get(url, timeout=3, stream=True, verify=False, headers=headers) as r:
            return r.status_code == 200
    except:
        return False

def get_remote_bd_sources():
    """抓取远程 [BD] 源"""
    bd_map = {}
    try:
        print(f">> 正在请求源地址: {SOURCE_URL}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(SOURCE_URL, timeout=15, headers=headers)
        resp.encoding = 'utf-8'
        lines = resp.text.splitlines()

        for line in lines:
            line = line.strip()
            # 逻辑：必须包含 [BD] 且包含 http
            if "[BD]" in line and "http" in line:
                # 针对 [BD]名字,链接 格式切割
                if "," in line:
                    parts = line.split(",", 1)
                    raw_name = parts[0].strip()
                    url = parts[1].strip()
                else:
                    # 兼容没有逗号的情况
                    url_match = re.search(r'https?://[^\s]+', line)
                    if url_match:
                        url = url_match.group().strip()
                        raw_name = line.split("http")[0].strip()
                    else: continue

                # 提取干净的频道名（去掉 [BD] 标签）
                clean_name = raw_name.replace("[BD]", "").strip()

                # 关键词过滤逻辑
                # 如果 WHITE_LIST 为空则全抓，否则只抓包含关键词的
                is_match = False
                if not WHITE_LIST:
                    is_match = True
                else:
                    if any(kw.upper() in clean_name.upper() for kw in WHITE_LIST):
                        is_match = True

                if is_match:
                    print(f"   发现目标: {clean_name}，正在测试连接...")
                    if check_link(url):
                        bd_map[clean_name] = url
                        print(f"   ✅ [有效] {clean_name}")
                    else:
                        print(f"   ❌ [失效] {clean_name}")
        return bd_map
    except Exception as e:
        print(f"爬取失败: {e}")
        return {}

def update_m3u():
    """合并远程 BD 源到本地库"""
    new_bd = get_remote_bd_sources()
    if not new_bd:
        print("❌ 远程未抓取到任何有效 [BD] 源，停止更新。")
        return

    # 1. 尝试读取旧库（实现多线路合并）
    channels_data = OrderedDict()
    try:
        resp = requests.get(MY_M3U_URL, timeout=10)
        if resp.status_code == 200:
            lines = resp.text.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith("#EXTINF"):
                    # 提取频道名
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
    except:
        print(">> 未发现旧库，将创建新库")

    # 2. 将新抓到的 BD 源插入到对应频道的第一位（首选线路）
    for name, bd_url in new_bd.items():
        if name in channels_data:
            if bd_url not in channels_data[name]["urls"]:
                channels_data[name]["urls"].insert(0, bd_url)
        else:
            # 自动分类
            group = "高清频道"
            if "卫视" in name: group = "地方卫视"
            elif "CCTV" in name.upper(): group = "央视频道"
            
            channels_data[name] = {
                "info": f'#EXTINF:-1 group-title="{group}" tvg-id="{name}",{name}',
                "urls": [bd_url]
            }

    # 3. 生成最终文件
    final_output = ["#EXTM3U"]
    for name, data in channels_data.items():
        for url in data["urls"]:
            final_output.append(data["info"])
            final_output.append(url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_output))
    print(f"✅ 更新完成，当前库内共 {len(channels_data)} 个频道。")

if __name__ == "__main__":
    # 忽略 SSL 警告
    requests.packages.urllib3.disable_warnings()
    update_m3u()
