import discord
from discord import app_commands, ui
from discord.ext import tasks
from datetime import datetime, timedelta

# --------------------------
# 봇 토큰
# --------------------------
DISCORD_TOKEN = "MTQ0NTM5ODc1NTc0NTczMDY3NQ.Gp2L5s.y2eFeVIk50zeERB3Zje_1flmOhwLzkibVAUmTM"

# --------------------------
# 봇 생성
# --------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = discord.Bot(intents=intents)

# --------------------------
# 데이터 저장소 (메모리 기반)
# --------------------------
banned_words = {}
nickname_detect_list = {}
warnings = {}
attendance_records = {}
attendance_message = {}
attendance_role_id = 123456789012345678

# --------------------------
# 도움말 버튼
# --------------------------
class HelpView(ui.View):
    def __init__(self):
        super().__init__()
        self.pages = [
            "**1. 금지어 / 화이트리스트**\n"
            "`/금지어추가 [단어]`, `/금지어제거 [단어]`, `/금지어목록`\n",

            "**2. 닉네임 감지**\n"
            "`/닉네임감지추가 [닉네임]`, `/닉네임감지제거 [닉네임]`, `/닉네임유저검사`\n",

            "**3. 메시지 차단 / 경고 시스템**\n"
            "`/경고부여 [유저] [사유]`, `/경고회수 [유저]`, `/경고목록 [유저]`, `/경고초기화 [유저]`, `/경고목록리스트`\n",

            "**4. 채팅 / 서버 관리**\n"
            "`/청소 [숫자]`, `/유저청소 [유저] [숫자]`, `/유저추방 [유저]`, `/유저밴 [유저]`, `/유저언밴 [유저]`, `/유저역할추가 [유저] [역할]`, `/유저역할제거 [유저] [역할]`\n",

            "**5. 출석체크 시스템**\n"
            "`/출석체크`: 24시간마다 특정 역할 멘션 + 임베드 출력\n"
            "출석 버튼 클릭 시 출석 완료 및 참여 인원 확인 가능\n"
        ]
        self.current = 0

    @ui.button(label="◀️ 이전", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: ui.Button):
        self.current = (self.current - 1) % len(self.pages)
        await interaction.response.edit_message(content=self.pages[self.current], view=self)

    @ui.button(label="▶️ 다음", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        self.current = (self.current + 1) % len(self.pages)
        await interaction.response.edit_message(content=self.pages[self.current], view=self)

# --------------------------
# 도움말 슬래시 명령어
# --------------------------
@bot.tree.command(name="help", description="봇 도움말")
async def help_command(interaction: discord.Interaction):
    view = HelpView()
    await interaction.response.send_message(view.pages[0], view=view, ephemeral=True)

# --------------------------
# 금지어 필터
# --------------------------
@bot.tree.command(name="금지어추가", description="금지어를 추가합니다.")
@app_commands.describe(word="추가할 금지어")
async def add_banned_word(interaction: discord.Interaction, word: str):
    server_id = interaction.guild.id
    banned_words.setdefault(server_id, set()).add(word)
    await interaction.response.send_message(f"'{word}' 금지어가 추가되었습니다.", ephemeral=True)

@bot.tree.command(name="금지어제거", description="금지어를 제거합니다.")
@app_commands.describe(word="제거할 금지어")
async def remove_banned_word(interaction: discord.Interaction, word: str):
    server_id = interaction.guild.id
    if word in banned_words.get(server_id, set()):
        banned_words[server_id].remove(word)
        await interaction.response.send_message(f"'{word}' 금지어가 제거되었습니다.", ephemeral=True)
    else:
        await interaction.response.send_message(f"'{word}' 금지어가 없습니다.", ephemeral=True)

@bot.tree.command(name="금지어목록", description="등록된 금지어를 확인합니다.")
async def list_banned_words(interaction: discord.Interaction):
    server_id = interaction.guild.id
    words = banned_words.get(server_id, [])
    await interaction.response.send_message("금지어 목록: " + ", ".join(words) if words else "등록된 금지어가 없습니다.", ephemeral=True)

# --------------------------
# 닉네임 감지
# --------------------------
@bot.tree.command(name="닉네임감지추가", description="닉네임 감지 추가")
@app_commands.describe(nickname="감지할 닉네임")
async def add_nickname(interaction: discord.Interaction, nickname: str):
    server_id = interaction.guild.id
    nickname_detect_list.setdefault(server_id, set()).add(nickname)
    await interaction.response.send_message(f"'{nickname}' 닉네임 감지 목록에 추가되었습니다.", ephemeral=True)

@bot.tree.command(name="닉네임감지제거", description="닉네임 감지 제거")
@app_commands.describe(nickname="제거할 닉네임")
async def remove_nickname(interaction: discord.Interaction, nickname: str):
    server_id = interaction.guild.id
    nickname_detect_list.get(server_id, set()).discard(nickname)
    await interaction.response.send_message(f"'{nickname}' 닉네임 감지 목록에서 제거되었습니다.", ephemeral=True)

@bot.tree.command(name="닉네임유저검사", description="감지된 닉네임 유저 확인")
async def check_nickname(interaction: discord.Interaction):
    server_id = interaction.guild.id
    detected_users = [member.mention for member in interaction.guild.members
                      if any(nick in member.display_name for nick in nickname_detect_list.get(server_id, set()))]
    await interaction.response.send_message("감지된 닉네임 유저:\n" + ", ".join(detected_users) if detected_users else "감지된 닉네임이 없습니다.", ephemeral=True)

# --------------------------
# 경고 시스템
# --------------------------
@bot.tree.command(name="경고부여", description="유저에게 경고 부여")
@app_commands.describe(user="경고를 부여할 유저", reason="경고 사유")
async def give_warning(interaction: discord.Interaction, user: discord.Member, reason: str):
    guild_id = interaction.guild.id
    warnings.setdefault(guild_id, {}).setdefault(user.id, []).append(reason)
    await interaction.response.send_message(f"{user.mention}님에게 경고가 부여되었습니다. 사유: {reason}", ephemeral=True)

@bot.tree.command(name="경고목록", description="유저 경고 목록 확인")
@app_commands.describe(user="확인할 유저")
async def warning_list(interaction: discord.Interaction, user: discord.Member):
    guild_id = interaction.guild.id
    warn_list = warnings.get(guild_id, {}).get(user.id, [])
    await interaction.response.send_message(f"{user.mention}님의 경고 목록:\n" + "\n".join(warn_list) if warn_list else "경고가 없습니다.", ephemeral=True)

# --------------------------
# 출석체크 시스템
# --------------------------
class AttendanceButton(ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @ui.button(label="출석체크", style=discord.ButtonStyle.green)
    async def check_in(self, interaction: discord.Interaction, button: ui.Button):
        guild_id = self.guild_id
        user_id = interaction.user.id
        attendance_records.setdefault(guild_id, set())
        if user_id in attendance_records[guild_id]:
            await interaction.response.send_message("이미 출석했습니다!", ephemeral=True)
        else:
            attendance_records[guild_id].add(user_id)
            await interaction.response.send_message(f"출석 완료! 현재 출석 인원: {len(attendance_records[guild_id])}명", ephemeral=True)
            msg = attendance_message.get(guild_id)
            if msg:
                embed = discord.Embed(
                    title="오늘 하루도 파이팅! 💪",
                    description=f"현재 출석 인원: {len(attendance_records[guild_id])}명",
                    color=discord.Color.green()
                )
                await msg.edit(embed=embed, view=self)

@bot.tree.command(name="출석체크", description="출석 메시지 생성")
async def attendance_command(interaction: discord.Interaction):
    guild = interaction.guild
    channel = interaction.channel
    role = guild.get_role(attendance_role_id)
    embed = discord.Embed(
        title="오늘 하루도 파이팅! 💪",
        description="출석 버튼을 눌러 출석 체크 해주세요!",
        color=discord.Color.green()
    )
    view = AttendanceButton(guild.id)
    msg = await channel.send(content=role.mention if role else "", embed=embed, view=view)
    attendance_message[guild.id] = msg
    attendance_records[guild.id] = set()

@tasks.loop(hours=24)
async def attendance_broadcast():
    for guild in bot.guilds:
        if not guild.text_channels:
            continue
        channel = guild.text_channels[0]
        role = guild.get_role(attendance_role_id)
        embed = discord.Embed(
            title="오늘 하루도 파이팅! 💪",
            description="출석 버튼을 눌러 출석 체크 해주세요!",
            color=discord.Color.green()
        )
        view = AttendanceButton(guild.id)
        msg = await channel.send(content=role.mention if role else "", embed=embed, view=view)
        attendance_message[guild.id] = msg
        attendance_records[guild.id] = set()

# --------------------------
# 봇 준비 이벤트
# --------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} 봇이 실행되었습니다.")
    if not attendance_broadcast.is_running():
        attendance_broadcast.start()

# --------------------------
# 메시지 필터
# --------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    guild_id = message.guild.id
    if any(word in message.content for word in banned_words.get(guild_id, set())):
        await message.delete()
        await message.channel.send(f"{message.author.mention}, 금지어 사용 금지!", delete_after=5)
    await bot.process_commands(message)

# --------------------------
# 봇 실행
# --------------------------
bot.run(DISCORD_TOKEN)
