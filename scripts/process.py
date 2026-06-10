#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 配置 ====================
TOP_SPEED_COUNT = int(os.environ.get('TOP_SPEED_COUNT', '10'))
SPEED_TIMEOUT = 8
SPEED_WORKERS = 15
# =============================================

# 拼音缩写到中文的映射表
PINYIN_TO_CHINESE = {
    'ahws': '安徽卫视', 'ahws_hd': '安徽卫视',
    'bjws': '北京卫视', 'bjws_hd': '北京卫视',
    'cetv2': 'CETV2',
    'hljws': '黑龙江卫视', 'hljws_hd': '黑龙江卫视',
    'hebws': '河北卫视', 'hebws_hd': '河北卫视',
    'henws': '河南卫视', 'henws_hd': '河南卫视',
    'hnws': '湖南卫视', 'hnws_hd': '湖南卫视',
    'dfws': '东方卫视', 'dfws_hd': '东方卫视',
    'jsws': '江苏卫视', 'jsws_hd': '江苏卫视',
    'zjws': '浙江卫视', 'zjws_hd': '浙江卫视',
    'gdws': '广东卫视', 'gdws_hd': '广东卫视',
    'szws': '深圳卫视', 'szws_hd': '深圳卫视',
    'sdws': '山东卫视', 'sdws_hd': '山东卫视',
    'hbws': '湖北卫视', 'hbws_hd': '湖北卫视',
    'jlws': '吉林卫视', 'jlws_hd': '吉林卫视',
    'jxws': '江西卫视', 'jxws_hd': '江西卫视',
    'lnws': '辽宁卫视', 'lnws_hd': '辽宁卫视',
    'nxws': '宁夏卫视', 'nxws_hd': '宁夏卫视',
    'qhws': '青海卫视', 'qhws_hd': '青海卫视',
    'scws': '四川卫视', 'scws_hd': '四川卫视',
    'sxws': '山西卫视', 'sxws_hd': '山西卫视',
    'shxws': '陕西卫视', 'shxws_hd': '陕西卫视',
    'tjws': '天津卫视', 'tjws_hd': '天津卫视',
    'ynws': '云南卫视', 'ynws_hd': '云南卫视',
    'gxws': '广西卫视', 'gxws_hd': '广西卫视',
    'gzws': '贵州卫视', 'gzws_hd': '贵州卫视',
    'gsgs': '甘肃卫视', 'gsgs_hd': '甘肃卫视',
    'xjws': '新疆卫视', 'xjws_hd': '新疆卫视',
    'xzws': '西藏卫视', 'xzws_hd': '西藏卫视',
    'nmws': '内蒙古卫视', 'nmws_hd': '内蒙古卫视',
    'cqws': '重庆卫视', 'cqws_hd': '重庆卫视',
    'fjws': '东南卫视', 'fjws_hd': '东南卫视',
}

def extract_cctv_number(name):
    """提取CCTV后面的数字，用于排序"""
    match = re.search(r'CCTV(\d+)', name)
    if match:
        return int(match.group(1))
    return 999

def normalize_name(name):
    """统一频道名称"""
    name_lower = name.lower().strip()
    name_original = name
    
    if name_lower in PINYIN_TO_CHINESE:
        return PINYIN_TO_CHINESE[name_lower]
    
    # 央视匹配（使用单词边界）
    if re.search(r'\bcctv[-\s]*1\b|中央[一1]台|中央[一1]套', name_lower):
        return 'CCTV1'
    if re.search(r'\bcctv[-\s]*2\b|中央[二2]台|中央[二2]套', name_lower):
        return 'CCTV2'
    if re.search(r'\bcctv[-\s]*3\b|中央[三3]台|中央[三3]套', name_lower):
        return 'CCTV3'
    if re.search(r'\bcctv[-\s]*4\b|中央[四4]台|中央[四4]套', name_lower):
        return 'CCTV4'
    if re.search(r'\bcctv[-\s]*5\+', name_lower):
        return 'CCTV5+'
    if re.search(r'\bcctv[-\s]*5\b|中央[五5]台|中央[五5]套', name_lower):
        return 'CCTV5'
    if re.search(r'\bcctv[-\s]*6\b|中央[六6]台|中央[六6]套', name_lower):
        return 'CCTV6'
    if re.search(r'\bcctv[-\s]*7\b|中央[七7]台|中央[七7]套', name_lower):
        return 'CCTV7'
    if re.search(r'\bcctv[-\s]*8\b|中央[八8]台|中央[八8]套', name_lower):
        return 'CCTV8'
    if re.search(r'\bcctv[-\s]*9\b|中央[九9]台|中央[九9]套', name_lower):
        return 'CCTV9'
    if re.search(r'\bcctv[-\s]*10\b|中央[十10]台|中央[十10]套', name_lower):
        return 'CCTV10'
    if re.search(r'\bcctv[-\s]*11\b|中央十一', name_lower):
        return 'CCTV11'
    if re.search(r'\bcctv[-\s]*12\b|中央十二', name_lower):
        return 'CCTV12'
    if re.search(r'\bcctv[-\s]*13\b|中央十三', name_lower):
        return 'CCTV13'
    if re.search(r'\bcctv[-\s]*14\b|中央十四', name_lower):
        return 'CCTV14'
    if re.search(r'\bcctv[-\s]*15\b|中央十五', name_lower):
        return 'CCTV15'
    if re.search(r'\bcctv[-\s]*16\b|中央十六', name_lower):
        return 'CCTV16'
    if re.search(r'\bcctv[-\s]*17\b|中央十七', name_lower):
        return 'CCTV17'
    if re.search(r'\bcgtn', name_lower):
        return 'CGTN'
    
    # 重庆卫视
    if re.search(r'\bcqws\b|重庆', name_lower):
        return '重庆卫视'
    
    # 去掉后缀
    result = re.sub(r'[_ ]?hd$|高清|超清|标清|4k|测试|备用|_hd', '', name_original, flags=re.IGNORECASE)
    return result.strip()

