import os
import mysql.connector
import telebot
import time

# 配置读取
DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASS'),
    'database': os.environ.get('DB_NAME'),
    'port': 3306,
    'autocommit': True  # 关键：确保更新立即生效
}
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = str(os.environ.get('CHANNEL_ID'))
BASE_URL = 'https://tgzyz.pp.ua/'

bot = telebot.TeleBot(BOT_TOKEN)

def run():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 逻辑调整：
        # 1. 先外层查询 type_id=41 的最近 1000 条 (DESC 降序)
        # 2. 再将这 1000 条按时间升序排列 (ASC)，实现“先旧后新”
        query = """
        SELECT * FROM (
            SELECT vod_id, vod_name, vod_pic, vod_tag, vod_play_url, vod_play_note, vod_time_add 
            FROM mac_vod 
            WHERE type_id = 41 
            ORDER BY vod_time_add DESC 
            LIMIT 1000
        ) AS temp_table 
        ORDER BY vod_time_add ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"成功获取 {len(rows)} 条数据，开始处理...")

        for row in rows:
            vod_id = row['vod_id']
            
            # --- 严格去重检查 ---
            current_note = str(row['vod_play_note'] or "")
            if CHANNEL_ID in current_note.split(','):
                continue

            # --- 内容处理 ---
            tags = row['vod_tag'].replace('，', ',').split(',')
            hashtag_line = " ".join([f"#{t.strip()}" for t in tags if t.strip()])
            
            # 处理超链接：截取 $ 后的部分
            raw_url = row['vod_play_url'].split('$')[-1] if '$' in row['vod_play_url'] else row['vod_play_url']
            
            caption = (
                f"{hashtag_line}\n\n"
                f"{row['vod_name']}\n\n"
                f"<a href='{raw_url}'>📂立即观看</a>     "
                f"<a href='https://aisoav.com'>🌐更多精彩收藏</a>"
            )
            
            # 图片拼接
            pic = row['vod_pic']
            full_pic_url = pic if pic.startswith('http') else BASE_URL + pic

            try:
                # 发送 Telegram 消息
                bot.send_photo(
                    CHANNEL_ID, 
                    full_pic_url, 
                    caption=caption, 
                    parse_mode='HTML',
                    has_spoiler=True
                )

                # --- 标记回写数据库 ---
                # 将 ID 拼接到原有内容后面
                new_note = f"{current_note},{CHANNEL_ID}".strip(',')
                
                # 显式执行更新
                update_sql = "UPDATE mac_vod SET vod_play_note = %s WHERE vod_id = %s"
                cursor.execute(update_sql, (new_note, vod_id))
                
                # 记录日志方便在 GitHub Actions 中排查
                print(f"✅ 发布成功并标记: {row['vod_name']} (ID: {vod_id})")
                
                # 适当延时防止 API 频率限制
                time.sleep(3)

            except Exception as send_error:
                print(f"❌ 发送失败 (ID {vod_id}): {send_error}")

    except Exception as db_error:
        print(f"💥 数据库错误: {db_error}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    run()
