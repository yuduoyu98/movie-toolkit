import configparser
import os

TMP_FILE = r'tmp/palette.png'


def gif_cut(source_file_path: str, start: str, ts: str, target_file_name: str, target_file_path: str):
    filters = "fps=30,scale=600:-1:flags=lanczos"
    # filters = "fps=30,scale=600:337.5:flags=lanczos"
    print(f'源文件：{source_file_path}')
    print(f'截取时间范围：{start} + {ts}')
    pre_cmd = f'ffmpeg -y -ss {start} -t {ts} -i "{source_file_path}" -vf "{filters},palettegen" {TMP_FILE}'
    print(f"预处理命令：{pre_cmd}")
    result = os.system(pre_cmd)
    if result == 0:
        print('执行成功')
    else:
        print('执行失败')
        exit(1)
    target_file_path = get_nonconflicting_filename(f'{target_file_path}\\{target_file_name}')
    print(f'目标文件名：{target_file_path}')
    cmd = f'ffmpeg -y -ss {start} -t {ts} -i "{source_file_path}" -i {TMP_FILE} -lavfi "{filters} [x]; [x][1:v] paletteuse" "{target_file_path}"'
    print(f"执行命令：{cmd}")
    result = os.system(cmd)
    if result == 0:
        print('执行成功')
    else:
        print('执行失败')
        exit(1)


def gif_cut_plus(source_file_path: str, start: str, end: str, target_file_name: str, target_file_path: str,
                 brightness: float, contrast: float, setpts: float):
    # 比例
    scale_ratio = "600:-1" # 默认自适应
    # scale_ratio = "600:324" # 指定
    fps = 30
    filters = f"eq=contrast={contrast}:brightness={brightness},setpts={setpts}*PTS,fps={fps},scale={scale_ratio}:flags=lanczos"
    print(f'源文件：{source_file_path}')
    print(f'截取时间范围：{start} + {end}')
    pre_cmd = f'ffmpeg -y -ss {start} -to {end} -i "{source_file_path}" -vf "{filters},palettegen" {TMP_FILE}'
    print(f"预处理命令：{pre_cmd}")
    result = os.system(pre_cmd)
    if result == 0:
        print('执行成功')
    else:
        print('执行失败')
        exit(1)
    target_file_path = get_nonconflicting_filename(f'{target_file_path}\\{target_file_name}')
    print(f'目标文件名：{target_file_path}')
    cmd = f'ffmpeg -y -ss {start} -to {end} -i "{source_file_path}" -i {TMP_FILE} -lavfi "{filters} [x]; [x][1:v] ' \
          f'paletteuse" "{target_file_path}" '
    print(f"执行命令：{cmd}")
    result = os.system(cmd)
    if result == 0:
        print('执行成功')
    else:
        print('执行失败')
        exit(1)


def get_nonconflicting_filename(file_path):
    if not os.path.exists(file_path):
        return file_path  # 文件名不冲突，直接返回

    file_name, extension = os.path.splitext(file_path)
    base_name = file_name.split('(')[0]
    index = int(file_name.split('(')[1].split(')')[0])
    index += 1

    while True:
        new_filename = f"{base_name}({index}){extension}"
        if not os.path.exists(new_filename):
            return new_filename  # 找到一个不冲突的文件名
        index += 1


def gif_file_name_generator(actor: str, country: str, movie: str, year: int, season: int = None, episode: int = None,
                            chn_name: str = None):
    format_actor = actor.replace(' ', '.')
    if chn_name is not None:
        format_actor = f'{format_actor}.{chn_name}'
    format_movie = movie.replace(' ', '.')
    if season is None or episode is None:
        return f'[{country}]{format_actor} » {format_movie}.{year}(1).gif'
    else:
        format_season = '{:02d}'.format(season)
        format_episode = '{:02d}'.format(episode)
        return f'[{country}]{format_actor} » {format_movie}.{year}.S{format_season}E{format_episode}(1).gif'



if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('movie.ini', encoding='utf-8')
    # 基本信息
    actor = config.get('MovieConfig', 'actor')
    chn_name = config.get('MovieConfig', 'chn_name', fallback=None)
    country = config.get('MovieConfig', 'country')
    movie = config.get('MovieConfig', 'movie')
    year =  config.getint('MovieConfig', 'year')
    season = config.getint('MovieConfig', 'season', fallback=None)
    episode = config.getint('MovieConfig', 'episode', fallback=None)
    source_file_path = config.get('MovieConfig', 'source_file_path')
    target_base_path = config.get('MovieConfig', 'target_base_path')

    # start_ts, end_ts = ("00:00:13.978", "00:00:27.622")
    start_ts, end_ts = ("00:00:29.442", "00:00:36.614")

    target_clip_name = gif_file_name_generator(actor, country, movie, year, season, episode, chn_name)

    # gif_cut(source_file_path, start_ts, ts, target_clip_name, target_base_path)
    # gif_cut_plus(source_file_path, start_ts, ts,  target_clip_name, target_base_path, brightness=0, contrast=1, setpts=1)
    gif_cut_plus(source_file_path, start_ts, end_ts, target_clip_name, target_base_path,
                 brightness=0,contrast=1, setpts=1)
                 # brightness=0, contrast=0.9, setpts=1)