def test_speed(url, timeout=SPEED_TIMEOUT):
    """使用 ffmpeg 测试流媒体速度"""
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix='.ts') as temp_file:
            cmd = [
                'ffmpeg', '-y',
                '-timeout', str(timeout * 1000000),
                '-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '-i', url,
                '-t', str(timeout),
                '-c', 'copy',
                '-f', 'mpegts',
                temp_file.name
            ]
            start_time = time.time()
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            try:
                process.communicate(timeout=timeout + 2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
            end_time = time.time()
            duration = end_time - start_time
            
            try:
                file_size = os.path.getsize(temp_file.name)
                if file_size > 10240 and duration > 0.1:
                    speed_mbps = (file_size / duration) / (1024 * 1024)
                    return round(speed_mbps, 2)
            except:
                pass
    except:
        pass
    return 0.0

def main():
    print("=" * 60)
    print("IPTV 直播源处理工具")
    print(f"每个频道保留最快的前 {TOP_SPEED_COUNT if TOP_SPEED_COUNT < 999 else '全部'} 个源")
    print("=" * 60)
    
    # 读取所有源文件
    all_urls = []
    source_count = 0
    for i in range(1, 5):  # 支持 source1.txt 到 source4.txt
        filename = f'source{i}.txt'
        if not os.path.exists(filename):
            continue
        source_count += 1
        print(f"读取源文件: {filename}")
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.endswith('#genre#'):
                    continue
                if ',' not in line:
                    continue
                parts = line.split(',', 1)
                raw_name = parts[0].strip()
                url = parts[1].strip()
                if not url.startswith('http'):
                    continue
                norm_name = normalize_name(raw_name)
                all_urls.append((norm_name, url))
    
    print(f"共收集 {len(all_urls)} 个频道源")
    
    # 去重
    unique_urls = {}
    for name, url in all_urls:
        key = f"{name}|{url}"
        if key not in unique_urls:
            unique_urls[key] = (name, url)
    
    unique_list = list(unique_urls.values())
    print(f"去重后 {len(unique_list)} 个频道源")
    
    # 测速
    print(f"\n开始测速...")
    speed_results = []
    
    with ThreadPoolExecutor(max_workers=SPEED_WORKERS) as executor:
        futures = {executor.submit(test_speed, url): (name, url) for name, url in unique_list}
        completed = 0
        for future in as_completed(futures):
            name, url = futures[future]
            speed = future.result()
            speed_results.append((name, url, speed))
            completed += 1
            status = f"{speed:.2f} MB/s" if speed > 0 else "失败"
            print(f"[{completed}/{len(unique_list)}] {name}: {status}")
    
    # 按频道分组排序
    channel_groups = {}
    for name, url, speed in speed_results:
        if name not in channel_groups:
            channel_groups[name] = []
        channel_groups[name].append((url, speed))
    
    final_channels = []
    for name, urls in channel_groups.items():
        urls.sort(key=lambda x: x[1], reverse=True)
        keep_count = TOP_SPEED_COUNT if TOP_SPEED_COUNT < 999 else len(urls)
        for url, speed in urls[:keep_count]:
            final_channels.append((name, url, speed))
    
    print(f"每个频道保留最快源后，共 {len(final_channels)} 个频道源")
    
    # 分类
    def classify_channel(name):
        if re.search(r'^CCTV|^CGTN', name):
            return "央视频道"
        if name.endswith('卫视'):
            return "卫视频道"
        return "其他频道"
    
    grouped = {"央视频道": [], "卫视频道": [], "其他频道": []}
    for name, url, speed in final_channels:
        category = classify_channel(name)
        grouped[category].append((name, url, speed))
    
    # 排序
    grouped["央视频道"].sort(key=lambda x: extract_cctv_number(x[0]))
    grouped["卫视频道"].sort(key=lambda x: x[0])
    grouped["其他频道"].sort(key=lambda x: x[0])
    
    # 生成 TXT 文件
    with open('iptv.txt', 'w', encoding='utf-8') as f:
        for category in ["央视频道", "卫视频道", "其他频道"]:
            channels = grouped[category]
            if not channels:
                continue
            f.write(f"{category},#genre#\n")
            for name, url, speed in channels:
                if speed > 0:
                    f.write(f"{name} [{speed:.1f}MB/s],{url}\n")
                else:
                    f.write(f"{name},{url}\n")
            f.write("\n")
    
    # 生成 M3U 文件
    with open('iptv.m3u', 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for category in ["央视频道", "卫视频道", "其他频道"]:
            channels = grouped[category]
            for name, url, speed in channels:
                if speed > 0:
                    f.write(f'#EXTINF:-1 group-title="{category}",{name} [{speed:.1f}MB/s]\n')
                else:
                    f.write(f'#EXTINF:-1 group-title="{category}",{name}\n')
                f.write(f'{url}\n')
    
    print("=" * 60)
    print("文件已生成: iptv.txt 和 iptv.m3u")
    for category, channels in grouped.items():
        if channels:
            print(f"{category}: {len(channels)} 个频道源")
    print("=" * 60)

if __name__ == "__main__":
    main()