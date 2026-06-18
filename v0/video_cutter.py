import configparser
import os


def video_cut(source_file_path: str, start: str, end: str, target_file_name: str, target_base_path: str,
              copy: bool = False):
    print(f'源文件：{source_file_path}')
    print(f'截取时间范围：{start} ~ {end}')
    print(f'目标文件名：{target_file_name}')

    cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}" -codec copy -avoid_negative_ts 1 "{target_base_path}\\{target_file_name}"'
    # cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}" -b:v 2000k -avoid_negative_ts 1 "{target_base_path}\\{target_file_name}"'
    if not copy:
        cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}"  -avoid_negative_ts 1 "{target_base_path}\\{target_file_name}"'
        # 遇到 Too many packets buffered for output stream 0:0. Error submitting a packet to the muxer 增加muxing_queue大小
        # cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}"  -max_muxing_queue_size 9999 -avoid_negative_ts 1 "{target_base_path}\\{target_file_name}"'
        # 第i个音频流 + 默认视频流
        # i = 2
        # cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}" -map 0:v:0 -map 0:a:{i-1} -avoid_negative_ts 1 "{target_base_path}\\{target_file_name}"'
        # 比例改为16:9
        # cmd = f'ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source_file_path}" -aspect 16:9 -avoid_negative_ts 1 "{target_base_path}\\{target_file_name}"'


    print(f"执行命令：{cmd}")
    result = os.system(cmd)
    if result == 0:
        print('执行成功')
    else:
        print('执行失败')


def movie_clip_file_name_generator(actor: str, country: str, movie: str, year: int, start_ts: str, end_ts: str,
                                   season: int = None, episode: int = None, chn_name=None):
    format_actor = actor.replace(' ', '.')
    if chn_name is not None:
        format_actor = f'{format_actor}.{chn_name}'
    format_movie = movie.replace(' ', '.')
    format_ts_range = f"{start_ts.replace(':', '.')}-{end_ts.replace(':', '.')}"
    if season is None or episode is None:
        return f'[{country}]{format_actor} » {format_movie}.{year} » {format_ts_range}.mp4'
    else:
        format_season = '{:02d}'.format(season)
        format_episode = '{:02d}'.format(episode)

        return f'[{country}]{format_actor} » {format_movie}.{year}.S{format_season}E{format_episode} » {format_ts_range}.mp4'


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('movie.ini', encoding='utf-8')
    # 基本信息
    actor = config.get('MovieConfig', 'actor')
    chn_name = config.get('MovieConfig', 'chn_name', fallback=None)
    country = config.get('MovieConfig', 'country')
    movie = config.get('MovieConfig', 'movie')
    year = config.getint('MovieConfig', 'year')
    season = config.getint('MovieConfig', 'season', fallback=None)
    episode = config.getint('MovieConfig', 'episode', fallback=None)
    source_file_path = config.get('MovieConfig', 'source_file_path')
    target_base_path = config. get('MovieConfig', 'target_base_path')

    start_ts, end_ts = ("00:09:37.043", "00:10:57.924")
    # start_ts, end_ts = ("00:48:22.274", "00:48:36.538")


    target_clip_name = movie_clip_file_name_generator(actor, country, movie, year, start_ts, end_ts, season, episode,
                                                      chn_name)
    video_cut(source_file_path, start_ts, end_ts, target_clip_name,
              # target_base_path, copy=True)
              target_base_path, copy=False)
