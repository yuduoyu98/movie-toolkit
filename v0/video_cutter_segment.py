import configparser
import os
import re


def video_cut(source_file_path: str, start: str, end: str, segment_no: int, copy: bool = False):
    print(f'源文件：{source_file_path}')
    print(f'截取时间范围：{start} ~ {end}')

    cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}" -codec copy -avoid_negative_ts 1 "tmp\\concat\\{segment_no}.mp4"'
    if not copy:
        # cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}" -avoid_negative_ts 1 "tmp\\concat\\{segment_no}.mp4"'
        # 遇到 Too many packets buffered for output stream 0:0. Error submitting a packet to the muxer 增加muxing_queue大小
        cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}" -max_muxing_queue_size 9999 -avoid_negative_ts 1 "tmp\\concat\\{segment_no}.mp4"'
        # -aspect 调整比例 4:3
        # cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}" -aspect 4:3 -avoid_negative_ts 1 "tmp\\concat\\{segment_no}.mp4"'
        # -an 去除音轨
        # cmd = f'ffmpeg -y -ss {start} -to {end} -an -accurate_seek -i "{source_file_path}" -avoid_negative_ts 1 "tmp\\concat\\{segment_no}.mp4"'
        # 第二个音频流 + 默认视频流
        # i = 2
        # cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}" -map 0:v:0 -map 0:a:{i-1} -avoid_negative_ts 1 "tmp\\concat\\{segment_no}.mp4"'


    print(f"执行命令：{cmd}")
    result = os.system(cmd)
    if result == 0:
        print('执行成功')
    else:
        print('执行失败')
        exit(0)


def replace_dash_between_ts(file_name):
    pattern = r"\d{2}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}"  # 匹配时间戳模式

    matches = re.findall(pattern, file_name)
    if len(matches) > 0:
        for match in matches:
            new_file_name = file_name.replace(match, match.replace("-", "~"))
            return new_file_name


def concat_segments(target_file_path: str):
    cmd = f'ffmpeg -y -f concat -i "tmp\\concat\\filelist.txt" -c copy "{target_file_path}"'
    print(f"执行命令：{cmd}")
    os.system(cmd)


def remove_origin_file(source_file_path: str):
    os.remove(source_file_path)


def movie_clip_file_name_generator(config: configparser.ConfigParser, start_ts: str, end_ts: str):

    # 基本信息
    actor = config.get('MovieConfig', 'actor')
    chn_name = config.get('MovieConfig', 'chn_name', fallback=None)
    country = config.get('MovieConfig', 'country')
    movie = config.get('MovieConfig', 'movie')
    year = config.getint('MovieConfig', 'year')
    season = config.getint('MovieConfig', 'season', fallback=None)
    episode = config.getint('MovieConfig', 'episode', fallback=None)

    format_actor = actor.replace(' ', '.')
    if chn_name is not None:
        format_actor = f'{format_actor}.{chn_name}'
    format_movie = movie.replace(' ', '.')
    format_ts_range = f"{start_ts.replace(':', '.')}~{end_ts.replace(':', '.')}"
    if season is None or episode is None:
        return f'[{country}]{format_actor} » {format_movie}.{year} » {format_ts_range}.mp4'
    else:
        format_season = '{:02d}'.format(season)
        format_episode = '{:02d}'.format(episode)

        return f'[{country}]{format_actor} » {format_movie}.{year}.S{format_season}E{format_episode} » {format_ts_range}.mp4'


if __name__ == '__main__':

    config = configparser.ConfigParser()
    config.read('movie.ini', encoding='utf-8')
    source_file_path = config.get('MovieConfig', 'source_file_path')
    target_base_path = config.get('MovieConfig', 'target_base_path')
    segment_points_list = [


        ("00:09:37.043", "00:09:51.557"),
        ("00:09:53.793", "00:09:55.595"),
        ("00:51:13.319", "00:18:54.231"),


    ]

    copy = False
    segment_no = 0
    target_file_path = rf"{target_base_path}\{movie_clip_file_name_generator(config, segment_points_list[0][0], segment_points_list[-1][1])}"
    print(target_file_path)

    fp = open(r'tmp/concat/filelist.txt', mode='w', encoding='utf-8')
    file_list = []

    for (start, end) in segment_points_list:
        print(start, end)
        segment_no += 1
        video_cut(source_file_path, start, end, segment_no, copy)
        file_list.append(f'file {segment_no}.mp4')

    fp.write("\n".join(file_list))
    fp.close()

    concat_segments(target_file_path)
    # remove_origin_file(source_file_path)
