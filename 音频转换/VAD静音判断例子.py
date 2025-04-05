import wave
import webrtcvad

def find_silence_segments(
    wav_path,
    start_sec=600,
    end_sec=660,
    frame_ms=30,
    min_silence_sec=2.0,
    vad_mode=2
):
    vad = webrtcvad.Vad(vad_mode)
    with wave.open(wav_path, 'rb') as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        rate = wf.getframerate()
        frame_bytes = int(rate * frame_ms / 1000) * 2

        wf.setpos(int(start_sec * rate))
        num_frames = int((end_sec - start_sec) * rate)
        audio = wf.readframes(num_frames)

    offset = 0
    timestamp = start_sec
    duration = frame_ms / 1000.0
    silence_frames = []
    silence_segments = []

    while offset + frame_bytes <= len(audio):
        frame = audio[offset:offset + frame_bytes]
        is_voice = vad.is_speech(frame, rate)

        if not is_voice:
            silence_frames.append(timestamp)
        else:
            if len(silence_frames) * duration >= min_silence_sec:
                silence_segments.append((silence_frames[0], silence_frames[-1] + duration))
            silence_frames = []

        offset += frame_bytes
        timestamp += duration

    if len(silence_frames) * duration >= min_silence_sec:
        silence_segments.append((silence_frames[0], silence_frames[-1] + duration))

    return silence_segments


# ✅ 函数调用与测试代码
if __name__ == "__main__":
    wav_path = r"e:\2.wav"  # 👈 你的音频路径

    segments = find_silence_segments(
        wav_path=wav_path,
        start_sec=60,        # 从10分钟开始
        end_sec=120,          # 到11分钟
        frame_ms=30,
        min_silence_sec=3.0,
        vad_mode=3
    )

    print("检测到的静音段（长度 ≥ 2秒）如下：")
    for idx, (start, end) in enumerate(segments):
        duration = end - start
        print(f"第{idx+1}段: {start:.2f}s ~ {end:.2f}s （时长 {duration:.2f}s）")
