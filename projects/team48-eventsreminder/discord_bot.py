"""Discord DM 리마인더 알림 봇"""

import argparse
import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import discord
import discord.app_commands
import discord.ui
from dotenv import load_dotenv
from gtts import gTTS

from db import (
    add_reminder,
    get_unsent_reminders,
    get_upcoming_reminders,
    init_db,
    mark_as_sent,
    update_reminder,
)


TTS_DIR = Path("tts")
CHECK_INTERVAL_SECONDS = 60
TEST_MESSAGE = "Discord DM 테스트 메시지입니다."

CATEGORY_COLORS = {
    "면접": 0x5865F2,
    "시험": 0xED4245,
    "약속": 0x57F287,
    "마감": 0xFEE75C,
    "기타": 0x99AAB5,
}


@dataclass(frozen=True)
class BotConfig:
    token: str
    user_id: int


def load_config() -> BotConfig:
    """환경 설정을 읽고 Discord 봇 설정을 반환"""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    user_id = os.environ.get("DISCORD_USER_ID")

    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN 환경변수가 필요합니다.")
    if not user_id:
        raise RuntimeError("DISCORD_USER_ID 환경변수가 필요합니다.")

    try:
        parsed_user_id = int(user_id)
    except ValueError as exc:
        raise RuntimeError("DISCORD_USER_ID는 숫자여야 합니다.") from exc

    return BotConfig(token=token, user_id=parsed_user_id)


def _discord_ts(dt_str: str) -> str:
    """ISO datetime → Discord 상대+절대 타임스탬프 문자열"""
    ts = int(datetime.fromisoformat(dt_str[:19]).timestamp())
    return f"<t:{ts}:F>  (<t:{ts}:R>)"


def build_embed(reminder: dict, note: str = "") -> discord.Embed:
    """리마인더를 Discord Embed 카드로 변환"""
    category = reminder.get("event_category") or "기타"
    color = CATEGORY_COLORS.get(category, 0x99AAB5)

    description = reminder["message"]
    if note:
        description += f"\n\n{note}"

    embed = discord.Embed(title="⏰ 리마인더", description=description, color=color)
    embed.add_field(name="카테고리", value=category, inline=True)
    embed.add_field(name="알림 시각", value=_discord_ts(reminder["remind_at"]), inline=True)
    return embed


