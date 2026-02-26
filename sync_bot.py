import os
import mysql.connector
import telebot
import time

# 从环境变量读取配置
DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASS'),
    'database': os.environ.get('DB_NAME')
}
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')
BASE_URL = 'https://tgzyz.pp.ua/'

bot = telebot.TeleBot(BOT_TOKEN)

def run():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 获取 type_id=41 的最新 1000 条数据
        query = """
        SELECT vod_id, vod_name, vod_pic, vod_tag, vod_play_url, vod_play_note 
        FROM mac_vod 
        WHERE type_id = 41 
        ORDER BY vod_time_add DESC 
        LIMIT 1000
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            vod_id = row['vod_id']
            # 检查去重逻辑：判断当前频道ID是否在 vod_play_note 中
            published_notes = str(row['vod_play_note'] or "")
            if CHANNEL_ID in published_notes.split(','):
                continue

            # --- 格式化 Caption ---
            # 1. 第一行：标签处理 (#标签1 #标签2)
            raw_tags = row['vod_tag'].replace('，', ',').split(',')
            hashtag_line = " ".join([f"#{t.strip()}" for t in raw_tags if t.strip()])
            
            # 2. 第三行：标题 (vod_name)
            content_title = row['vod_name']
            
            # 3. 第五行：超链接处理
            play_url = row['vod_play_url'].replace('HD$', '')
            link_line = f"<a href='{play_url}'>📂立即观看</a>     <a href='https://aisoav.com'>🌐更多精彩收藏</a>"
            
            # 组合全文
            caption = f"{hashtag_line}\n\n{content_title}\n\n{link_line}"
            
            # 拼接图片URL
            full_pic_url = BASE_URL + row['vod_pic']

            try:
                # 发布到 Telegram (has_spoiler=True 实现成人内容遮盖)
                bot.send_photo(
                    CHANNEL_ID, 
                    full_pic_url, 
                    caption=caption, 
                    parse_mode='HTML',
                    has_spoiler=True
                )

                # 更新 vod_play_note 标记已发布
                new_note = f"{published_notes},{CHANNEL_ID}".strip(',')
                update_sql = "UPDATE mac_vod SET vod_play_note = %s WHERE vod_id = %s"
                cursor.execute(update_sql, (new_note, vod_id))
                conn.commit()
                
                print(f"成功发布 ID {vod_id}: {content_title}")
                time.sleep(3.5) # 遵守 Telegram 频率限制，每秒约 30 条限制，留出余量

            except Exception as e:
                print(f"发布错误 ID {vod_id}: {e}")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"数据库连接失败: {e}")

if __name__ == "__main__":
    run()
