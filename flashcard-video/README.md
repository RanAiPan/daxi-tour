# 字卡影片產生器

用 Python + Pillow + ffmpeg 產生無聲的直式（1080x1920）字卡 MP4 影片：
馬卡龍淺綠色漸層背景、置中相片卡片（白框＋柔和陰影）、文字逐行淡入，
結尾淡出以利循環播放。

## 需求

```bash
pip install Pillow numpy
apt-get install ffmpeg fonts-noto-cjk   # 需要 Noto Serif CJK 字型
```

## 使用方式

1. 把要放進卡片的相片放到 `assets/photo.jpg`
2. 依需要修改 `make_flashcard_video.py` 最上方 `CONFIG`（文字內容、顏色、時長等）
3. 執行：

```bash
python3 make_flashcard_video.py
```

輸出檔會產生在 `output/quote_flashcard.mp4`（此資料夾已加入 .gitignore，不會進版控）。