class SnoozeView(discord.ui.View):
    """리마인더 카드에 붙는 미루기/확인 버튼 (1시간 후 자동 만료)"""

    def __init__(self, reminder: dict):
        super().__init__(timeout=3600)
        self.reminder = reminder

    @discord.ui.button(label="30분 미루기", style=discord.ButtonStyle.secondary, emoji="⏰")
    async def snooze_30(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._snooze(interaction, 30)

    @discord.ui.button(label="1시간 미루기", style=discord.ButtonStyle.secondary, emoji="⏰")
    async def snooze_60(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._snooze(interaction, 60)

    @discord.ui.button(label="확인", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_embed(self.reminder, note="✅ 확인했습니다.")
        await interaction.response.edit_message(embed=embed, view=None)

    async def _snooze(self, interaction: discord.Interaction, minutes: int):
        new_time = (datetime.now() + timedelta(minutes=minutes)).isoformat()
        add_reminder(self.reminder["event_id"], new_time, self.reminder["message"])
        embed = build_embed(self.reminder, note=f"⏰ {minutes}분 뒤 다시 알려드릴게요.")
        await interaction.response.edit_message(embed=embed, view=None)


def text_to_speech(message: str, file_name: str) -> Path:
    """메시지를 mp3 음성 파일로 변환하고 파일 경로 반환"""
    TTS_DIR.mkdir(exist_ok=True)
    file_path = TTS_DIR / file_name

    tts = gTTS(text=message, lang="ko", slow=False)
    tts.save(file_path)

    return file_path


async def create_tts_file(message: str, file_name: str) -> Path:
    """gTTS 파일 생성을 이벤트 루프 밖에서 실행"""
    return await asyncio.to_thread(text_to_speech, message, file_name)


class ReminderBot(discord.Client):
    def __init__(self, config: BotConfig, test_mode: bool):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.config = config
        self.test_mode = test_mode
        self.reminder_task: asyncio.Task | None = None
        self.tree = discord.app_commands.CommandTree(self)
        self._register_commands()

    def _register_commands(self):
        bot = self

        async def reminder_id_autocomplete(
            interaction: discord.Interaction,
            current: str,
        ) -> list[discord.app_commands.Choice[int]]:
            reminders = get_upcoming_reminders(limit=25)
            choices = []
            for r in reminders:
                title = r["event_title"]
                if current and current.lower() not in title.lower() and current not in str(r["id"]):
                    continue
                label = f"#{r['id']} {title}"[:100]
                choices.append(discord.app_commands.Choice(name=label, value=r["id"]))
            return choices[:25]

        @bot.tree.command(name="reminders", description="예정된 리마인더 목록을 확인합니다")
        async def cmd_list(interaction: discord.Interaction):
            if interaction.user.id != bot.config.user_id:
                await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
                return
            reminders = get_upcoming_reminders()
            if not reminders:
                await interaction.response.send_message("예정된 리마인더가 없습니다.", ephemeral=True)
                return
            embed = discord.Embed(title="📅 예정 리마인더", color=0x5865F2)
            for r in reminders:
                category = r.get("event_category") or "기타"
                embed.add_field(
                    name=f"`#{r['id']}` {r['event_title']}",
                    value=f"{_discord_ts(r['remind_at'])}\n카테고리: {category}",
                    inline=False,
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @bot.tree.command(name="snooze", description="리마인더를 N분 뒤로 미룹니다")
        @discord.app_commands.describe(
            reminder_id="미룰 리마인더 (선택하거나 ID 입력)",
            minutes="미룰 시간(분, 예: 30)",
        )
        @discord.app_commands.autocomplete(reminder_id=reminder_id_autocomplete)
        async def cmd_snooze(interaction: discord.Interaction, reminder_id: int, minutes: int):
            if interaction.user.id != bot.config.user_id:
                await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
                return
            if minutes <= 0:
                await interaction.response.send_message("1분 이상 입력하세요.", ephemeral=True)
                return
            new_time = (datetime.now() + timedelta(minutes=minutes)).isoformat()
            update_reminder(reminder_id, new_time)
            await interaction.response.send_message(
                f"리마인더 #{reminder_id}를 {minutes}분 뒤로 미뤘습니다.",
                ephemeral=True,
            )

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        await self.tree.sync()
        print("슬래시 커맨드 동기화 완료")

        if self.test_mode:
            await self.send_test_dm()
            await self.close()
            return

        if self.reminder_task is None or self.reminder_task.done():
            self.reminder_task = asyncio.create_task(self.run_reminder_loop())

    async def fetch_target_user(self) -> discord.User:
        user = self.get_user(self.config.user_id)
        if user is None:
            user = await self.fetch_user(self.config.user_id)
        return user

    async def send_dm_with_tts(
        self,
        user: discord.User,
        message: str,
        file_name: str,
        audio_label: str,
    ):
        audio_path = await create_tts_file(message, file_name)

        await user.send(message)
        await user.send(
            content=audio_label,
            file=discord.File(audio_path, filename=audio_path.name),
        )

    async def send_test_dm(self):
        try:
            user = await self.fetch_target_user()
            await self.send_dm_with_tts(
                user,
                TEST_MESSAGE,
                "test_dm.mp3",
                "음성 알림 테스트",
            )
            print(f"DM 전송 완료: {user} ({self.config.user_id})")
        except discord.Forbidden as exc:
            print(f"DM 전송 실패: {exc}")
            print("봇과 사용자가 함께 들어가 있는 서버가 없거나, 사용자의 DM 설정이 막혀 있습니다.")

    async def run_reminder_loop(self):
        while not self.is_closed():
            try:
                await self.check_and_send_reminders()
            except Exception as exc:
                print(f"리마인더 확인 실패: {exc}")

            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    async def check_and_send_reminders(self):
        user = await self.fetch_target_user()

        for reminder in get_unsent_reminders():
            try:
                await self.send_reminder(user, reminder)
            except Exception as exc:
                print(f"리마인더 전송 실패 id={reminder.get('id')}: {exc}")

    async def send_reminder(self, user: discord.User, reminder: dict):
        embed = build_embed(reminder)
        view = SnoozeView(reminder)
        await user.send(embed=embed, view=view)
        mark_as_sent(reminder["id"])
        try:
            tts_text = reminder["message"].replace("\n", ". ")
            audio_path = await create_tts_file(tts_text, f"reminder_{reminder['id']}.mp3")
            await user.send(content="🔊 음성 알림", file=discord.File(audio_path, filename=audio_path.name))
        except Exception as exc:
            print(f"TTS 전송 실패 (알림은 발송됨) id={reminder.get('id')}: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discord 리마인더 DM 봇")
    parser.add_argument(
        "--test-dm",
        action="store_true",
        help="리마인더 루프 없이 DM 테스트 메시지만 전송하고 종료합니다.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    load_dotenv()
    config = load_config()

    init_db()
    bot = ReminderBot(config=config, test_mode=args.test_dm)
    bot.run(config.token)


if __name__ == "__main__":
    main()
