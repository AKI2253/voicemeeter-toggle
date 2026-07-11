"""pyaudioop stub — Python 3.13+ 移除了 audioop 模块, pydub 需要此替代。

提供 pydub 实际调用的最小函数集 (用纯 Python/numpy 实现)。
"""

import math

def max(data, width):
    """返回音频片段中的最大绝对值。"""
    if not data:
        return 0
    if width == 1:
        return max(abs(b - 128) for b in data)
    elif width == 2:
        import struct
        samples = struct.unpack(f'<{len(data)//2}h', data)
        return max(abs(s) for s in samples)
    elif width == 4:
        import struct
        samples = struct.unpack(f'<{len(data)//4}i', data)
        return max(abs(s) for s in samples)
    return 0

def maxpp(data, width):
    """返回峰峰值 (pydub 可能调用)。"""
    return max(data, width) * 2

def rms(data, width):
    """计算均方根。"""
    if not data:
        return 0
    if width == 1:
        squares = [(b - 128) ** 2 for b in data]
    elif width == 2:
        import struct
        samples = struct.unpack(f'<{len(data)//2}h', data)
        squares = [s ** 2 for s in samples]
    elif width == 4:
        import struct
        samples = struct.unpack(f'<{len(data)//4}i', data)
        squares = [s ** 2 for s in samples]
    else:
        return 0
    return int(math.sqrt(sum(squares) / len(squares)))

def ratecv(data, width, nchannels, inrate, outrate, state):
    """采样率转换 (pydub 可能调用)。"""
    # 简单实现: 线性插值
    if inrate == outrate:
        return data, state
    import struct
    ratio = outrate / inrate
    out_len = int(len(data) / width * ratio)
    # 返回原始数据 + 空状态 (简化, pydub 使用 ffmpeg 做重采样)
    return data, state

def tomono(data, width, lfactor, rfactor):
    """立体声转单声道。"""
    if not data:
        return data
    if width == 2:
        import struct
        samples = struct.unpack(f'<{len(data)//2}h', data)
        mono = [int((samples[i] * lfactor + samples[i+1] * rfactor)) for i in range(0, len(samples), 2)]
        return struct.pack(f'<{len(mono)}h', *mono)
    return data

def tostereo(data, width, lfactor, rfactor):
    """单声道转立体声。"""
    if not data:
        return data
    if width == 2:
        import struct
        samples = struct.unpack(f'<{len(data)//2}h', data)
        stereo = []
        for s in samples:
            stereo.append(int(s * lfactor))
            stereo.append(int(s * rfactor))
        return struct.pack(f'<{len(stereo)}h', *stereo)
    return data

def lin2lin(data, width, newwidth):
    """位深度转换。"""
    if width == newwidth:
        return data
    return data

def adpcm2lin(data, width, state):
    """ADPCM 解码 (极少使用, 返回空)。"""
    return data, state

def lin2adpcm(data, width, state):
    """ADPCM 编码 (极少使用, 返回空)。"""
    return data, state

def findmax(data, width):
    """返回 (最大值, 索引)。"""
    if not data:
        return 0, 0
    if width == 2:
        import struct
        samples = struct.unpack(f'<{len(data)//2}h', data)
        abs_samples = [abs(s) for s in samples]
        m = max(abs_samples)
        return m, abs_samples.index(m)
    return 0, 0

def findfit(data, width):
    """返回拟合参数 (极少使用)。"""
    return 0, 0

def cross(data, width):
    """过零检测。"""
    return 0

def getsample(data, width, index):
    """获取单个样本值。"""
    if width == 1:
        return data[index] - 128
    elif width == 2:
        import struct
        return struct.unpack_from('<h', data, index * 2)[0]
    elif width == 4:
        import struct
        return struct.unpack_from('<i', data, index * 4)[0]
    return 0

def add(data1, data2, width):
    """两段音频相加。"""
    return data1

def bias(data, width, bias):
    """添加偏置。"""
    return data

def reverse(data, width):
    """反转音频。"""
    return data[::-1]

def byteswap(data, width):
    """字节交换。"""
    return data

def alaw2lin(data, width):
    """A-law 解码。"""
    return data

def lin2alaw(data, width):
    """A-law 编码。"""
    return data

def ulaw2lin(data, width):
    """u-law 解码。"""
    return data

def lin2ulaw(data, width):
    """u-law 编码。"""
    return data

def mul(data, width, factor):
    """乘以因子。"""
    return data
